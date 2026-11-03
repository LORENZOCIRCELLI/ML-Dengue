from pathlib import Path
import copy
import hashlib
import json
import platform
import runpy
import shutil

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, log_loss
from sklearn.preprocessing import StandardScaler


VARIANTS = {
    'sem_ENSO': 'Sem ENSO',
    'ONI_continuo': 'ONI contínuo',
    'ENSO_binario': 'ENSO binário',
}
COLORS = {
    'sem_ENSO': '#2563EB',
    'ONI_continuo': '#D97706',
    'ENSO_binario': '#059669',
}
PRIMARY_METRICS = ['f1', 'pr_auc']
BOOTSTRAP_REPETITIONS = 1000
BOOTSTRAP_SEED = 72841
ONI_LAG_WEEKS = 4


class SequenceClassifier(nn.Module):
    def __init__(self, kind, input_size):
        super().__init__()
        self.input_size = input_size
        layer = nn.RNN if kind == 'rnn' else nn.LSTM
        self.recurrent = layer(
            input_size=input_size,
            hidden_size=24,
            num_layers=1,
            batch_first=True,
        )
        self.output = nn.Linear(24, 1)

    def forward(self, x):
        sequence, _ = self.recurrent(x.reshape(-1, 12, self.input_size))
        return self.output(sequence[:, -1, :]).squeeze(-1)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load_api(root):
    return runpy.run_path(str(root / 'v1/estudo.py'))


def prepare_inputs(df, base, variant, reference, output, api):
    features = base.copy()
    lags = {name: 1 for name in features}
    if variant == 'ONI_continuo':
        features['ONI'] = df.ONI.astype(float)
        lags['ONI'] = ONI_LAG_WEEKS
    elif variant == 'ENSO_binario':
        features['el_nino'] = (df.ONI >= 0.5).astype(float)
        features['la_nina'] = (df.ONI <= -0.5).astype(float)
        lags.update({'el_nino': ONI_LAG_WEEKS, 'la_nina': ONI_LAG_WEEKS})
    available = pd.DataFrame({
        name: features[name].shift(lags[name]) for name in features
    })
    samples = pd.read_csv(
        reference / 'data/particoes.csv',
        parse_dates=['data_emissao', 'data_alvo'],
    )
    cases = base.casos_dengue
    baseline = cases.shift(1).rolling(4).mean()
    for row in samples.itertuples():
        index = row.sample_id
        horizon = (row.data_alvo - row.data_emissao).days // 7
        assert row.data_emissao == df.dt_pri_sem.iloc[index]
        assert row.data_alvo == df.dt_pri_sem.iloc[index + horizon]
        assert row.media_referencia == baseline.iloc[index]
        assert row.casos_futuros == cases.iloc[index + horizon]
        assert row.target == int(row.casos_futuros >= 1.5 * row.media_referencia)
        expected = 'descartado_fronteira'
        if row.data_alvo <= pd.Timestamp(api['CONFIG']['train_end']):
            expected = 'treino'
        elif row.data_emissao > pd.Timestamp(api['CONFIG']['train_end']):
            if row.data_alvo <= pd.Timestamp(api['CONFIG']['validation_end']):
                expected = 'validacao'
        if row.data_emissao > pd.Timestamp(api['CONFIG']['validation_end']):
            expected = 'teste'
        assert row.split == expected and expected != 'descartado_fronteira'
    raw = np.stack([
        available.iloc[index - 11:index + 1].to_numpy()
        for index in samples.sample_id
    ])
    assert np.isfinite(raw).all()
    width = len(features.columns)
    mask = samples.split.eq('treino').to_numpy()
    scaler = StandardScaler().fit(raw[mask].reshape(-1, width))
    scaled = scaler.transform(raw.reshape(-1, width))
    scaled = scaled.reshape(len(raw), 12 * width).astype(np.float32)
    names = [
        f'{name}__tmenos{11 - offset + lags[name]}'
        for offset in range(12)
        for name in features
    ]
    arrays, targets, split_samples = {}, {}, {}
    base_positions = [
        index for index, name in enumerate(names)
        if name.split('__tmenos')[0] in api['FEATURES']
    ]
    for split in api['SPLITS']:
        mask = samples.split.eq(split).to_numpy()
        arrays[split] = scaled[mask]
        targets[split] = samples.loc[mask, 'target'].to_numpy(dtype=np.int64)
        split_samples[split] = samples.loc[mask].reset_index(drop=True)
        original = pd.read_csv(reference / f'data/{split}_padronizado.csv')
        np.testing.assert_array_equal(
            original.sample_id, split_samples[split].sample_id,
        )
        np.testing.assert_array_equal(original.target, targets[split])
        np.testing.assert_allclose(
            arrays[split][:, base_positions],
            original[[name for name in names if name.split('__tmenos')[0] in api['FEATURES']]],
            atol=1e-7,
            rtol=1e-6,
        )
        frame = pd.DataFrame(arrays[split], columns=names)
        frame.insert(0, 'sample_id', split_samples[split].sample_id)
        frame['target'] = targets[split]
        api['table'](output / f'data/{split}_padronizado', frame)
    assert split_samples['treino'].data_alvo.max() < split_samples['validacao'].data_emissao.min()
    assert split_samples['validacao'].data_alvo.max() < split_samples['teste'].data_emissao.min()
    api['table'](output / 'data/particoes', samples)
    api['table'](output / 'data/atributos_disponiveis', available)
    joblib.dump(scaler, output / 'scaler.joblib')
    api['write_json'](output / 'entradas.json', {
        'variant': variant,
        'base_features': api['FEATURES'],
        'features': list(features.columns),
        'flattened_features': names,
        'availability_lags_weeks': lags,
        'n_features': width,
        'sequence_length': 12,
        'scaler_fit': 'janelas do treino somente',
        'baseline_inputs_verified_against_v1': True,
    })
    return arrays, targets, split_samples, width


