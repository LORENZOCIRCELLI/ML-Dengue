"""Repete o protocolo existente usando somente treino e validação.

O teste histórico e os modelos da execução inicial não são modificados.
"""
from pathlib import Path
import copy
import hashlib
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
from torch import nn
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (f1_score, precision_score, recall_score, accuracy_score,
                             roc_auc_score, average_precision_score, log_loss)

SEEDS = [42, 123, 2025, 7, 99]
METRICS = ['f1', 'precision', 'recall', 'roc_auc', 'pr_auc', 'accuracy']
LABELS = {'f1': 'F1', 'precision': 'Precisão', 'recall': 'Recall',
          'roc_auc': 'ROC-AUC', 'pr_auc': 'PR-AUC (Average Precision)', 'accuracy': 'Acurácia'}
MODEL_NAMES = {'random_forest': 'Random Forest', 'rnn': 'RNN', 'lstm': 'LSTM',
               'tendencia_recente': 'Tendência recente'}
MODEL_COLORS = {'random_forest': '#2563EB', 'rnn': '#D97706', 'lstm': '#059669',
                'tendencia_recente': '#64748B'}


def records(frame):
    return json.loads(frame.replace([np.inf, -np.inf], np.nan).to_json(
        orient='records', force_ascii=False, double_precision=15))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def scores(target, score, threshold=.5):
    prediction = (np.asarray(score) >= threshold).astype(int)
    return {'f1': f1_score(target, prediction, zero_division=0),
            'precision': precision_score(target, prediction, zero_division=0),
            'recall': recall_score(target, prediction, zero_division=0),
            'accuracy': accuracy_score(target, prediction),
            'roc_auc': roc_auc_score(target, score),
            # AP usa a curva precisão-recall em degraus; não integração trapezoidal.
            'pr_auc': average_precision_score(target, score),
            'predicted_positive': int(prediction.sum()), 'n': len(target),
            'positive': int(np.sum(target)), 'prevalence': float(np.mean(target))}


def save_figure(fig, directory, name):
    fig.tight_layout()
    for suffix in ['png', 'svg']:
        fig.savefig(directory / f'{name}.{suffix}', dpi=160, bbox_inches='tight')
    plt.show()
    plt.close(fig)


class SequenceClassifier(nn.Module):
    def __init__(self, kind, n_features):
        super().__init__()
        self.recurrent = (nn.RNN if kind == 'rnn' else nn.LSTM)(
            input_size=n_features, hidden_size=24, num_layers=1, batch_first=True)
        self.output = nn.Linear(24, 1)

    def forward(self, inputs):
        sequence, _ = self.recurrent(inputs)
        return self.output(sequence[:, -1, :]).squeeze(-1)


def update_exports(results, payload, out_name='estabilidade'):
    """Atualiza JSONs e inventário sem recalcular métricas do teste."""
    results = Path(results)
    stability = results / out_name
    write_json(stability / 'app_estabilidade.json', payload)
    app_path = results / 'app_resultados.json'
    app = json.loads(app_path.read_text(encoding='utf-8'))
    app[out_name] = payload
    app['graficos'] = [g for g in app['graficos'] if not g['id'].startswith(f'{out_name}/')]
    app['graficos'].extend(payload['graficos'])
    for path in sorted(stability.glob('*.csv')):
        data = records(pd.read_csv(path))
        write_json(results / 'json' / out_name / f'{path.stem}.json', data)
        app['tabelas'][f'{out_name}/{path.stem}'] = data
    write_json(app_path, app)
    inventory = [{'path': str(p.relative_to(results)), 'bytes': p.stat().st_size}
                 for p in sorted(results.rglob('*')) if p.is_file() and p.name != 'manifest.csv']
    pd.DataFrame(inventory).to_csv(results / 'manifest.csv', index=False)


