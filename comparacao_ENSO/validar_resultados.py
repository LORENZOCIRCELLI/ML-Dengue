from pathlib import Path
import hashlib
import importlib.util
import json

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.preprocessing import StandardScaler


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate(root):
    root = Path(root)
    directory = root / 'comparacao_ENSO'
    output = directory / 'results'
    spec = importlib.util.spec_from_file_location('enso_comparison', directory / 'estudo.py')
    study = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(study)
    torch.set_num_threads(1)
    protocol = read_json(output / 'protocolo.json')
    config = protocol['base_protocol']
    assert config['seeds'] == [42, 123, 2025, 7, 99]
    assert config['horizons_weeks'] == [4, 8, 12, 16]
    assert not protocol['variants_selected_by_test']
    path = root / 'data/dataset/processado/base_modelagem_dengue_dataset.xlsx'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == protocol['source_audit']['source_sha256']
    df = pd.read_excel(path).sort_values('dt_pri_sem').reset_index(drop=True)
    base = pd.DataFrame({
        'casos_dengue': df['n dengue'],
        'temperatura_media': df.media_temperatura_semana,
        'umidade_media': df.media_umidade_semana,
        'chuva_total': df.chuva_total_mm,
        'semana_sin': np.sin(2 * np.pi * df.semana_epidemiologica / 52),
        'semana_cos': np.cos(2 * np.pi * df.semana_epidemiologica / 52),
    })
    checks = []
    for horizon in config['horizons_weeks']:
        reference = pd.read_csv(root / f'v1/results/horizontes/{horizon:02d}_semanas/data/particoes.csv')
        baseline_arrays = {}
        for variant, width in [('sem_ENSO', 6), ('ONI_continuo', 7), ('ENSO_binario', 8)]:
            current = output / f'horizontes/{horizon:02d}_semanas/{variant}'
            samples = pd.read_csv(current / 'data/particoes.csv')
            pd.testing.assert_frame_equal(samples, reference)
            raw_features = base.copy()
            if variant == 'ONI_continuo':
                raw_features['ONI'] = df.ONI
            elif variant == 'ENSO_binario':
                raw_features['el_nino'] = (df.ONI >= 0.5).astype(float)
                raw_features['la_nina'] = (df.ONI <= -0.5).astype(float)
            available = pd.DataFrame({
                name: raw_features[name].shift(4 if name not in base else 1)
                for name in raw_features
            })
            raw = np.stack([
                available.iloc[index - 11:index + 1].to_numpy()
                for index in samples.sample_id
            ])
            mask = samples.split.eq('treino').to_numpy()
            expected_scaler = StandardScaler().fit(raw[mask].reshape(-1, width))
            scaler = joblib.load(current / 'scaler.joblib')
            np.testing.assert_allclose(expected_scaler.mean_, scaler.mean_)
            np.testing.assert_allclose(expected_scaler.scale_, scaler.scale_)
            transformed = scaler.transform(raw.reshape(-1, width)).reshape(-1, 12 * width).astype(np.float32)
            arrays, labels = {}, {}
            for split in ['treino', 'validacao', 'teste']:
                table = pd.read_csv(current / f'data/{split}_padronizado.csv')
                arrays[split] = table.drop(columns=['sample_id', 'target']).to_numpy(dtype=np.float32)
                labels[split] = table.target.to_numpy()
                np.testing.assert_allclose(arrays[split], transformed[samples.split.eq(split)], atol=1e-7, rtol=1e-6)
                if variant == 'sem_ENSO':
                    baseline_arrays[split] = arrays[split]
                else:
                    np.testing.assert_allclose(
                        arrays[split].reshape(-1, 12, width)[:, :, :6].reshape(-1, 72),
                        baseline_arrays[split], atol=1e-7, rtol=1e-6,
                    )
            for kind in ['random_forest', 'rnn', 'lstm']:
                model_directory = current / kind
                model_config = read_json(model_directory / 'configuracao.json')
                assert model_config['input_size'] == width
                assert model_config['base_protocol'] == config
                models = []
                for seed in config['seeds']:
                    if kind == 'random_forest':
                        model = joblib.load(model_directory / f'artifacts/seed_{seed}.joblib')
                        assert model.max_depth == 6 and model.min_samples_leaf == 2
                        assert model.max_features == 'sqrt'
                    else:
                        checkpoint = torch.load(model_directory / f'artifacts/seed_{seed}.pt', map_location='cpu', weights_only=False)
                        assert checkpoint['input_size'] == width
                        model = study.SequenceClassifier(kind, width)
                        model.load_state_dict(checkpoint['state_dict'])
                        model.eval()
                        assert model.recurrent.hidden_size == 24
                    models.append(model)
                metrics = pd.read_csv(model_directory / 'metrics/metricas_ensemble.csv')
                selection = pd.read_csv(model_directory / 'metrics/selecao_por_semente.csv')
                history = pd.read_csv(model_directory / 'metrics/historico_treinamento.csv')
                for seed in config['seeds']:
                    validation = history.query('seed == @seed and split == "validacao"').sort_values('step')
                    row = selection.query('seed == @seed').iloc[0]
                    if kind == 'random_forest':
                        assert row.selected_step == validation.loc[validation.f1.idxmax(), 'step']
                    else:
                        best, best_step = np.inf, None
                        for record in validation.itertuples():
                            if record.loss < best - 1e-8:
                                best, best_step = record.loss, record.step
                        assert row.selected_step == best_step
                for split in arrays:
                    y = labels[split]
                    predictions = pd.read_csv(model_directory / f'data/previsoes_{split}.csv')
                    individual = []
                    for model in models:
                        if kind == 'random_forest':
                            probability = model.predict_proba(arrays[split])[:, 1]
                        else:
                            with torch.no_grad():
                                probability = torch.sigmoid(model(torch.tensor(arrays[split]))).numpy()
                        individual.append(probability)
                    individual = np.array(individual)
                    expected = predictions[[f'escore_seed_{seed}' for seed in config['seeds']]].to_numpy().T
                    np.testing.assert_allclose(individual, expected, atol=2e-7, rtol=1e-6)
                    probability = individual.mean(axis=0)
                    np.testing.assert_allclose(probability, predictions.escore_aumento, atol=2e-7, rtol=1e-6)
                    predicted = probability >= 0.5
                    np.testing.assert_array_equal(predicted.astype(int), predictions.prediction)
                    actual = {
                        'f1': f1_score(y, predicted, zero_division=0),
                        'precision': precision_score(y, predicted, zero_division=0),
                        'recall': recall_score(y, predicted, zero_division=0),
                        'accuracy': accuracy_score(y, predicted),
                        'roc_auc': roc_auc_score(y, probability),
                        'pr_auc': average_precision_score(y, probability),
                    }
                    saved = metrics.query('split == @split').iloc[0]
                    for metric, value in actual.items():
                        assert abs(saved[metric] - value) < 1e-6, (horizon, variant, kind, split, metric)
                    matrix = read_json(model_directory / 'metrics/matrizes_confusao.json')[split]['valores']
                    np.testing.assert_array_equal(confusion_matrix(y, predicted, labels=[0, 1]), matrix)
                checks.append({'horizon': horizon, 'variant': variant, 'model': kind, 'status': 'ok'})
                print(f'OK {horizon} / {variant} / {kind}', flush=True)
    deltas = pd.read_csv(output / 'comparacao/diferencas_ensemble.csv')
    assert len(deltas) == 4 * 3 * 2 * 3 * 6
    np.testing.assert_allclose(deltas.delta, deltas.candidate - deltas.baseline, atol=1e-14)
    intervals = pd.read_csv(output / 'comparacao/intervalos_pareados_teste.csv')
    assert len(intervals) == 4 * 3 * 2 * 2
    assert (intervals.ci95_low <= intervals.ci95_high).all()
    assert (intervals.valid_resamples > 0).all()
    assert (intervals.block_weeks == intervals.horizon_weeks.clip(lower=12)).all()
    for row in pd.read_csv(output / 'manifesto.csv').itertuples():
        assert (output / row.path).stat().st_size == row.bytes
    (directory / 'verificacao.json').write_text(json.dumps({
        'models_checked': len(checks),
        'checks': checks,
        'data_splits_scalers_predictions_metrics_selection_verified': True,
    }, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('36 combinações verificadas sem retreinamento.', flush=True)


if __name__ == '__main__':
    validate(Path(__file__).resolve().parents[1])