def train(kind, arrays, targets, directory, width, api):
    models, histories, selections = [], [], []
    artifact = directory / 'artifacts'
    artifact.mkdir(parents=True, exist_ok=True)
    for seed in api['SEEDS']:
        torch.manual_seed(seed)
        np.random.seed(seed)
        if kind == 'random_forest':
            best = -np.inf
            for trees in api['CONFIG']['forest_tree_counts']:
                candidate = RandomForestClassifier(
                    n_estimators=trees,
                    max_depth=6,
                    min_samples_leaf=2,
                    class_weight='balanced',
                    max_features='sqrt',
                    random_state=seed,
                    n_jobs=1,
                ).fit(arrays['treino'], targets['treino'])
                for split in ['treino', 'validacao']:
                    probability = candidate.predict_proba(arrays[split])[:, 1]
                    metrics = api['scores'](targets[split], probability)
                    histories.append({
                        'seed': seed, 'step': trees, 'split': split,
                        'loss': log_loss(targets[split], probability, labels=[0, 1]),
                        **metrics,
                    })
                    if split == 'validacao' and metrics['f1'] > best:
                        best = metrics['f1']
                        selected = trees
                        model = copy.deepcopy(candidate)
            joblib.dump(model, artifact / f'seed_{seed}.joblib')
            selections.append({
                'seed': seed, 'selected_step': selected,
                'selection': 'validation_f1',
            })
        else:
            model = SequenceClassifier(kind, width)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
            criterion = nn.BCEWithLogitsLoss()
            tensors = {
                split: torch.tensor(arrays[split])
                for split in ['treino', 'validacao']
            }
            labels = {
                split: torch.tensor(targets[split], dtype=torch.float32)
                for split in tensors
            }
            best_loss, stale, best_state = np.inf, 0, None
            for epoch in range(1, 151):
                model.train()
                optimizer.zero_grad()
                loss = criterion(model(tensors['treino']), labels['treino'])
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                model.eval()
                with torch.no_grad():
                    for split in tensors:
                        logits = model(tensors[split])
                        probability = torch.sigmoid(logits).numpy()
                        validation_loss = criterion(logits, labels[split]).item()
                        histories.append({
                            'seed': seed, 'step': epoch, 'split': split,
                            'loss': validation_loss,
                            **api['scores'](targets[split], probability),
                        })
                if validation_loss < best_loss - 1e-8:
                    best_loss = validation_loss
                    selected = epoch
                    best_state = copy.deepcopy(model.state_dict())
                    stale = 0
                else:
                    stale += 1
                if stale >= 20:
                    break
            model.load_state_dict(best_state)
            model.eval()
            torch.save({
                'state_dict': best_state,
                'model_type': kind,
                'seed': seed,
                'selected_epoch': selected,
                'stopped_epoch': epoch,
                'input_size': width,
                'hidden_size': 24,
                'sequence_length': 12,
                'selected_validation_loss': best_loss,
            }, artifact / f'seed_{seed}.pt')
            selections.append({
                'seed': seed, 'selected_step': selected,
                'stopped_epoch': epoch,
                'selection': 'validation_bce_loss',
                'selected_loss': best_loss,
            })
        models.append(model)
        print(f'    semente {seed}: selecionado {selected}', flush=True)
    history = pd.DataFrame(histories)
    api['table'](directory / 'metrics/historico_treinamento', history)
    api['table'](directory / 'metrics/selecao_por_semente', pd.DataFrame(selections))
    return models, history


