import argparse
import json
import os
import re
from pathlib import Path, PurePosixPath
import tempfile


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_FIELDS = (
    'previsao',
    'metricas',
    'explicabilidade',
    'conclusao',
    'resultadoCompleto',
)
BUNDLED_FIELDS = RESOURCE_FIELDS[:-1]


def resource_path(value):
    path = PurePosixPath(value)
    if (
        not re.fullmatch(r'[A-Za-z0-9_./-]+\.json', value)
        or path.is_absolute()
        or '..' in path.parts
    ):
        raise ValueError(f'Caminho de recurso inválido: {value}')
    return path.as_posix()


def reject_constant(value):
    raise ValueError(f'Valor JSON não finito: {value}')


def prepare_export(source):
    catalog = json.loads((source / 'catalogo.json').read_text(encoding='utf-8'))
    if catalog.get('schemaVersion') != '1.0.0':
        raise ValueError('Versão de catálogo incompatível.')

    resources = {'catalogo.json', 'data/dataset_utilizado.json'}
    bundled = set(resources)
    combinations = set()

    for entry in catalog['resultados']:
        key = (entry['modelo'], entry['horizonteSemanas'])
        if key in combinations:
            raise ValueError(f'Resultado duplicado: {key}')
        combinations.add(key)
        for field in RESOURCE_FIELDS:
            relative = resource_path(entry[field])
            resources.add(relative)
            if field in BUNDLED_FIELDS:
                bundled.add(relative)
        if 'retrospectiva' in entry:
            relative = resource_path(entry['retrospectiva'])
            resources.add(relative)
            bundled.add(relative)

    expected = {
        (model, horizon)
        for model in ('random_forest', 'rnn', 'lstm')
        for horizon in (4, 8, 12, 16)
    }
    if combinations != expected:
        raise ValueError('O catálogo deve conter os três modelos nos quatro horizontes.')

    contents = {}
    payloads = {}
    for relative in sorted(resources):
        path = (source / relative).resolve()
        if not path.is_relative_to(source.resolve()):
            raise ValueError(f'Recurso fora da origem: {relative}')
        content = path.read_bytes()
        payloads[relative] = json.loads(content, parse_constant=reject_constant)
        contents[relative] = content

    for entry in catalog['resultados']:
        for field in ('previsao', 'metricas', 'conclusao'):
            payload = payloads[entry[field]]
            if (
                payload['modelo'] != entry['modelo']
                or payload['horizonteSemanas'] != entry['horizonteSemanas']
            ):
                raise ValueError(f'Modelo ou horizonte divergente: {entry[field]}')
        forecast = payloads[entry['previsao']]
        conclusion = payloads[entry['conclusao']]
        if forecast['dataAlvo'] != entry['dataAlvo']:
            raise ValueError(f'Data-alvo divergente: {entry["previsao"]}')
        if (
            conclusion['dataAlvo'] != forecast['dataAlvo']
            or conclusion['texto'] != forecast['textoConclusao']
        ):
            raise ValueError(f'Conclusão divergente: {entry["conclusao"]}')

    return contents, sorted(bundled)


def write_atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def build_registry(destination, registry, bundled):
    lines = ['export const bundledResults: Record<string, () => unknown> = {']
    for relative in bundled:
        target = os.path.relpath(destination / relative, registry.parent)
        target = target.replace(os.sep, '/')
        if not target.startswith('.'):
            target = './' + target
        key = "'" + relative.replace("'", "\\'") + "'"
        module = "'" + target.replace("'", "\\'") + "'"
        line = f'  {key}: () => require({module}),'
        if len(line) > 90:
            lines.extend((f'  {key}: () =>', f'    require({module}),'))
        else:
            lines.append(line)
    lines.append('};')
    return ('\n'.join(lines) + '\n').encode()


def export_results(source, destination, registry):
    source = source.resolve()
    destination = destination.resolve()
    if (
        destination == source
        or destination.is_relative_to(source)
        or source.is_relative_to(destination)
    ):
        raise ValueError('Origem e destino devem ser pastas independentes.')

    contents, bundled = prepare_export(source)
    for relative, content in contents.items():
        write_atomic(destination / relative, content)
    if registry:
        write_atomic(registry, build_registry(destination, registry, bundled))
    return len(contents)


def main():
    parser = argparse.ArgumentParser(
        description='Exporta os JSONs da v1 para consumo pelo aplicativo.'
    )
    parser.add_argument('--source', type=Path, default=ROOT / 'v1/results')
    parser.add_argument('--destination', type=Path, default=ROOT / 'export')
    parser.add_argument(
        '--registry',
        type=Path,
        default=ROOT / 'mobile/src/generated/results.ts',
    )
    parser.add_argument('--no-registry', action='store_true')
    arguments = parser.parse_args()
    registry = None if arguments.no_registry else arguments.registry
    count = export_results(arguments.source, arguments.destination, registry)
    print(
        f'{count} JSONs exportados para {arguments.destination.resolve()} '
        'sem alteração de conteúdo.'
    )


if __name__ == '__main__':
    main()
