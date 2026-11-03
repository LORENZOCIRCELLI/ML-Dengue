import csv
from datetime import date
import json
from pathlib import Path


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
        encoding='utf-8',
    )


def build_retrospective(results, entry):
    directory = results / Path(entry['previsao']).parent
    forecast = read_json(directory / 'previsao.json')
    metrics = read_json(directory / 'metricas.json')
    predictions = read_json(directory / 'data/previsoes_teste.json')
    records = []
    counts = {
        'verdadeiro_negativo': 0,
        'falso_positivo': 0,
        'falso_negativo': 0,
        'verdadeiro_positivo': 0,
    }
    outcomes = {
        (False, False): 'verdadeiro_negativo',
        (False, True): 'falso_positivo',
        (True, False): 'falso_negativo',
        (True, True): 'verdadeiro_positivo',
    }
    for row in predictions:
        emission = date.fromisoformat(row['data_emissao'][:10])
        target_date = date.fromisoformat(row['data_alvo'][:10])
        if row['split'] != 'teste':
            raise ValueError('A retrospectiva deve conter somente a partição de teste.')
        if (target_date - emission).days != 7 * entry['horizonteSemanas']:
            raise ValueError('Distância entre emissão e alvo incompatível com o horizonte.')
        actual = row['casos_futuros'] >= 1.5 * row['media_referencia']
        predicted = row['escore_aumento'] >= forecast['limiarDecisao']
        if row['target'] != int(actual) or row['prediction'] != int(predicted):
            raise ValueError('Rótulo ou previsão divergente dos valores originais.')
        outcome = outcomes[(actual, predicted)]
        counts[outcome] += 1
        records.append({
            'dataEmissao': emission.isoformat(),
            'dataAlvo': target_date.isoformat(),
            'mediaCasosReferencia': row['media_referencia'],
            'limiteCasosAumento': 1.5 * row['media_referencia'],
            'casosObservados': row['casos_futuros'],
            'aumentoObservado': actual,
            'aumentoPrevisto': predicted,
            'acertou': actual == predicted,
            'resultado': outcome,
            'escoreAumentoNaoCalibrado': row['escore_aumento'],
        })

    records.sort(key=lambda row: row['dataAlvo'])
    if not records or len({row['dataAlvo'] for row in records}) != len(records):
        raise ValueError('Retrospectiva vazia ou com semanas duplicadas.')
    historical = forecast['desempenhoHistorico']
    correct = counts['verdadeiro_negativo'] + counts['verdadeiro_positivo']
    matrix = [
        [counts['verdadeiro_negativo'], counts['falso_positivo']],
        [counts['falso_negativo'], counts['verdadeiro_positivo']],
    ]
    test = next(row for row in metrics['metricas'] if row['split'] == 'teste')
    if (
        len(records) != historical['semanasAvaliadas']
        or len(records) != test['n_samples']
        or abs(correct / len(records) - historical['acuracia']) > 1e-12
        or matrix != metrics['matrizesConfusao']['teste']['valores']
    ):
        raise ValueError('Retrospectiva divergente das métricas históricas existentes.')

    return {
        'schemaVersion': '1.0.0',
        'versao': forecast['versao'],
        'modelo': entry['modelo'],
        'nomeModelo': forecast['nomeModelo'],
        'horizonteSemanas': entry['horizonteSemanas'],
        'particao': 'teste',
        'tipoAvaliacao': historical['tipoAvaliacao'],
        'criterio': forecast['criterio'],
        'limiarDecisao': forecast['limiarDecisao'],
        'periodoAlvo': {
            'inicio': records[0]['dataAlvo'],
            'fim': records[-1]['dataAlvo'],
        },
        'unidades': {
            'casosObservados': 'casos/semana',
            'mediaCasosReferencia': 'casos/semana',
            'limiteCasosAumento': 'casos/semana',
            'escoreAumentoNaoCalibrado': 'escore 0–1, não calibrado',
        },
        'desempenhoHistorico': historical,
        'contagens': counts,
        'registros': records,
        'experimental': True,
        'aviso': forecast['aviso'],
        'notaMetodologica': (
            'Avaliação retrospectiva e exploratória, em período já examinado no '
            'desenvolvimento. Não representa validação prospectiva independente. '
            'Compara aumentos previstos e observados; não estima o número de casos.'
        ),
    }


def refresh_manifest(results):
    rows = [
        {'path': str(path.relative_to(results)), 'bytes': path.stat().st_size}
        for path in sorted(results.rglob('*'))
        if path.is_file() and path.stem != 'manifesto'
    ]
    with (results / 'manifesto.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['path', 'bytes'])
        writer.writeheader()
        writer.writerows(rows)
    write_json(results / 'manifesto.json', rows)


def export_retrospectives(results):
    results = Path(results)
    catalog = read_json(results / 'catalogo.json')
    prepared = [
        (entry, build_retrospective(results, entry))
        for entry in catalog['resultados']
    ]
    summary = []
    for entry, payload in prepared:
        relative = Path(entry['previsao']).parent / 'retrospectiva.json'
        write_json(results / relative, payload)
        entry['retrospectiva'] = relative.as_posix()
        summary.append({
            'modelo': entry['modelo'],
            'horizonteSemanas': entry['horizonteSemanas'],
            'semanasAvaliadas': len(payload['registros']),
            'acuraciaPercentual': payload['desempenhoHistorico']['acuraciaPercentual'],
            **payload['contagens'],
        })
    write_json(results / 'catalogo.json', catalog)
    write_json(results / 'retrospectiva/resumo.json', summary)
    refresh_manifest(results)
    return summary