def load_reference(kind, directory, api):
    models = []
    for seed in api['SEEDS']:
        if kind == 'random_forest':
            model = joblib.load(directory / f'artifacts/seed_{seed}.joblib')
        else:
            state = torch.load(
                directory / f'artifacts/seed_{seed}.pt',
                map_location='cpu', weights_only=False,
            )
            model = SequenceClassifier(kind, 6)
            model.load_state_dict(state['state_dict'])
            model.eval()
        models.append(model)
    return models


def evaluate_reference(root, horizon, kind, arrays, targets, directory, api):
    source = root / f'v1/results/horizontes/{horizon:02d}_semanas/{kind}'
    models = load_reference(kind, source, api)
    for split in api['SPLITS']:
        actual = api['predict'](kind, models, arrays[split])
        original = pd.read_csv(source / f'data/previsoes_{split}.csv')
        expected = original[[f'escore_seed_{seed}' for seed in api['SEEDS']]].to_numpy().T
        np.testing.assert_allclose(actual, expected, atol=2e-7, rtol=1e-6)
    for name in ['artifacts', 'metrics']:
        shutil.copytree(source / name, directory / name, dirs_exist_ok=True)
    history = pd.read_csv(source / 'metrics/historico_treinamento.csv')
    return models, history


def paired_bootstrap(y, baseline, candidate, horizon, seed):
    rng = np.random.default_rng(seed)
    n = len(y)
    length = max(12, horizon)
    blocks = int(np.ceil(n / length))
    samples = np.concatenate([
        rng.integers(0, n - length + 1, size=(BOOTSTRAP_REPETITIONS, 1))
        + np.arange(length)
        for _ in range(blocks)
    ], axis=1)[:, :n]
    valid = np.logical_and(y[samples].sum(axis=1) > 0, y[samples].sum(axis=1) < n)
    samples = samples[valid]
    distribution = {'f1': [], 'pr_auc': []}
    for indices in samples:
        labels = y[indices]
        values = {}
        for name, probability in [('base', baseline), ('candidate', candidate)]:
            p = probability[indices]
            predicted = p >= 0.5
            tp = np.sum(predicted & (labels == 1))
            fp = np.sum(predicted & (labels == 0))
            fn = np.sum(~predicted & (labels == 1))
            denominator = 2 * tp + fp + fn
            values[name] = {
                'f1': 2 * tp / denominator if denominator else 0.0,
                'pr_auc': average_precision_score(labels, p),
            }
        for metric in distribution:
            distribution[metric].append(values['candidate'][metric] - values['base'][metric])
    return {
        metric: {
            'ci95_low': float(np.quantile(values, 0.025)),
            'ci95_high': float(np.quantile(values, 0.975)),
            'block_weeks': length,
            'valid_resamples': len(values),
            'bootstrap_seed': seed,
        }
        for metric, values in distribution.items()
    }