def run_experiment(experiment_dir, network_selection='f1'):
    if network_selection not in ['f1', 'loss']:
        raise ValueError('network_selection deve ser f1 ou loss')
    experiment_dir = Path(experiment_dir).resolve()
    results = experiment_dir / 'results'
    out_name = 'estabilidade' if network_selection == 'f1' else 'estabilidade_perda'
    out = results / out_name
    figures = out / 'figures'
    artifacts = out / 'artifacts'
    for p in [out, figures, artifacts]:
        p.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
        'figure.facecolor': 'white', 'axes.facecolor': 'white', 'axes.grid': True,
        'grid.alpha': .2, 'axes.spines.top': False, 'axes.spines.right': False})
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    metric_rows, history_rows, prediction_rows, diagnostics = [], [], [], []
    input_hashes = {}

    for kind in ['random_forest', 'rnn', 'lstm']:
        meta_path = results / kind / 'metadata.json'
        meta = json.loads(meta_path.read_text())
        arrays, targets, ids = {}, {}, {}
        for split in ['treino', 'validacao']:
            path = results / kind / 'data' / f'{split}_padronizado.csv'
            frame = pd.read_csv(path)
            input_hashes[f'{kind}/{split}'] = hashlib.sha256(path.read_bytes()).hexdigest()
            arrays[split] = frame[meta['features']].to_numpy(dtype=np.float32)
            targets[split] = frame.target.to_numpy(dtype=np.int64)
            ids[split] = frame.sample_id.to_numpy(dtype=int)
            assert set(targets[split]) == {0, 1}
        for seed in SEEDS:
            np.random.seed(seed)
            torch.manual_seed(seed)
            if kind == 'random_forest':
                best_score = -np.inf
                for trees in [25, 50, 100, 200]:
                    candidate = RandomForestClassifier(n_estimators=trees, max_depth=6,
                        min_samples_leaf=2, class_weight='balanced', random_state=seed, n_jobs=1)
                    candidate.fit(arrays['treino'], targets['treino'])
                    for split in ['treino', 'validacao']:
                        prob = candidate.predict_proba(arrays[split])[:, 1]
                        metric = scores(targets[split], prob)
                        history_rows.append({'model': kind, 'seed': seed, 'step': trees,
                            'split': split, 'phase': 'protocolo_original',
                            'loss': log_loss(targets[split], prob, labels=[0, 1]), **metric})
                        if split == 'validacao' and metric['f1'] > best_score:
                            best_score = metric['f1']
                            selected_step = trees
                            model = copy.deepcopy(candidate)
                probability = model.predict_proba(arrays['validacao'])[:, 1]
                joblib.dump(model, artifacts / f'{kind}_seed_{seed}.joblib')
            else:
                n_features = len(meta['input_features'])
                tensors = {s: torch.tensor(a.reshape(len(a), meta['sequence_length'], n_features))
                           for s, a in arrays.items()}
                labels = {s: torch.tensor(y, dtype=torch.float32) for s, y in targets.items()}
                model = SequenceClassifier(kind, n_features)
                optimizer = torch.optim.Adam(model.parameters(), lr=.003)
                criterion = nn.BCEWithLogitsLoss()
                best_score, stale, stopped_epoch = -np.inf, 0, None
                best_validation_loss = np.inf
                best_state = None
                # Continuação fixa somente para diagnosticar a LSTM de semente 42.
                # Ela não altera o checkpoint nem entra na comparação principal.
                continuation = kind == 'lstm' and seed == 42
                local_history = []
                for epoch in range(1, 151):
                    model.train()
                    optimizer.zero_grad()
                    loss = criterion(model(tensors['treino']), labels['treino'])
                    loss.backward()
                    nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.)
                    optimizer.step()
                    model.eval()
                    with torch.no_grad():
                        for split in ['treino', 'validacao']:
                            logits = model(tensors[split])
                            prob = torch.sigmoid(logits).numpy()
                            metric = scores(targets[split], prob)
                            row = {'model': kind, 'seed': seed, 'step': epoch, 'split': split,
                                'phase': 'diagnostico_continuacao' if stopped_epoch else (
                                    'protocolo_original' if network_selection == 'f1' else 'selecao_por_perda'),
                                'loss': criterion(logits, labels[split]).item(), **metric}
                            history_rows.append(row)
                            local_history.append(row)
                            if split == 'validacao':
                                val_f1 = metric['f1']
                                val_loss = row['loss']
                    if stopped_epoch is None:
                        improvement = (val_f1 > best_score + 1e-8 if network_selection == 'f1'
                                       else val_loss < best_validation_loss - 1e-8)
                        if improvement:
                            best_score, selected_step = val_f1, epoch
                            best_validation_loss = val_loss
                            best_state = copy.deepcopy(model.state_dict())
                            stale = 0
                        else:
                            stale += 1
                        if stale >= 20:
                            stopped_epoch = epoch
                    if stopped_epoch and not continuation:
                        break
                stopped_epoch = stopped_epoch or epoch
                if continuation:
                    valid_history = [h for h in local_history if h['split'] == 'validacao']
                    stopped = next(h for h in valid_history if h['step'] == stopped_epoch)
                    later = [h for h in valid_history if h['step'] > stopped_epoch]
                    diagnostics.append({'model': kind, 'seed': seed, 'selected_epoch': selected_step,
                        'stopped_epoch': stopped_epoch, 'initial_validation_loss': valid_history[0]['loss'],
                        'stopped_validation_loss': stopped['loss'],
                        'stopped_validation_f1': stopped['f1'],
                        'stopped_predicted_positive': stopped['predicted_positive'],
                        'last_diagnostic_epoch': epoch, 'last_diagnostic_validation_loss': valid_history[-1]['loss'],
                        'last_diagnostic_validation_f1': valid_history[-1]['f1'],
                        'best_later_validation_f1': max((h['f1'] for h in later), default=stopped['f1']),
                        'diagnostic_changes_primary_model': False})
                model.load_state_dict(best_state)
                model.eval()
                with torch.no_grad():
                    probability = torch.sigmoid(model(tensors['validacao'])).numpy()
                torch.save({'state_dict': model.state_dict(), 'model_type': kind,
                    'input_size': n_features, 'hidden_size': 24, 'sequence_length': meta['sequence_length'],
                    'seed': seed, 'selected_epoch': selected_step, 'stopped_epoch': stopped_epoch,
                    'network_selection': network_selection, 'selected_validation_loss': best_validation_loss},
                    artifacts / f'{kind}_seed_{seed}.pt')
            metric_rows.append({'experiment': experiment_dir.name, 'model': kind, 'seed': seed,
                'selected_step': selected_step, **scores(targets['validacao'], probability)})
            prediction_rows.extend({'model': kind, 'seed': seed, 'sample_id': int(i), 'target': int(y),
                'score': float(p), 'prediction': int(p >= .5), 'threshold': .5,
                'score_kind': 'probabilidade_modelo_nao_calibrada'}
                for i, y, p in zip(ids['validacao'], targets['validacao'], probability))
            print(experiment_dir.name, kind, seed, 'F1 validação =', round(metric_rows[-1]['f1'], 4), flush=True)

    # Referência fixa: extrapola a diferença entre médias de dois blocos de quatro semanas.
    # Nenhum parâmetro dessa referência é escolhido pelos resultados.
    meta = json.loads((results / 'lstm/metadata.json').read_text())
    raw = pd.read_csv(results / 'data/dataset_origem.csv', parse_dates=['dt_pri_sem'])
    raw = raw.loc[raw.dt_pri_sem <= pd.Timestamp(meta['validation_end'])].copy()
    assert raw.index.equals(pd.RangeIndex(len(raw)))
    cases = raw['n dengue'].astype(float)
    recent = cases.shift(1).rolling(4).mean()
    previous = cases.shift(5).rolling(4).mean()
    slope = (recent - previous) / 4
    forecast = np.maximum(0, cases.shift(1) + (meta['horizon_weeks'] + 1) * slope)
    growth_score = forecast / recent
    baseline_ids = ids['validacao']
    baseline_score = growth_score.loc[baseline_ids].to_numpy()
    assert np.isfinite(baseline_score).all()
    baseline_target = targets['validacao']
    metric_rows.append({'experiment': experiment_dir.name, 'model': 'tendencia_recente',
        'seed': None, 'selected_step': None,
        **scores(baseline_target, baseline_score, threshold=1.5)})
    prediction_rows.extend({'model': 'tendencia_recente', 'seed': None, 'sample_id': int(i),
        'target': int(y), 'score': float(s), 'prediction': int(s >= 1.5), 'threshold': 1.5,
        'score_kind': 'razao_casos_previstos_media_recente_nao_probabilidade'}
        for i, y, s in zip(baseline_ids, baseline_target, baseline_score))

    metrics = pd.DataFrame(metric_rows)
    history = pd.DataFrame(history_rows)
    predictions = pd.DataFrame(prediction_rows)
    metrics.to_csv(out / 'metricas_validacao_por_semente.csv', index=False)
    history.to_csv(out / 'historico_treinamento.csv', index=False)
    predictions.to_csv(out / 'previsoes_validacao.csv', index=False)
    pd.DataFrame(diagnostics).to_csv(out / 'diagnostico_lstm.csv', index=False)
    summary_rows = []
    for kind, group in metrics.groupby('model', sort=False):
        for metric in METRICS:
            summary_rows.append({'model': kind, 'metric': metric, 'n_runs': len(group),
                'mean': group[metric].mean(), 'std': group[metric].std(ddof=1) if len(group) > 1 else 0.,
                'min': group[metric].min(), 'max': group[metric].max()})
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out / 'resumo_validacao.csv', index=False)
    graphs = []
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    for ax, metric in zip(axes.flat, METRICS):
        subset = summary[summary.metric == metric]
        positions = np.arange(len(subset))
        ax.bar(positions, subset['mean'], yerr=subset['std'], capsize=4,
            color=[MODEL_COLORS[k] for k in subset.model])
        ax.set(xticks=positions, xticklabels=[MODEL_NAMES[k] for k in subset.model],
               title=LABELS[metric], ylabel='Escore (0–1)', ylim=(0, 1.08))
        ax.tick_params(axis='x', rotation=25)
        graphs.append({'id': f'estabilidade/validacao/{metric}', 'titulo': LABELS[metric],
            'tipo': 'barras', 'eixoX': 'Modelo', 'eixoY': 'Escore (0–1)',
            'barrasErro': 'Desvio padrão entre sementes; não intervalo de confiança',
            'series': [{'id': row.model, 'cor': MODEL_COLORS[row.model],
                'pontos': [{'x': MODEL_NAMES[row.model], 'y': row.mean, 'erroY': row.std}]}
                for row in subset.itertuples(index=False, name='Summary')]})
    fig.suptitle(f'{experiment_dir.name} — validação — média ± DP de cinco sementes', fontsize=15)
    save_figure(fig, figures, '01_estabilidade_validacao')

    diag_history = history[(history.model == 'lstm') & (history.seed == 42)]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4))
    stop = diagnostics[0]['stopped_epoch']
    for ax, column, label in zip(axes, ['loss', 'f1', 'predicted_positive'],
                                ['Perda BCE', 'F1 (0–1)', 'Previsões positivas (contagem)']):
        series = []
        for split, color in [('treino', '#2563EB'), ('validacao', '#D97706')]:
            subset = diag_history[diag_history.split == split]
            ax.plot(subset.step, subset[column], color=color, label=split)
            series.append({'id': split, 'cor': color,
                'pontos': [{'x': int(r['step']), 'y': float(r[column])} for r in records(subset)]})
        ax.axvline(stop, color='#64748B', linestyle='--', label=(
            'Parada por F1' if network_selection == 'f1' else 'Parada pela perda'))
        ax.set(title=label, xlabel='Época (contagem)', ylabel=label)
        ax.legend(fontsize=8)
        graphs.append({'id': f'estabilidade/diagnostico_lstm/{column}', 'titulo': label,
            'tipo': 'linha', 'eixoX': 'Época (contagem)', 'eixoY': label,
            'epocaParada': stop, 'criterioParada': network_selection, 'series': series})
    fig.suptitle('LSTM — semente 42 — continuação apenas diagnóstica', fontsize=14)
    save_figure(fig, figures, '02_diagnostico_lstm')

    for graph in graphs:
        graph['id'] = graph['id'].replace('estabilidade/', f'{out_name}/', 1)
    payload = {'schemaVersion': '1.1.0', 'experiment': experiment_dir.name,
        'round': out_name, 'network_selection': network_selection,
        'evaluation_split': 'validacao', 'seeds': SEEDS, 'test_evaluated': False,
        'protocol': {'selection': ('Maior F1 de validação; primeiro em empate' if network_selection == 'f1'
                                 else 'Redes: menor perda BCE de validação; RF: maior F1 de validação'),
            'network_max_epochs': 150, 'patience': 20, 'learning_rate': .003,
            'hidden_size': 24, 'threshold': .5, 'input_sha256': input_hashes,
            'pr_auc_definition': 'sklearn.average_precision_score (AP), não área trapezoidal',
            'baseline': 'máximo(0, último caso + 5 × (média últimas 4 − média 4 anteriores)/4); alerta se ≥ 1,5 × média últimas 4',
            'diagnostic': 'LSTM, seed 42: continuar até 150 épocas; checkpoint principal preservado'},
        'metricas': records(metrics), 'resumo': records(summary), 'diagnosticoLSTM': diagnostics,
        'graficos': graphs,
        'limitations': ['Cinco sementes medem variação de treinamento no mesmo período, não generalização temporal.',
            'Validação também seleciona checkpoints; resultados são de desenvolvimento, não teste independente.',
            'Referência determinística: uma execução por experimento; DP zero não significa certeza.',
            'O teste histórico já examinado continua exploratório.']}
    update_exports(results, payload, out_name)
    report = '# Estabilidade na validação\n\n'
    report += 'Cinco sementes predefinidas: 42, 123, 2025, 7 e 99. Mesmo alvo, entradas e partições.\n'
    report += f'Seleção das redes: {network_selection}. Limiar fixo 0,5. RF permanece selecionado por F1.\n'
    report += 'Treino e validação somente; não se escolheu a melhor semente. PR-AUC = Average Precision.\n\n'
    report += summary.to_csv(index=False) + '\n'
    report += '\n## Diagnóstico da LSTM\n\n' + pd.DataFrame(diagnostics).to_csv(index=False)
    report += '\nA continuação até 150 épocas é diagnóstica; não altera o modelo selecionado pelo critério desta rodada.\n'
    report += 'A repetição de sementes não é validação em novos anos ou episódios climáticos.\n'
    (out / 'relatorio.md').write_text(report, encoding='utf-8')
    # Inclui o relatório no inventário final.
    update_exports(results, payload, out_name)
    return summary


