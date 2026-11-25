"""Reúne cópias rastreáveis dos resultados pertinentes à pergunta da tese."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'v1': 'v1/results',
    'comparacao_ENSO': 'comparacao_ENSO/results',
    **{
        f'intermediarios/{name}': f'{name}/results'
        for name in (
            'experimento_sem_ONI',
            'experimento_com_ONI',
            'experimento_ONI_continuo',
            'experimento_ONI_resumido',
        )
    },
}
EXTRA_FILES = {
    'comparacao_ENSO/INTERPRETACAO.md': 'comparacao_ENSO/INTERPRETACAO.md',
    'comparacao_ENSO/verificacao.json': 'comparacao_ENSO/verificacao.json',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(root=ROOT):
    root = Path(root)
    # Confere todas as origens antes de escrever qualquer cópia.
    for source in SOURCES.values():
        if not (root / source).is_dir():
            raise FileNotFoundError(f'Origem ausente: {source}')
    for source in EXTRA_FILES.values():
        if not (root / source).is_file():
            raise FileNotFoundError(f'Origem ausente: {source}')
    records = []
    pairs = [
        (path, root / 'results' / destination / path.relative_to(root / source))
        for destination, source in SOURCES.items()
        for path in sorted((root / source).rglob('*')) if path.is_file()
    ] + [(root / source, root / 'results' / destination)
         for destination, source in EXTRA_FILES.items()]
    for path, target in pairs:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        checksum = digest(path)
        if digest(target) != checksum:
            raise ValueError(f'Cópia divergente: {target}')
        records.append({
            'origem': path.relative_to(root).as_posix(),
            'copia': target.relative_to(root).as_posix(),
            'bytes': path.stat().st_size,
            'sha256': checksum,
        })
    payload = {
        'schemaVersion': '1.0.0',
        'copiadoEm': datetime.now(timezone.utc).isoformat(),
        'tipo': 'cópias de consulta; as origens continuam sendo as saídas dos estudos',
        'fontes': SOURCES,
        'arquivosAdicionais': EXTRA_FILES,
        'arquivos': records,
    }
    (root / 'results/manifesto.json').write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
    )
    return len(records)


def verify(root=ROOT):
    root = Path(root)
    payload = json.loads((root / 'results/manifesto.json').read_text(encoding='utf-8'))
    expected_sources = set()
    expected_copies = set()
    for row in payload['arquivos']:
        expected_sources.add(row['origem'])
        expected_copies.add(row['copia'])
        for key in ('origem', 'copia'):
            path = root / row[key]
            if not path.is_file() or digest(path) != row['sha256']:
                raise ValueError(f'Arquivo ausente ou alterado: {row[key]}')
    actual_sources = {
        p.relative_to(root).as_posix()
        for source in SOURCES.values()
        for p in (root / source).rglob('*') if p.is_file()
    }
    actual_sources.update(EXTRA_FILES.values())
    actual_copies = {
        p.relative_to(root).as_posix()
        for destination in SOURCES
        for p in (root / 'results' / destination).rglob('*') if p.is_file()
    }
    if expected_sources != actual_sources or expected_copies != actual_copies:
        raise ValueError('Inventário desatualizado: há arquivos novos, ausentes ou extras.')
    return len(expected_copies)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Confere cópias e origens sem escrever.')
    args = parser.parse_args()
    count = verify() if args.check else collect()
    print(f'{count} arquivos {"verificados" if args.check else "copiados e verificados"}.')