def compare(results, api):
    metrics = pd.read_csv(results / 'comparacao/metricas_ensemble.csv')
    seed_metrics = pd.read_csv(results / 'comparacao/metricas_por_semente.csv')
    deltas, seed_deltas, intervals = [], [], []
    for horizon in api['HORIZONS']:
        for kind in api['MODELS']:
            base_rows = metrics.query('horizon_weeks == @horizon and model == @kind and variant == "sem_ENSO"')
            for variant in ['ONI_continuo', 'ENSO_binario']:
                added_rows = metrics.query('horizon_weeks == @horizon and model == @kind and variant == @variant')
                paired = base_rows.merge(added_rows, on='split', suffixes=('_base', '_added'), validate='one_to_one')
                for row in paired.itertuples():
                    for metric in api['METRICS']:
                        deltas.append({
                            'horizon_weeks': horizon, 'model': kind, 'variant': variant,
                            'split': row.split, 'metric': metric,
                            'baseline': getattr(row, metric + '_base'),
                            'candidate': getattr(row, metric + '_added'),
                            'delta': getattr(row, metric + '_added') - getattr(row, metric + '_base'),
                        })
                a = seed_metrics.query('horizon_weeks == @horizon and model == @kind and variant == "sem_ENSO"')
                b = seed_metrics.query('horizon_weeks == @horizon and model == @kind and variant == @variant')
                for row in a.merge(b, on=['split', 'seed'], suffixes=('_base', '_added'), validate='one_to_one').itertuples():
                    for metric in api['METRICS']:
                        seed_deltas.append({
                            'horizon_weeks': horizon, 'model': kind, 'variant': variant,
                            'split': row.split, 'seed': row.seed, 'metric': metric,
                            'delta': getattr(row, metric + '_added') - getattr(row, metric + '_base'),
                        })
                base_path = results / f'horizontes/{horizon:02d}_semanas/sem_ENSO/{kind}'
                added_path = results / f'horizontes/{horizon:02d}_semanas/{variant}/{kind}'
                base_predictions = pd.read_csv(base_path / 'data/previsoes_teste.csv')
                added_predictions = pd.read_csv(added_path / 'data/previsoes_teste.csv')
                pd.testing.assert_frame_equal(
                    base_predictions[['sample_id', 'data_emissao', 'data_alvo', 'target']],
                    added_predictions[['sample_id', 'data_emissao', 'data_alvo', 'target']],
                )
                bootstrap = paired_bootstrap(
                    base_predictions.target.to_numpy(),
                    base_predictions.escore_aumento.to_numpy(),
                    added_predictions.escore_aumento.to_numpy(), horizon,
                    BOOTSTRAP_SEED + horizon + list(api['MODELS']).index(kind),
                )
                for metric in PRIMARY_METRICS:
                    delta = next(row for row in deltas if row['horizon_weeks'] == horizon
                                 and row['model'] == kind and row['variant'] == variant
                                 and row['split'] == 'teste' and row['metric'] == metric)
                    intervals.append({**delta, **bootstrap[metric]})
                print(f'Intervalos: {horizon} semanas / {kind} / {variant}', flush=True)
    delta_frame = pd.DataFrame(deltas)
    seed_frame = pd.DataFrame(seed_deltas)
    interval_frame = pd.DataFrame(intervals)
    api['table'](results / 'comparacao/diferencas_ensemble', delta_frame)
    api['table'](results / 'comparacao/diferencas_por_semente', seed_frame)
    api['table'](results / 'comparacao/intervalos_pareados_teste', interval_frame)
    summary = seed_frame.groupby(['horizon_weeks', 'model', 'variant', 'split', 'metric']).agg(
        mean_delta=('delta', 'mean'), std_delta=('delta', 'std'),
        positive_seeds=('delta', lambda values: int((values > 1e-10).sum())),
        negative_seeds=('delta', lambda values: int((values < -1e-10).sum())),
        n_seeds=('delta', 'size'),
    ).reset_index()
    api['table'](results / 'comparacao/resumo_sementes', summary)
    plots(results, metrics, interval_frame, api)
    report(results, metrics, interval_frame, api)
    api['write_json'](results / 'comparacao/consolidado.json', {
        'schemaVersion': '1.0.0',
        'question': 'ONI/ENSO acrescenta desempenho à base epidemiológica e meteorológica local?',
        'primary_metrics': PRIMARY_METRICS,
        'metrics': api['records'](metrics),
        'paired_differences': api['records'](delta_frame),
        'paired_test_intervals': api['records'](interval_frame),
        'seed_stability': api['records'](summary),
        'limitations': limitations(),
        'style': {'font': 'DejaVu Sans', 'colors': COLORS, 'score_unit': '0–1'},
    })
    return metrics