def compare_experiments(project_root, network_selection='f1'):
    root = Path(project_root)
    if network_selection not in ['f1', 'loss']:
        raise ValueError('network_selection deve ser f1 ou loss')
    out_name = 'estabilidade' if network_selection == 'f1' else 'estabilidade_perda'
    directories = [root / 'experimento_sem_ONI/results' / out_name,
                   root / 'experimento_com_ONI/results' / out_name]
    if not all((d / 'metricas_validacao_por_semente.csv').exists() for d in directories):
        return None
    without, with_enso = [pd.read_csv(d / 'metricas_validacao_por_semente.csv') for d in directories]
    paired = without[without.model != 'tendencia_recente'].merge(
        with_enso[with_enso.model != 'tendencia_recente'], on=['model', 'seed'],
        suffixes=('_sem', '_com'), validate='one_to_one')
    assert len(paired) == 15
    rows, pair_rows = [], []
    for kind, group in paired.groupby('model', sort=False):
        for metric in METRICS:
            delta = group[f'{metric}_com'] - group[f'{metric}_sem']
            rows.append({'model': kind, 'metric': metric, 'n_pairs': len(group),
                'mean_without': group[f'{metric}_sem'].mean(), 'mean_with_binary_enso': group[f'{metric}_com'].mean(),
                'mean_delta': delta.mean(), 'std_delta': delta.std(ddof=1),
                'positive_deltas': int((delta > 1e-10).sum()), 'negative_deltas': int((delta < -1e-10).sum())})
            pair_rows.extend({'model': kind, 'seed': int(seed), 'metric': metric, 'delta': float(d)}
                             for seed, d in zip(group.seed, delta))
    comparison = pd.DataFrame(rows)
    out = directories[1]
    comparison.to_csv(out / 'comparacao_com_sem_ONI.csv', index=False)
    pd.DataFrame(pair_rows).to_csv(out / 'diferencas_por_semente.csv', index=False)
    app_path = out / 'app_estabilidade.json'
    payload = json.loads(app_path.read_text())
    payload['comparacaoComSemONI'] = records(comparison)
    payload['diferencasPorSemente'] = pair_rows
    payload['graficos'] = [g for g in payload['graficos'] if not g['id'].startswith(f'{out_name}/comparacao/')]
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    for ax, metric in zip(axes.flat, METRICS):
        subset = comparison[comparison.metric == metric]
        ax.bar(np.arange(len(subset)), subset.mean_delta, yerr=subset.std_delta,
               capsize=4, color=[MODEL_COLORS[k] for k in subset.model])
        ax.axhline(0, color='#475569', linestyle='--')
        ax.set(xticks=np.arange(len(subset)), xticklabels=[MODEL_NAMES[k] for k in subset.model],
               title=LABELS[metric], ylabel='Diferença de escore: com ENSO − sem ENSO')
        payload['graficos'].append({'id': f'{out_name}/comparacao/{metric}',
            'titulo': f'{LABELS[metric]} — com ENSO menos sem ENSO', 'tipo': 'barras',
            'eixoX': 'Modelo', 'eixoY': 'Diferença de escore (adimensional)',
            'barrasErro': 'Desvio padrão das diferenças entre sementes; não intervalo de confiança',
            'series': [{'id': row.model, 'cor': MODEL_COLORS[row.model],
                'pontos': [{'x': MODEL_NAMES[row.model], 'y': row.mean_delta, 'erroY': row.std_delta}]}
                for row in subset.itertuples(index=False)]})
    fig.suptitle('Validação — efeito de acrescentar ENSO binário — cinco sementes', fontsize=14)
    save_figure(fig, out / 'figures', '03_comparacao_com_sem_ONI')
    summary_without, summary_with = [pd.read_csv(d / 'resumo_validacao.csv') for d in directories]
    report = '# Comparação de estabilidade na validação\n\n'
    report += 'Cinco sementes fixas; mesmas entradas de base, alvo de quatro semanas e partições. '
    report += 'Somente os indicadores ENSO são acrescentados no segundo experimento. O teste não foi reavaliado.\n\n'
    report += f'Critério de seleção das redes nesta rodada: {network_selection}. Limiar fixo 0,5.\n\n'
    report += '| Modelo | F1 sem ENSO (média ± DP) | F1 com ENSO (média ± DP) |\n|---|---:|---:|\n'
    for kind in ['random_forest', 'rnn', 'lstm', 'tendencia_recente']:
        a = summary_without[(summary_without.model == kind) & (summary_without.metric == 'f1')].iloc[0]
        b = summary_with[(summary_with.model == kind) & (summary_with.metric == 'f1')].iloc[0]
        report += f'| {MODEL_NAMES[kind]} | {a["mean"]:.3f} ± {a["std"]:.3f} | {b["mean"]:.3f} ± {b["std"]:.3f} |\n'
    report += '\nDP representa variação entre sementes no mesmo período; não é intervalo de confiança. '
    report += 'A tendência recente é determinística e foi executada uma vez por experimento.\n\n'
    for row in comparison[comparison.metric == 'f1'].itertuples():
        report += (f'- {MODEL_NAMES[row.model]}: diferença média de F1 com menos sem ENSO = {row.mean_delta:+.3f}; '
                   f'melhorou em {row.positive_deltas} de {row.n_pairs} sementes.\n')
    report += '\n## Diagnóstico da LSTM, semente 42\n\n'
    for directory, label in zip(directories, ['Sem ENSO', 'Com ENSO']):
        d = pd.read_csv(directory / 'diagnostico_lstm.csv').iloc[0]
        report += (f'- {label}: parada original na época {int(d.stopped_epoch)}, '
                   f'F1 da época de parada {d.stopped_validation_f1:.3f}; '
                   f'maior F1 posterior na continuação diagnóstica {d.best_later_validation_f1:.3f}. '
                   f'Checkpoint original preservado.\n')
    report += ('\nA continuação diagnóstica não substitui o checkpoint escolhido pelo critério desta rodada.\n\n'
               'Os resultados são de desenvolvimento: a validação seleciona checkpoints e a variação '
               'entre sementes não substitui avaliação temporal em novos períodos. A evidência atual '
               'não autoriza concluir causalidade ou relevância geral de ENSO.\n')
    (out / 'comparacao_interpretacao.md').write_text(report, encoding='utf-8')
    update_exports(out.parent, payload, out_name)
    if network_selection == 'loss':
        for directory in directories:
            old = pd.read_csv(directory.parent / 'estabilidade/metricas_validacao_por_semente.csv')
            new = pd.read_csv(directory / 'metricas_validacao_por_semente.csv')
            rows = []
            for kind in ['random_forest', 'rnn', 'lstm', 'tendencia_recente']:
                for metric in METRICS:
                    a = old.loc[old.model == kind, metric]
                    b = new.loc[new.model == kind, metric]
                    rows.append({'model': kind, 'metric': metric, 'n_runs': len(b),
                        'mean_original_f1_selection': a.mean(), 'mean_loss_selection': b.mean(),
                        'std_original': a.std(ddof=1) if len(a) > 1 else 0.,
                        'std_new': b.std(ddof=1) if len(b) > 1 else 0.,
                        'mean_delta': b.mean() - a.mean()})
            before_after = pd.DataFrame(rows)
            before_after.to_csv(directory / 'comparacao_criterio_treinamento.csv', index=False)
            current = json.loads((directory / 'app_estabilidade.json').read_text())
            current['comparacaoCriterioTreinamento'] = records(before_after)
            update_exports(directory.parent, current, out_name)
    return comparison


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network-selection', choices=['f1', 'loss'], default='loss')
    args = parser.parse_args()
    project = Path(__file__).resolve().parent.parent
    for experiment in ['experimento_sem_ONI', 'experimento_com_ONI']:
        run_experiment(project / experiment, network_selection=args.network_selection)
    compare_experiments(project, network_selection=args.network_selection)
