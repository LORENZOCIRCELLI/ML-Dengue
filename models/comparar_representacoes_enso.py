"""Prepara ONI contínuo e compara três representações somente na validação."""
from pathlib import Path
import copy
import importlib.util
import hashlib
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
from sklearn.preprocessing import StandardScaler


def stability_api():
    path = Path(__file__).with_name('avaliar_estabilidade.py')
    spec = importlib.util.spec_from_file_location('dengue_stability', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_continuous(project_root):
    root = Path(project_root).resolve()
    directory = root / 'experimento_ONI_continuo'
    results = directory / 'results'
    shared = results / 'data'
    shared.mkdir(parents=True, exist_ok=True)
    reference = root / 'experimento_sem_ONI/results'
    meta = json.loads((reference / 'lstm/metadata.json').read_text())
    # Mantém os rótulos/datas congelados; somente treino e validação são preparados.
    samples = pd.read_csv(reference / 'data/amostras_e_particoes.csv',
        parse_dates=['data_emissao', 'data_alvo', 'data_ultimo_caso'])
    samples = samples[samples.split.isin(['treino', 'validacao'])].set_index('sample_id')
    raw = pd.read_excel(root / meta['dataset'])
    raw['dt_pri_sem'] = pd.to_datetime(raw.dt_pri_sem)
    raw = raw.sort_values('dt_pri_sem').reset_index(drop=True)
    raw = raw[raw.dt_pri_sem <= pd.Timestamp(meta['validation_end'])].copy()
    assert raw.dt_pri_sem.diff().dropna().eq(pd.Timedelta(weeks=1)).all()
    features = pd.DataFrame({'casos_dengue': raw['n dengue'].astype(float),
        'temperatura_media': raw['media_temperatura_semana'],
        'umidade_media': raw['media_umidade_semana'], 'chuva_total': raw['chuva_total_mm'],
        'semana_sin': np.sin(2*np.pi*raw['semana_epidemiologica']/52),
        'semana_cos': np.cos(2*np.pi*raw['semana_epidemiologica']/52), 'ONI': raw.ONI})
    lags = {f: 4 if f == 'ONI' else 1 for f in features}
    available = pd.DataFrame({f: features[f].shift(lags[f]) for f in features})
    length = meta['sequence_length']
    sequences = np.stack([available.iloc[i-length+1:i+1].to_numpy() for i in samples.index])
    assert np.isfinite(sequences).all()
    scaler = StandardScaler().fit(sequences[samples.split.eq('treino')].reshape(-1, len(features.columns)))
    scaled = scaler.transform(sequences.reshape(-1, len(features.columns))).reshape(sequences.shape).astype(np.float32)
    names = [f'{col}__tmenos{length-1-step+lags[col]}' for step in range(length) for col in features]
    # Verificação do alvo e das fronteiras, sem examinar o teste.
    for i, row in samples.iterrows():
        mean = raw['n dengue'].iloc[i-4:i].mean()
        assert np.isclose(mean, row.media_casos_referencia)
        assert row.target == int(raw['n dengue'].iloc[i+4] >= 1.5*mean)
    assert samples.loc[samples.split.eq('treino'), 'data_alvo'].max() < samples.loc[samples.split.eq('validacao'), 'data_emissao'].min()
    raw[['dt_pri_sem', 'n dengue', 'media_temperatura_semana',
         'media_umidade_semana', 'chuva_total_mm', 'ONI']].to_csv(shared/'dataset_origem.csv', index=False)
    samples.to_csv(shared/'amostras_e_particoes.csv')
    available.rename_axis('sample_id').to_csv(shared/'atributos_disponiveis.csv')
    summary = samples.groupby('split', sort=False).agg(amostras=('target','size'),
        positivos=('target','sum'), prevalencia=('target','mean'),
        primeira_emissao=('data_emissao','min'), ultima_emissao=('data_emissao','max'),
        primeiro_alvo=('data_alvo','min'), ultimo_alvo=('data_alvo','max'))
    summary.to_csv(shared/'resumo_particoes.csv')
    metadata = {}
    for kind in ['random_forest', 'rnn', 'lstm']:
        model_dir = results/kind
        for name in ['data', 'artifacts']:
            (model_dir/name).mkdir(parents=True, exist_ok=True)
        current = copy.deepcopy(meta)
        current.update({'model': kind, 'experiment': directory.name, 'include_oni': True,
            'oni_representation': 'continuous', 'input_features': features.columns.tolist(),
            'features': names, 'availability_lags_weeks': lags,
            'selection_metric': 'validation_loss_for_networks_f1_for_rf',
            'preparation_scope': 'treino_e_validacao_somente',
            'status': 'inputs_for_validation_repeats',
            'data_reference': 'mesmos alvos e partições congelados do experimento sem ONI'})
        current.pop('selected_step', None)
        current['units']['ONI'] = '°C (anomalia contínua da coluna de origem)'
        (model_dir/'metadata.json').write_text(json.dumps(current, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        metadata[kind] = current
        joblib.dump(scaler, model_dir/'artifacts/scaler.joblib')
        for split in ['treino', 'validacao']:
            mask = samples.split.eq(split).to_numpy()
            frame = pd.DataFrame(scaled[mask].reshape(mask.sum(), -1), columns=names, index=samples.index[mask])
            frame.index.name = 'sample_id'
            frame['target'] = samples.loc[mask, 'target'].to_numpy()
            old = pd.read_csv(reference/kind/'data'/f'{split}_padronizado.csv').set_index('sample_id')
            assert frame.index.equals(old.index)
            np.testing.assert_allclose(frame[old.columns], old, rtol=1e-6, atol=1e-6)
            frame.to_csv(model_dir/'data'/f'{split}_padronizado.csv')
    # Uma reexecução preserva até a atualização os campos de resultados já existentes.
    app_path = results/'app_resultados.json'
    app = json.loads(app_path.read_text()) if app_path.exists() else {'graficos': [], 'tabelas': {}}
    app.update({'schemaVersion': '1.0.0', 'experimento': directory.name,
        'representacaoONI': 'continuo', 'metadadosModelos': metadata,
        'estilo': {'fonte': 'DejaVu Sans', 'cores': meta['colors']},
        'escopo': 'treino e validação; teste não avaliado'})
    api = stability_api()
    for path in sorted(results.rglob('*.csv')):
        if 'json' in path.relative_to(results).parts or 'estabilidade_perda' in path.parts or path.name == 'manifest.csv':
            continue
        data = api.records(pd.read_csv(path))
        relative = path.relative_to(results).with_suffix('.json')
        api.write_json(results/'json'/relative, data)
        app['tabelas'][str(path.relative_to(results).with_suffix(''))] = data
    api.write_json(app_path, app)
    return summary


def compare_representations(project_root):
    root = Path(project_root).resolve()
    variants = {'sem_ENSO': 'experimento_sem_ONI', 'ENSO_binario': 'experimento_com_ONI',
                'ONI_continuo': 'experimento_ONI_continuo'}
    api = stability_api()
    frames, summaries = {}, []
    for variant, experiment in variants.items():
        directory = root/experiment/'results/estabilidade_perda'
        payload = json.loads((directory/'app_estabilidade.json').read_text())
        assert payload['network_selection'] == 'loss' and payload['seeds'] == api.SEEDS
        frames[variant] = pd.read_csv(directory/'metricas_validacao_por_semente.csv')
        summary = pd.read_csv(directory/'resumo_validacao.csv')
        summary.insert(0, 'representation', variant)
        summaries.append(summary)
    summary = pd.concat(summaries, ignore_index=True)
    paired_rows = []
    for reference in ['sem_ENSO', 'ENSO_binario']:
        a = frames[reference].query("model != 'tendencia_recente'")
        b = frames['ONI_continuo'].query("model != 'tendencia_recente'")
        pairs = a.merge(b, on=['model','seed'], suffixes=('_reference','_continuous'), validate='one_to_one')
        assert len(pairs) == 15
        for _, row in pairs.iterrows():
            assert row.n_reference == row.n_continuous and row.positive_reference == row.positive_continuous
            for metric in api.METRICS:
                paired_rows.append({'model': row.model, 'seed': int(row.seed), 'reference': reference,
                    'metric': metric, 'reference_value': row[metric+'_reference'],
                    'continuous_value': row[metric+'_continuous'],
                    'delta': row[metric+'_continuous']-row[metric+'_reference']})
    paired = pd.DataFrame(paired_rows)
    delta = paired.groupby(['model','reference','metric'], sort=False).agg(
        n_pairs=('delta','size'), mean_delta=('delta','mean'), std_delta=('delta','std'),
        positive_deltas=('delta',lambda v: int((v > 1e-10).sum())))
    delta = delta.reset_index()
    results = root/'experimento_ONI_continuo/results'
    out = results/'estabilidade_perda'
    summary.to_csv(out/'comparacao_tres_representacoes.csv', index=False)
    paired.to_csv(out/'diferencas_por_semente_representacoes.csv', index=False)
    delta.to_csv(out/'resumo_diferencas_representacoes.csv', index=False)
    colors = {'sem_ENSO': '#2563EB', 'ENSO_binario': '#D97706', 'ONI_continuo': '#059669'}
    labels = {'sem_ENSO': 'Sem ENSO', 'ENSO_binario': 'ENSO binário', 'ONI_continuo': 'ONI contínuo'}
    graphs = []
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    for ax, metric in zip(axes.flat, api.METRICS):
        series = []
        for variant, offset in zip(variants, [-.25, 0, .25]):
            rows = summary[(summary.representation == variant)&(summary.metric == metric)].set_index('model').loc[
                ['random_forest','rnn','lstm']]
            ax.bar(np.arange(3)+offset, rows['mean'], width=.25, yerr=rows['std'], capsize=3,
                   color=colors[variant], label=labels[variant])
            series.append({'id': variant, 'titulo': labels[variant], 'cor': colors[variant],
                'pontos': [{'x': api.MODEL_NAMES[k], 'y': float(row['mean']), 'erroY': float(row['std'])}
                           for k, row in rows.iterrows()]})
        baseline = float(summary[(summary.representation=='sem_ENSO')&(summary.model=='tendencia_recente')&
                                  (summary.metric==metric)]['mean'].iloc[0])
        ax.axhline(baseline, color='#64748B', linestyle='--', label='Tendência recente')
        ax.set(xticks=np.arange(3), xticklabels=['Random Forest','RNN','LSTM'],
               title=api.LABELS[metric], ylabel='Escore (0–1)', ylim=(0,1.08))
        ax.legend(fontsize=8)
        graphs.append({'id': f'estabilidade_perda/representacoes/{metric}', 'titulo': api.LABELS[metric],
            'tipo': 'barras_agrupadas', 'eixoX': 'Modelo', 'eixoY': 'Escore (0–1)',
            'series': series, 'referencia': {'titulo': 'Tendência recente', 'valor': baseline},
            'barrasErro': 'DP entre cinco sementes; não intervalo de confiança'})
    fig.suptitle('Validação — mesma seleção pela perda — três representações ENSO', fontsize=15)
    api.save_figure(fig, out/'figures', '03_comparacao_tres_representacoes')
    report = '# ONI contínuo, ENSO binário e ausência de ENSO\n\n'
    report += 'Validação somente, com cinco sementes fixas. Redes selecionadas pela menor perda BCE; '
    report += 'RF pelo maior F1. Limiar 0,5, mesmo alvo de quatro semanas, mesmas datas e entradas de base. '
    report += 'ONI contínuo e indicadores binários têm atraso de quatro semanas.\n\n'
    report += '| Modelo | Sem ENSO — F1 média ± DP | ENSO binário — F1 média ± DP | ONI contínuo — F1 média ± DP |\n|---|---:|---:|---:|\n'
    for kind in ['random_forest','rnn','lstm','tendencia_recente']:
        line = [api.MODEL_NAMES[kind]]
        for variant in variants:
            row = summary[(summary.representation==variant)&(summary.model==kind)&(summary.metric=='f1')].iloc[0]
            line.append(f'{row["mean"]:.3f} ± {row["std"]:.3f}')
        report += '| '+' | '.join(line)+' |\n'
    report += ('\nA tendência recente é determinística (uma execução). DP de cinco sementes não é intervalo '
               'de confiança nem variação em novos anos. A validação seleciona checkpoints e já orientou '
               'mudanças anteriores: esta comparação é exploratória e não confirma generalização ou causalidade. '
               'Nenhum ajuste foi escolhido pelo teste, e o teste não foi reavaliado nesta rodada.\n')
    (out/'comparacao_interpretacao.md').write_text(report, encoding='utf-8')
    payload = json.loads((out/'app_estabilidade.json').read_text())
    payload['comparacaoRepresentacoes'] = api.records(summary)
    payload['diferencasPorSementeRepresentacoes'] = paired_rows
    payload['resumoDiferencasRepresentacoes'] = api.records(delta)
    payload['graficos'] = [g for g in payload['graficos'] if not g['id'].startswith('estabilidade_perda/representacoes/')]+graphs
    api.update_exports(results, payload, 'estabilidade_perda')
    return summary


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    prepare_continuous(root)
    stability_api().run_experiment(root/'experimento_ONI_continuo', network_selection='loss')
    compare_representations(root)