def limitations():
    return [
        'Um município e uma divisão temporal; teste já examinado no desenvolvimento.',
        'Resultados retrospectivos e exploratórios; não validação prospectiva independente.',
        'Ausência de ganho consistente não demonstra equivalência nem ausência de efeito climático.',
        'ONI histórico da planilha, sem vintages ou datas originais de publicação; atraso de quatro semanas é hipótese.',
        'ONI usa médias trimestrais e pode sofrer revisões; atraso fixo não garante ausência de informação revisada.',
        'Indicadores por limiares semanais não identificam episódios ENSO oficiais com persistência.',
        'Intervalos percentis por blocos são exploratórios, condicionados aos modelos fixos, sem correção por multiplicidade.',
        'Blocos preservam dependência local, mas não asseguram estacionariedade ou independência entre epidemias.',
        'DP entre cinco sementes mede instabilidade de treinamento, não incerteza em novos anos.',
        'Mais entradas mudam a contagem de parâmetros das redes e o número implícito de atributos do RF com sqrt.',
        'A análise mede ganho condicional às variáveis locais, não efeito causal total de ENSO sobre dengue.',
    ]


def plots(results, metrics, intervals, api):
    figures = results / 'comparacao/figuras'
    for split in ['validacao', 'teste']:
        for metric in ['f1', 'pr_auc', 'recall', 'accuracy', 'roc_auc', 'precision']:
            fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True)
            for ax, (kind, name) in zip(axes, api['MODELS'].items()):
                for variant, label in VARIANTS.items():
                    rows = metrics.query('split == @split and model == @kind and variant == @variant').sort_values('horizon_weeks')
                    ax.plot(rows.horizon_weeks, rows[metric], marker='o', color=COLORS[variant], label=label)
                ax.set(title=name, xlabel='Horizonte (semanas)', ylabel='Escore (0–1)', xticks=api['HORIZONS'], ylim=(0, 1.03))
                ax.legend(fontsize=8)
            fig.suptitle(f'Comparação ENSO — {api["METRICS"][metric]} — {api["SPLITS"][split]}')
            api['figure'](figures / f'{split}_{metric}', fig)
    for metric in PRIMARY_METRICS:
        fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
        for ax, (kind, name) in zip(axes, api['MODELS'].items()):
            for variant, offset in [('ONI_continuo', -0.18), ('ENSO_binario', 0.18)]:
                rows = intervals.query('model == @kind and variant == @variant and metric == @metric').sort_values('horizon_weeks')
                x = np.arange(4) + offset
                ax.vlines(x, rows.ci95_low, rows.ci95_high, color=COLORS[variant], linewidth=2)
                ax.scatter(x, rows.delta, color=COLORS[variant], label=VARIANTS[variant], zorder=3)
            ax.axhline(0, color='#64748B', linestyle='--')
            ax.set(title=name, xlabel='Horizonte (semanas)', ylabel='Diferença de escore (variante − sem ENSO)', xticks=np.arange(4), xticklabels=api['HORIZONS'])
            ax.legend(fontsize=8)
        fig.suptitle(f'Teste histórico — Δ {api["METRICS"][metric]} e intervalo exploratório de 95% por blocos')
        api['figure'](figures / f'diferencas_{metric}_intervalos', fig)


