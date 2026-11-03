import argparse
import json
from pathlib import Path, PurePosixPath


FIELDS = (
    'previsao', 'metricas', 'explicabilidade',
    'conclusao', 'resultadoCompleto', 'retrospectiva',
)


def reject_constant(value):
    raise ValueError(f'Valor JSON inválido: {value}')


def load_resource(directory, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or path.suffix != '.json':
        raise ValueError(f'Caminho inválido: {relative}')
    resource = directory.joinpath(*path.parts)
    if not resource.resolve().is_relative_to(directory.resolve()):
        raise ValueError(f'Recurso fora de export: {relative}')
    return json.loads(resource.read_text(encoding='utf-8'), parse_constant=reject_constant)


def validate_export(directory):
    directory = Path(directory)
    catalog = load_resource(directory, 'catalogo.json')
    if catalog.get('schemaVersion') != '1.0.0':
        raise ValueError('Versão do catálogo incompatível.')
    combinations = set()
    resources = {'catalogo.json', 'data/dataset_utilizado.json'}
    for entry in catalog['resultados']:
        key = (entry['modelo'], entry['horizonteSemanas'])
        if key in combinations:
            raise ValueError(f'Resultado duplicado: {key}')
        combinations.add(key)
        payloads = {}
        for field in FIELDS:
            payloads[field] = load_resource(directory, entry[field])
            resources.add(entry[field])
        for field in ('previsao', 'metricas', 'conclusao', 'retrospectiva'):
            payload = payloads[field]
            if (payload['modelo'], payload['horizonteSemanas']) != key:
                raise ValueError(f'Modelo ou horizonte divergente: {entry[field]}')
        forecast = payloads['previsao']
        if forecast['dataAlvo'] != entry['dataAlvo']:
            raise ValueError('Data-alvo divergente.')
        if payloads['conclusao']['texto'] != forecast['textoConclusao']:
            raise ValueError('Conclusão divergente da previsão.')
        complete = payloads['resultadoCompleto']
        for field in ('previsao', 'metricas', 'explicabilidade'):
            if complete[field] != payloads[field]:
                raise ValueError(f'Resultado completo divergente: {entry[field]}')
        retrospective = payloads['retrospectiva']
        if len(retrospective['registros']) != forecast['desempenhoHistorico']['semanasAvaliadas']:
            raise ValueError('Número de semanas divergente na retrospectiva.')
    expected = {
        (model, horizon)
        for model in ('random_forest', 'rnn', 'lstm')
        for horizon in (4, 8, 12, 16)
    }
    if combinations != expected:
        raise ValueError('Faltam modelos ou horizontes na exportação.')
    if not load_resource(directory, 'data/dataset_utilizado.json'):
        raise ValueError('Série histórica vazia.')
    for path in directory.rglob('*.json'):
        load_resource(directory, path.relative_to(directory).as_posix())
    return len(resources)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Valida somente os JSONs de export.')
    parser.add_argument('directory', type=Path)
    arguments = parser.parse_args()
    count = validate_export(arguments.directory)
    print(f'Exportação válida: {count} recursos, três modelos e quatro horizontes.')