def report(results, metrics, intervals, api):
    text = '# Comparação consolidada ONI/ENSO\n\n'
    text += 'Três variantes, três modelos e quatro horizontes. Mesmas amostras, alvos, datas, sementes, '
    text += 'padronização no treino, regras de seleção e limiar 0,5. A base sem ENSO é a v1 original, '
    text += 'com checkpoints recarregados e previsões reproduzidas antes da comparação.\n\n'
    text += 'F1 e PR-AUC (Average Precision) são os indicadores principais definidos no protocolo. '
    text += 'Não se escolhe uma variante ou configuração pelo teste. Não há refit.\n\n'
    for horizon in api['HORIZONS']:
        text += f'## Horizonte de {horizon} semanas — teste histórico\n\n'
        text += '| Modelo | Variante | F1 | PR-AUC | Recall | Acurácia |\n|---|---|---:|---:|---:|---:|\n'
        for kind, name in api['MODELS'].items():
            for variant, label in VARIANTS.items():
                row = metrics.query('horizon_weeks == @horizon and model == @kind and variant == @variant and split == "teste"').iloc[0]
                text += f'| {name} | {label} | {row.f1:.3f} | {row.pr_auc:.3f} | {row.recall:.3f} | {row.accuracy:.3f} |\n'
        text += '\n'
    text += '## Diferenças pareadas e incerteza\n\n'
    text += 'As diferenças são variante menos sem ENSO. O bootstrap móvel pareado usa as mesmas '
    text += 'semanas nas variantes e 1.000 reamostragens, em blocos de max(12, horizonte) semanas. '
    text += 'Reamostras sem ambas as classes são excluídas, com contagem registrada. Os intervalos '
    text += 'são percentis de 95%, condicionados aos modelos ajustados. Não são testes de equivalência '
    text += 'nem intervalos simultâneos para todos os contrastes.\n\n'
    text += '| Horizonte | Modelo | Variante | Métrica | Δ | Intervalo exploratório 95% |\n|---:|---|---|---|---:|---|\n'
    for row in intervals.itertuples():
        text += f'| {row.horizon_weeks} | {api["MODELS"][row.model]} | {VARIANTS[row.variant]} | {row.metric} | {row.delta:+.3f} | [{row.ci95_low:+.3f}; {row.ci95_high:+.3f}] |\n'
    text += '\n## Limitações e interpretação\n\n'
    text += '\n'.join('- ' + item for item in limitations())
    text += '\n\nNão se deve concluir antecipadamente que ONI/ENSO ajuda ou não ajuda. '
    text += 'Diferenças devem ser descritas por modelo, horizonte, validação/teste e estabilidade entre sementes. '
    text += 'Mesmo um intervalo que inclui zero não prova ausência de benefício.\n\n'
    text += '## Referências metodológicas\n\n'
    text += '- NOAA/CPC — definição e revisões do ONI: https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v5/\n'
    text += '- Hyndman e Athanasopoulos — bootstrap por blocos em séries temporais: https://otexts.com/fpp3/bootstrap.html\n'
    (results / 'relatorio.md').write_text(text, encoding='utf-8')


def run_study(root):
    root = Path(root).resolve()
    results = root / 'comparacao_ENSO/results'
    results.mkdir(parents=True, exist_ok=True)
    api = load_api(root)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 11,
        'axes.grid': True, 'grid.alpha': 0.2,
        'axes.spines.top': False, 'axes.spines.right': False,
    })
    df, base, audit = api['load_data'](root)
    assert np.isfinite(df.ONI.to_numpy()).all()
    original_config = read_json(root / 'v1/results/configuracao.json')
    assert audit['source_sha256'] == original_config['audit']['source_sha256']
    for key, value in api['CONFIG'].items():
        assert value == original_config[key], key
    protocol = {
        'base_protocol': api['CONFIG'],
        'variants': VARIANTS,
        'oni_lag_weeks': ONI_LAG_WEEKS,
        'enso_encoding': {'el_nino': 'ONI >= +0.5', 'la_nina': 'ONI <= -0.5', 'neutral': 'ambos zero'},
        'primary_metrics': PRIMARY_METRICS,
        'bootstrap': {'repetitions': BOOTSTRAP_REPETITIONS, 'seed': BOOTSTRAP_SEED, 'block_weeks': 'max(12, horizonte)'},
        'baseline_reused_with_prediction_verification': True,
        'variants_selected_by_test': False,
        'source_audit': audit,
        'code_sha256': digest(__file__),
        'v1_code_sha256': digest(root / 'v1/estudo.py'),
        'python': platform.python_version(),
        'versions': original_config['versions'],
        'limitations': limitations(),
    }
    api['write_json'](results / 'protocolo.json', protocol)
    run_id = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    api['table'](results / 'data/dataset_base', pd.concat([
        df[['dt_pri_sem', 'ONI']], base,
    ], axis=1))
    all_metrics, all_seed_metrics = [], []
    for horizon in api['HORIZONS']:
        reference = root / f'v1/results/horizontes/{horizon:02d}_semanas'
        for variant in VARIANTS:
            output = results / f'horizontes/{horizon:02d}_semanas/{variant}'
            arrays, targets, samples, width = prepare_inputs(df, base, variant, reference, output, api)
            for kind in api['MODELS']:
                directory = output / kind
                completed = directory / 'concluido.json'
                if completed.exists() and read_json(completed).get('run_id') == run_id:
                    print(f'Reutilizando execução idêntica: {horizon} / {variant} / {kind}', flush=True)
                    frame = pd.read_csv(directory / 'metrics/metricas_ensemble.csv')
                else:
                    print(f'Executando: {horizon} semanas / {variant} / {kind}', flush=True)
                    if variant == 'sem_ENSO':
                        models, history = evaluate_reference(root, horizon, kind, arrays, targets, directory, api)
                    else:
                        models, history = train(kind, arrays, targets, directory, width, api)
                    title = f'{api["MODELS"][kind]} — {VARIANTS[variant]} — {horizon} semanas'
                    frame, _, matrices, curves = api['evaluate'](
                        kind, models, arrays, targets, samples, directory, title, history,
                    )
                    api['write_json'](directory / 'metricas.json', {
                        'modelo': kind, 'variant': variant, 'horizonteSemanas': horizon,
                        'metricas': api['records'](frame),
                        'matrizesConfusao': matrices, 'curvasRoc': curves,
                    })
                    api['write_json'](directory / 'configuracao.json', {
                        **protocol, 'model': kind, 'variant': variant,
                        'horizon_weeks': horizon, 'input_size': width,
                        'flattened_size': 12 * width,
                        'parameter_count': None if kind == 'random_forest' else sum(parameter.numel() for parameter in models[0].parameters()),
                        'reference_artifacts': str((reference / kind).relative_to(root)) if variant == 'sem_ENSO' else None,
                    })
                    api['write_json'](completed, {'run_id': run_id})
                all_metrics.extend({'horizon_weeks': horizon, 'variant': variant, 'model': kind, **row} for row in api['records'](frame))
                seed_frame = pd.read_csv(directory / 'metrics/metricas_por_semente.csv')
                all_seed_metrics.extend({'horizon_weeks': horizon, 'variant': variant, 'model': kind, **row} for row in api['records'](seed_frame))
                print(f'  F1 teste: {frame.loc[frame.split.eq("teste"), "f1"].iloc[0]:.4f}', flush=True)
    api['table'](results / 'comparacao/metricas_ensemble', pd.DataFrame(all_metrics))
    api['table'](results / 'comparacao/metricas_por_semente', pd.DataFrame(all_seed_metrics))
    summary = compare(results, api)
    api['table'](results / 'manifesto', pd.DataFrame([
        {'path': str(path.relative_to(results)), 'bytes': path.stat().st_size}
        for path in sorted(results.rglob('*'))
        if path.is_file() and path.stem != 'manifesto'
    ]))
    return summary


if __name__ == '__main__':
    run_study(Path(__file__).resolve().parents[1])
