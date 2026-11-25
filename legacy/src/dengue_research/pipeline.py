"""Pipeline temporal para previsão de surtos de dengue.

Princípios implementados:
1. cada amostra representa uma previsão emitida na semana t;
2. o alvo ocorre em t+h (ou dentro de t+1..t+h na análise complementar);
3. todas as transformações aprendidas são ajustadas apenas no treino;
4. validação escolhe hiperparâmetros e limiar; teste é usado uma única vez;
5. o canal endêmico usa apenas anos anteriores à semana rotulada.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal
import json
import math
import random
import joblib

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    fbeta_score,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_curve,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import ParameterGrid
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


TargetKind = Literal["exact", "window"]


@dataclass(frozen=True)
class StudyConfig:
    data_path: Path = Path("data/dataset/processado/base_modelagem_dengue_dataset.xlsx")
    output_dir: Path = Path("outputs/revisao_metodologica")
    horizons: tuple[int, ...] = (4, 8, 12, 16)
    target_kinds: tuple[TargetKind, ...] = ("exact", "window")
    case_column: str = "n dengue"
    date_column: str = "dt_pri_sem"
    train_end: str = "2021-12-26"
    validation_start: str = "2022-01-02"
    validation_end: str = "2023-12-31"
    test_start: str = "2024-01-07"
    test_end: str = "2025-12-28"
    endemic_quantile: float = 0.75
    endemic_week_radius: int = 2
    endemic_lookback_years: int = 5
    endemic_min_years: int = 3
    persistence_weeks: int = 3
    persistence_factor: float = 1.10
    sequence_length: int = 12
    target_recall: float = 0.80
    seed: int = 42
    numpy_hidden_size: int = 16
    numpy_epochs: int = 120
    pytorch_hidden_size: int = 32
    pytorch_epochs: int = 150
    early_stopping_patience: int = 20

    def to_json(self) -> dict:
        result = asdict(self)
        result["data_path"] = str(self.data_path)
        result["output_dir"] = str(self.output_dir)
        return result


def set_reproducible_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def load_weekly_data(config: StudyConfig) -> pd.DataFrame:
    df = pd.read_excel(config.data_path)
    if config.date_column not in df or config.case_column not in df:
        raise ValueError("Dataset sem as colunas obrigatórias de data ou casos.")
    df[config.date_column] = pd.to_datetime(df[config.date_column])
    df = df.sort_values(config.date_column).set_index(config.date_column)
    if df.index.has_duplicates:
        raise ValueError("Existem semanas duplicadas no dataset.")
    expected = pd.date_range(df.index.min(), df.index.max(), freq="W-SUN")
    missing = expected.difference(df.index)
    if len(missing):
        raise ValueError(f"A série possui {len(missing)} semanas ausentes.")
    if not df.index.is_monotonic_increasing:
        raise ValueError("O índice temporal não está ordenado.")
    return df


def audit_data(df: pd.DataFrame, config: StudyConfig) -> dict:
    numeric = df.select_dtypes(include=np.number)
    spatial = [c for c in df.columns if c.startswith("N dengue N")]
    spatial_sum = df[spatial].sum(axis=1) if spatial else pd.Series(index=df.index, dtype=float)
    return {
        "n_rows": int(len(df)),
        "n_columns": int(df.shape[1] + 1),  # inclui a data, movida para o índice
        "start": str(df.index.min().date()),
        "end": str(df.index.max().date()),
        "frequency": pd.infer_freq(df.index),
        "duplicated_dates": int(df.index.duplicated().sum()),
        "missing_values": int(df.isna().sum().sum()),
        "infinite_numeric_values": int(np.isinf(numeric.to_numpy()).sum()),
        "case_min": float(df[config.case_column].min()),
        "case_median": float(df[config.case_column].median()),
        "case_mean": float(df[config.case_column].mean()),
        "case_max": float(df[config.case_column].max()),
        "spatial_columns": spatial,
        "spatial_sum_equals_target_fraction": (
            float(np.mean(np.isclose(spatial_sum, df[config.case_column]))) if spatial else None
        ),
        "excluded_pending_provenance": spatial + ["Trend SP"],
    }


def _circular_week_distance(a: np.ndarray, b: int) -> np.ndarray:
    distance = np.abs(a - b)
    return np.minimum(distance, 53 - distance)


def causal_endemic_channel(df: pd.DataFrame, config: StudyConfig) -> pd.DataFrame:
    """Cria limiar e rótulo semanal usando somente observações de anos anteriores."""
    cases = df[config.case_column].astype(float)
    years = (
        df["ano"].to_numpy(dtype=int)
        if "ano" in df
        else (df.index + pd.Timedelta(days=1)).isocalendar().year.to_numpy(dtype=int)
    )
    weeks = (
        df["semana_epidemiologica"].to_numpy(dtype=int)
        if "semana_epidemiologica" in df
        else (df.index + pd.Timedelta(days=1)).isocalendar().week.to_numpy(dtype=int)
    )
    values = cases.to_numpy()
    thresholds = np.full(len(df), np.nan, dtype=float)
    history_n = np.zeros(len(df), dtype=int)
    history_years = np.zeros(len(df), dtype=int)

    for pos, (year, week) in enumerate(zip(years, weeks)):
        past_year = (years < year) & (years >= year - config.endemic_lookback_years)
        similar_week = _circular_week_distance(weeks, int(week)) <= config.endemic_week_radius
        mask = past_year & similar_week
        n_years = len(np.unique(years[mask]))
        history_years[pos] = n_years
        history_n[pos] = int(mask.sum())
        if n_years >= config.endemic_min_years:
            thresholds[pos] = float(np.quantile(values[mask], config.endemic_quantile))

    rolling_cases = cases.rolling(config.persistence_weeks, min_periods=config.persistence_weeks).mean()
    above = cases > thresholds
    persistent = above & (rolling_cases > thresholds * config.persistence_factor)
    persistent = persistent.astype("Float64").where(~pd.isna(thresholds), pd.NA)

    return pd.DataFrame(
        {
            "endemic_threshold": thresholds,
            "endemic_history_n": history_n,
            "endemic_history_years": history_years,
            "rolling_cases_for_outbreak": rolling_cases,
            "outbreak": persistent,
        },
        index=df.index,
    )


def create_targets(
    outbreak: pd.Series,
    horizons: Iterable[int],
) -> pd.DataFrame:
    targets = pd.DataFrame(index=outbreak.index)
    for horizon in horizons:
        targets[f"target_exact_{horizon}"] = outbreak.shift(-horizon)
        future = pd.concat([outbreak.shift(-step) for step in range(1, horizon + 1)], axis=1)
        targets[f"target_window_{horizon}"] = future.max(axis=1, skipna=False)
    return targets


def engineer_features(df: pd.DataFrame, config: StudyConfig) -> pd.DataFrame:
    """Features disponíveis até t; casos entram com atraso mínimo de uma semana."""
    feature_series: dict[str, pd.Series | np.ndarray] = {}
    cases = df[config.case_column].astype(float)
    observed_cases = cases.shift(1)

    feature_series["population"] = df["dem"].astype(float)
    week = (
        df["semana_epidemiologica"].astype(float)
        if "semana_epidemiologica" in df
        else pd.Series(
            (df.index + pd.Timedelta(days=1)).isocalendar().week.to_numpy(dtype=float),
            index=df.index,
        )
    )
    feature_series["week_sin"] = np.sin(2 * np.pi * week / 52.1775)
    feature_series["week_cos"] = np.cos(2 * np.pi * week / 52.1775)

    for lag in (1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 26, 52):
        feature_series[f"cases_lag_{lag}"] = cases.shift(lag)
        feature_series[f"log_cases_lag_{lag}"] = np.log1p(cases.shift(lag))

    for window in (4, 8, 12, 26, 52):
        rolling = observed_cases.rolling(window, min_periods=window)
        feature_series[f"cases_mean_{window}"] = rolling.mean()
        feature_series[f"cases_std_{window}"] = rolling.std()
        feature_series[f"cases_max_{window}"] = rolling.max()
        feature_series[f"cases_min_{window}"] = rolling.min()

    feature_series["cases_diff_1"] = observed_cases.diff(1)
    feature_series["cases_diff_4"] = observed_cases.diff(4)
    feature_series["cases_pct_1"] = observed_cases.pct_change(1)
    feature_series["cases_pct_4"] = observed_cases.pct_change(4)

    climate = [
        "media_temperatura_semana",
        "amplitude_termica_semana",
        "media_ponto_orvalho_semana",
        "media_umidade_semana",
        "chuva_total_mm",
        "numero_dias_com_chuva_semana",
        "dias_com_tempestade",
    ]
    for column in climate:
        if column not in df:
            continue
        series = df[column].astype(float)
        feature_series[column] = series
        for lag in (1, 2, 4, 8, 12):
            feature_series[f"{column}_lag_{lag}"] = series.shift(lag)
        for window in (4, 8, 12):
            feature_series[f"{column}_mean_{window}"] = series.rolling(window, min_periods=window).mean()

    for column in ("ONI", "AMM_SST", "AMM_WIND", "AAO_SAM"):
        if column not in df:
            continue
        series = df[column].astype(float)
        feature_series[column] = series
        for lag in (4, 8, 12):
            feature_series[f"{column}_lag_{lag}"] = series.shift(lag)

    # Google Trends e sub-regiões ficam fora até que sua disponibilidade e origem
    # sejam documentadas. As colunas derivadas existentes são recalculadas acima.
    features = pd.DataFrame(feature_series, index=df.index)
    return features.replace([np.inf, -np.inf], np.nan)


def assemble_samples(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    outbreak: pd.Series,
    horizon: int,
    target_kind: TargetKind,
) -> pd.DataFrame:
    target_name = f"target_{target_kind}_{horizon}"
    sample = features.copy()
    sample["target"] = targets[target_name]
    # Baseline de persistência respeita o atraso epidemiológico de uma semana.
    sample["current_outbreak"] = outbreak.shift(1)
    sample["issue_date"] = sample.index
    sample["target_date"] = sample.index + pd.to_timedelta(7 * horizon, unit="D")
    sample = sample.dropna(subset=list(features.columns) + ["target"])
    sample["target"] = sample["target"].astype(int)
    return sample


def temporal_split(sample: pd.DataFrame, config: StudyConfig) -> dict[str, pd.DataFrame]:
    target_date = pd.to_datetime(sample["target_date"])
    train = sample.loc[target_date <= pd.Timestamp(config.train_end)].copy()
    validation = sample.loc[
        (target_date >= pd.Timestamp(config.validation_start))
        & (target_date <= pd.Timestamp(config.validation_end))
    ].copy()
    test = sample.loc[
        (target_date >= pd.Timestamp(config.test_start))
        & (target_date <= pd.Timestamp(config.test_end))
    ].copy()
    for name, part in {"train": train, "validation": validation, "test": test}.items():
        if part.empty:
            raise ValueError(f"Partição temporal vazia: {name}")
        if part["target"].nunique() < 2:
            raise ValueError(f"Partição {name} contém apenas uma classe.")
    return {"train": train, "validation": validation, "test": test}


def choose_operating_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    target_recall: float,
) -> tuple[float, dict]:
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    candidates = []
    for idx, threshold in enumerate(thresholds):
        candidates.append((float(threshold), float(precision[idx]), float(recall[idx])))
    feasible = [row for row in candidates if row[2] >= target_recall]
    if feasible:
        threshold, p, r = max(feasible, key=lambda row: (row[1], row[0]))
        method = f"maior precisão com recall >= {target_recall:.2f}"
    else:
        scored = []
        for threshold, p, r in candidates:
            f2 = 0.0 if p + r == 0 else 5 * p * r / (4 * p + r)
            scored.append((f2, threshold, p, r))
        _, threshold, p, r = max(scored, key=lambda row: row[0])
        method = "máximo F2 (meta de recall não atingida)"
    return threshold, {"method": method, "validation_precision": p, "validation_recall": r}


def classification_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict:
    prediction = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, prediction, labels=[0, 1]).ravel()
    result = {
        "n": int(len(y_true)),
        "prevalence": float(np.mean(y_true)),
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, prediction)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall_sensitivity": float(recall_score(y_true, prediction, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else math.nan,
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "f2": float(fbeta_score(y_true, prediction, beta=2, zero_division=0)),
        "pr_auc": float(average_precision_score(y_true, probabilities)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "brier": float(brier_score_loss(y_true, probabilities)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "false_alarms_per_year": float(fp / (len(y_true) / 52.1775)),
    }
    return result


def block_bootstrap_ci(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    seed: int,
    block_length: int = 8,
    n_bootstrap: int = 500,
) -> dict:
    """IC percentil com reamostragem em blocos para preservar dependência local."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    measures = {key: [] for key in ("pr_auc", "roc_auc", "recall_sensitivity", "precision", "f2")}
    for _ in range(n_bootstrap):
        positions: list[int] = []
        while len(positions) < n:
            start = int(rng.integers(0, max(n - block_length + 1, 1)))
            positions.extend(range(start, min(start + block_length, n)))
        idx = np.asarray(positions[:n], dtype=int)
        y_b = y_true[idx]
        if len(np.unique(y_b)) < 2:
            continue
        p_b = probabilities[idx]
        metrics = classification_metrics(y_b, p_b, threshold)
        for key in measures:
            measures[key].append(metrics[key])
    return {
        key: {
            "lower_95": float(np.quantile(values, 0.025)),
            "upper_95": float(np.quantile(values, 0.975)),
        }
        for key, values in measures.items()
        if values
    }


def _feature_columns(sample: pd.DataFrame) -> list[str]:
    metadata = {"target", "current_outbreak", "issue_date", "target_date"}
    return [column for column in sample.columns if column not in metadata]


def seasonal_baseline(
    train: pd.DataFrame,
    frame: pd.DataFrame,
) -> np.ndarray:
    train_target_week = (
        pd.to_datetime(train["target_date"]) + pd.Timedelta(days=1)
    ).dt.isocalendar().week.astype(int)
    rates = train.assign(target_week=train_target_week).groupby("target_week")["target"].mean()
    global_rate = float(train["target"].mean())
    frame_week = (
        pd.to_datetime(frame["target_date"]) + pd.Timedelta(days=1)
    ).dt.isocalendar().week.astype(int)
    return frame_week.map(rates).fillna(global_rate).to_numpy(dtype=float)


def expanding_year_folds(train: pd.DataFrame, min_train_years: int = 3) -> list[tuple[np.ndarray, np.ndarray]]:
    years = pd.to_datetime(train["target_date"]).dt.year.to_numpy()
    unique = np.unique(years)
    folds = []
    for validation_year in unique[min_train_years:]:
        train_idx = np.flatnonzero(years < validation_year)
        validation_idx = np.flatnonzero(years == validation_year)
        if len(train_idx) and len(validation_idx):
            y_train = train.iloc[train_idx]["target"]
            y_validation = train.iloc[validation_idx]["target"]
            if y_train.nunique() == 2 and y_validation.nunique() == 2:
                folds.append((train_idx, validation_idx))
    return folds


def select_random_forest(
    train: pd.DataFrame,
    feature_columns: list[str],
    seed: int,
) -> tuple[RandomForestClassifier, dict, pd.DataFrame]:
    grid = ParameterGrid(
        {
            "n_estimators": [300],
            "max_depth": [4, 8, None],
            "min_samples_leaf": [3, 8],
            "max_features": ["sqrt"],
        }
    )
    folds = expanding_year_folds(train)
    if not folds:
        raise ValueError("Não foi possível criar folds temporais com as duas classes.")
    records = []
    X = train[feature_columns]
    y = train["target"].to_numpy()
    for params in grid:
        scores = []
        for fit_idx, val_idx in folds:
            model = RandomForestClassifier(
                class_weight="balanced_subsample",
                random_state=seed,
                n_jobs=-1,
                **params,
            )
            model.fit(X.iloc[fit_idx], y[fit_idx])
            probability = model.predict_proba(X.iloc[val_idx])[:, 1]
            scores.append(average_precision_score(y[val_idx], probability))
        records.append({**params, "mean_walk_forward_pr_auc": float(np.mean(scores)), "n_folds": len(scores)})
    result = pd.DataFrame(records).sort_values("mean_walk_forward_pr_auc", ascending=False)
    best = result.iloc[0].to_dict()
    best_params = {
        key: best[key]
        for key in ("n_estimators", "max_depth", "min_samples_leaf", "max_features")
    }
    best_params["n_estimators"] = int(best_params["n_estimators"])
    best_params["min_samples_leaf"] = int(best_params["min_samples_leaf"])
    if not pd.isna(best_params["max_depth"]):
        best_params["max_depth"] = int(best_params["max_depth"])
    else:
        best_params["max_depth"] = None
    model = RandomForestClassifier(
        class_weight="balanced_subsample",
        random_state=seed,
        n_jobs=-1,
        **best_params,
    )
    model.fit(X, y)
    return model, best_params, result


def select_logistic_regression(
    train: pd.DataFrame,
    feature_columns: list[str],
    seed: int,
) -> tuple[Pipeline, dict, pd.DataFrame]:
    """Seleciona a regularização somente dentro do treino com folds anuais."""
    folds = expanding_year_folds(train)
    if not folds:
        raise ValueError("Não foi possível criar folds temporais com as duas classes.")
    X = train[feature_columns]
    y = train["target"].to_numpy()
    records = []
    for c_value in (0.01, 0.1, 1.0, 10.0):
        scores = []
        for fit_idx, val_idx in folds:
            model = Pipeline(
                [
                    ("scaler", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            C=c_value,
                            class_weight="balanced",
                            max_iter=5000,
                            random_state=seed,
                        ),
                    ),
                ]
            )
            model.fit(X.iloc[fit_idx], y[fit_idx])
            probability = model.predict_proba(X.iloc[val_idx])[:, 1]
            scores.append(average_precision_score(y[val_idx], probability))
        records.append(
            {
                "C": float(c_value),
                "mean_walk_forward_pr_auc": float(np.mean(scores)),
                "n_folds": len(scores),
            }
        )
    search = pd.DataFrame(records).sort_values("mean_walk_forward_pr_auc", ascending=False)
    best_c = float(search.iloc[0]["C"])
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=best_c,
                    class_weight="balanced",
                    max_iter=5000,
                    random_state=seed,
                ),
            ),
        ]
    )
    model.fit(X, y)
    return model, {"C": best_c, "penalty": "l2"}, search


def fit_tabular_models(
    splits: dict[str, pd.DataFrame],
    config: StudyConfig,
) -> tuple[dict, dict, dict]:
    train, validation, test = splits["train"], splits["validation"], splits["test"]
    columns = _feature_columns(train)
    y_train = train["target"].to_numpy()
    y_validation = validation["target"].to_numpy()
    y_test = test["target"].to_numpy()
    models: dict[str, object] = {}
    predictions: dict[str, dict[str, np.ndarray]] = {}
    selection: dict[str, dict] = {}

    logistic, logistic_params, logistic_search = select_logistic_regression(
        train, columns, config.seed
    )
    models["logistic_regression"] = logistic
    selection["logistic_regression"] = {
        "best_params": logistic_params,
        "walk_forward_search": logistic_search.to_dict(orient="records"),
    }

    rf, rf_params, rf_search = select_random_forest(train, columns, config.seed)
    models["random_forest"] = rf
    selection["random_forest"] = {
        "best_params": rf_params,
        "walk_forward_search": rf_search.to_dict(orient="records"),
    }

    for name, model in models.items():
        predictions[name] = {
            "validation": model.predict_proba(validation[columns])[:, 1],
            "test": model.predict_proba(test[columns])[:, 1],
        }

    predictions["seasonal_baseline"] = {
        "validation": seasonal_baseline(train, validation),
        "test": seasonal_baseline(train, test),
    }
    predictions["persistence_baseline"] = {
        "validation": validation["current_outbreak"].astype(float).fillna(y_train.mean()).to_numpy(),
        "test": test["current_outbreak"].astype(float).fillna(y_train.mean()).to_numpy(),
    }

    for name, probability in predictions.items():
        threshold, details = choose_operating_threshold(
            y_validation,
            probability["validation"],
            config.target_recall,
        )
        selection[name] = {**selection.get(name, {}), "threshold": threshold, **details}
        probability["y_validation"] = y_validation
        probability["y_test"] = y_test
    return models, predictions, selection


def fixed_lstm_features(all_columns: Iterable[str]) -> list[str]:
    case_preferred = [
        "log_cases_lag_1",
        "log_cases_lag_2",
        "log_cases_lag_4",
        "log_cases_lag_8",
        "log_cases_lag_12",
        "log_cases_lag_52",
        "cases_mean_4",
        "cases_mean_12",
        "cases_std_12",
        "media_temperatura_semana",
        "media_umidade_semana",
        "chuva_total_mm",
        "ONI",
        "week_sin",
        "week_cos",
    ]
    available = set(all_columns)
    incidence_preferred = [
        "log_incidence_lag_1",
        "log_incidence_lag_2",
        "log_incidence_lag_4",
        "log_incidence_lag_8",
        "log_incidence_lag_12",
        "log_incidence_lag_52",
        "incidence_mean_4",
        "incidence_mean_12",
        "incidence_std_12",
        "incidence_ratio_upper_lag1",
        "media_temperatura_semana",
        "media_umidade_semana",
        "chuva_total_mm",
        "ONI",
        "week_sin",
        "week_cos",
    ]
    preferred = incidence_preferred if "log_incidence_lag_1" in available else case_preferred
    missing = [column for column in preferred if column not in available]
    if missing:
        raise ValueError(f"Features fixas da LSTM ausentes: {missing}")
    return preferred


def prepare_sequences(
    features: pd.DataFrame,
    sample: pd.DataFrame,
    splits: dict[str, pd.DataFrame],
    columns: list[str],
    sequence_length: int,
) -> tuple[StandardScaler, dict[str, tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]]]:
    max_train_issue = splits["train"].index.max()
    scaler_fit_frame = features.loc[features.index <= max_train_issue, columns].dropna()
    scaler = StandardScaler().fit(scaler_fit_frame)
    valid_features = features[columns].dropna()
    transformed = pd.DataFrame(
        scaler.transform(valid_features),
        index=valid_features.index,
        columns=columns,
    )
    position = {date: idx for idx, date in enumerate(transformed.index)}
    arrays: dict[str, tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]] = {}
    for split_name, split in splits.items():
        X, y, dates = [], [], []
        for date, row in split.iterrows():
            idx = position.get(date)
            if idx is None or idx < sequence_length - 1:
                continue
            sequence_index = transformed.index[idx - sequence_length + 1 : idx + 1]
            if len(sequence_index) != sequence_length:
                continue
            expected = pd.date_range(sequence_index[0], sequence_index[-1], freq="W-SUN")
            if not sequence_index.equals(expected):
                continue
            X.append(transformed.iloc[idx - sequence_length + 1 : idx + 1].to_numpy(dtype=np.float32))
            y.append(int(row["target"]))
            dates.append(date)
        arrays[split_name] = (
            np.asarray(X, dtype=np.float32),
            np.asarray(y, dtype=np.float32),
            pd.DatetimeIndex(dates),
        )
    return scaler, arrays


class NumpyLSTM:
    """LSTM NumPy com BPTT completo e Adam, mantida para comparação didática."""

    def __init__(self, input_size: int, hidden_size: int, seed: int = 42):
        self.input_size = input_size
        self.hidden_size = hidden_size
        rng = np.random.default_rng(seed)
        scale = np.sqrt(1.0 / (input_size + hidden_size))
        self.params = {
            "W": rng.normal(0, scale, size=(4 * hidden_size, input_size + hidden_size)),
            "b": np.zeros((4 * hidden_size, 1)),
            "Wy": rng.normal(0, np.sqrt(1.0 / hidden_size), size=(1, hidden_size)),
            "by": np.zeros((1, 1)),
        }
        # Inicialização positiva da porta de esquecimento.
        self.params["b"][:hidden_size] = 1.0
        self.m = {name: np.zeros_like(value) for name, value in self.params.items()}
        self.v = {name: np.zeros_like(value) for name, value in self.params.items()}
        self.step = 0

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -40, 40)))

    def forward(self, sequence: np.ndarray, cache: bool = False):
        h = np.zeros((self.hidden_size, 1))
        c = np.zeros((self.hidden_size, 1))
        caches = []
        for x_t in sequence:
            x = x_t.reshape(-1, 1)
            h_previous, c_previous = h, c
            joined = np.vstack([h_previous, x])
            gates = self.params["W"] @ joined + self.params["b"]
            f = self._sigmoid(gates[: self.hidden_size])
            i = self._sigmoid(gates[self.hidden_size : 2 * self.hidden_size])
            g = np.tanh(gates[2 * self.hidden_size : 3 * self.hidden_size])
            o = self._sigmoid(gates[3 * self.hidden_size :])
            c = f * c_previous + i * g
            h = o * np.tanh(c)
            if cache:
                caches.append((joined, h_previous, c_previous, f, i, g, o, c, h))
        logit = self.params["Wy"] @ h + self.params["by"]
        probability = self._sigmoid(logit)
        return (float(probability.item()), caches) if cache else float(probability.item())

    def backward(self, sequence: np.ndarray, target: float, positive_weight: float) -> tuple[dict, float]:
        probability, caches = self.forward(sequence, cache=True)
        weight = positive_weight if target == 1.0 else 1.0
        loss = -weight * (
            target * np.log(probability + 1e-9)
            + (1 - target) * np.log(1 - probability + 1e-9)
        )
        gradients = {name: np.zeros_like(value) for name, value in self.params.items()}
        final_h = caches[-1][-1]
        dlogit = weight * (probability - target)
        gradients["Wy"] += dlogit * final_h.T
        gradients["by"] += dlogit
        dh_next = self.params["Wy"].T * dlogit
        dc_next = np.zeros_like(dh_next)

        for joined, _, c_previous, f, i, g, o, c, _ in reversed(caches):
            tanh_c = np.tanh(c)
            do = dh_next * tanh_c
            dc = dc_next + dh_next * o * (1 - tanh_c**2)
            df = dc * c_previous
            di = dc * g
            dg = dc * i
            dc_next = dc * f
            da_f = df * f * (1 - f)
            da_i = di * i * (1 - i)
            da_g = dg * (1 - g**2)
            da_o = do * o * (1 - o)
            da = np.vstack([da_f, da_i, da_g, da_o])
            gradients["W"] += da @ joined.T
            gradients["b"] += da
            d_joined = self.params["W"].T @ da
            dh_next = d_joined[: self.hidden_size]

        return gradients, float(loss)

    def _adam_update(self, gradients: dict, learning_rate: float, clip_norm: float = 5.0) -> None:
        norm = math.sqrt(sum(float(np.sum(gradient**2)) for gradient in gradients.values()))
        if norm > clip_norm:
            gradients = {name: gradient * clip_norm / (norm + 1e-12) for name, gradient in gradients.items()}
        self.step += 1
        for name in self.params:
            gradient = gradients[name]
            self.m[name] = 0.9 * self.m[name] + 0.1 * gradient
            self.v[name] = 0.999 * self.v[name] + 0.001 * (gradient**2)
            m_hat = self.m[name] / (1 - 0.9**self.step)
            v_hat = self.v[name] / (1 - 0.999**self.step)
            self.params[name] -= learning_rate * m_hat / (np.sqrt(v_hat) + 1e-8)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_validation: np.ndarray,
        y_validation: np.ndarray,
        epochs: int,
        patience: int,
        seed: int,
        batch_size: int = 32,
        learning_rate: float = 0.003,
    ) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        positive_weight = float((len(y_train) - y_train.sum()) / max(y_train.sum(), 1))
        best_loss = np.inf
        best_params = None
        waiting = 0
        history = []
        for epoch in range(epochs):
            order = rng.permutation(len(X_train))
            losses = []
            for start in range(0, len(order), batch_size):
                batch = order[start : start + batch_size]
                accumulated = {name: np.zeros_like(value) for name, value in self.params.items()}
                for idx in batch:
                    gradients, loss = self.backward(X_train[idx], float(y_train[idx]), positive_weight)
                    losses.append(loss)
                    for name in accumulated:
                        accumulated[name] += gradients[name]
                for name in accumulated:
                    accumulated[name] /= max(len(batch), 1)
                self._adam_update(accumulated, learning_rate)
            validation_probability = self.predict_proba(X_validation)
            validation_loss = float(
                -np.mean(
                    positive_weight * y_validation * np.log(validation_probability + 1e-9)
                    + (1 - y_validation) * np.log(1 - validation_probability + 1e-9)
                )
            )
            history.append(
                {"epoch": epoch + 1, "train_loss": float(np.mean(losses)), "validation_loss": validation_loss}
            )
            if validation_loss < best_loss - 1e-5:
                best_loss = validation_loss
                best_params = {name: value.copy() for name, value in self.params.items()}
                waiting = 0
            else:
                waiting += 1
                if waiting >= patience:
                    break
        if best_params is not None:
            self.params = best_params
        return pd.DataFrame(history)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return np.asarray([self.forward(sequence) for sequence in X], dtype=float)


class TorchLSTM(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, seed: int):
        super().__init__()
        torch.manual_seed(seed)
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers=1, batch_first=True)
        self.dropout = nn.Dropout(0.20)
        self.output = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        sequence, _ = self.lstm(x)
        return self.output(self.dropout(sequence[:, -1, :])).squeeze(1)


def fit_torch_lstm(
    arrays: dict[str, tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]],
    input_size: int,
    config: StudyConfig,
) -> tuple[TorchLSTM, pd.DataFrame, str]:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    X_train, y_train, _ = arrays["train"]
    X_validation, y_validation, _ = arrays["validation"]
    train_tensor = torch.tensor(X_train, dtype=torch.float32)
    target_tensor = torch.tensor(y_train, dtype=torch.float32)
    loader_generator = torch.Generator().manual_seed(config.seed)
    loader = DataLoader(
        TensorDataset(train_tensor, target_tensor),
        batch_size=32,
        shuffle=True,
        generator=loader_generator,
    )
    model = TorchLSTM(input_size, config.pytorch_hidden_size, config.seed).to(device)
    positive_weight = torch.tensor(
        [(len(y_train) - y_train.sum()) / max(y_train.sum(), 1)],
        dtype=torch.float32,
        device=device,
    )
    criterion = nn.BCEWithLogitsLoss(pos_weight=positive_weight)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=7)
    X_val_tensor = torch.tensor(X_validation, dtype=torch.float32, device=device)
    y_val_tensor = torch.tensor(y_validation, dtype=torch.float32, device=device)
    best_loss = np.inf
    best_state = None
    waiting = 0
    history = []
    for epoch in range(config.pytorch_epochs):
        model.train()
        train_losses = []
        for X_batch, y_batch in loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(float(loss.item()))
        model.eval()
        with torch.no_grad():
            validation_loss = float(criterion(model(X_val_tensor), y_val_tensor).item())
        scheduler.step(validation_loss)
        history.append(
            {"epoch": epoch + 1, "train_loss": float(np.mean(train_losses)), "validation_loss": validation_loss}
        )
        if validation_loss < best_loss - 1e-5:
            best_loss = validation_loss
            best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
            waiting = 0
        else:
            waiting += 1
            if waiting >= config.early_stopping_patience:
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    model.to(device).eval()
    return model, pd.DataFrame(history), device


def torch_probabilities(model: TorchLSTM, X: np.ndarray, device: str) -> np.ndarray:
    with torch.no_grad():
        logits = model(torch.tensor(X, dtype=torch.float32, device=device))
        return torch.sigmoid(logits).cpu().numpy()


def fit_sequence_models(
    features: pd.DataFrame,
    sample: pd.DataFrame,
    splits: dict[str, pd.DataFrame],
    config: StudyConfig,
) -> tuple[dict, dict, dict, dict]:
    columns = fixed_lstm_features(_feature_columns(sample))
    scaler, arrays = prepare_sequences(features, sample, splits, columns, config.sequence_length)
    X_train, y_train, _ = arrays["train"]
    X_validation, y_validation, _ = arrays["validation"]
    X_test, y_test, _ = arrays["test"]

    numpy_model = NumpyLSTM(len(columns), config.numpy_hidden_size, config.seed)
    numpy_history = numpy_model.fit(
        X_train,
        y_train,
        X_validation,
        y_validation,
        epochs=config.numpy_epochs,
        patience=config.early_stopping_patience,
        seed=config.seed,
    )
    torch_model, torch_history, device = fit_torch_lstm(arrays, len(columns), config)

    predictions = {
        "lstm_numpy": {
            "validation": numpy_model.predict_proba(X_validation),
            "test": numpy_model.predict_proba(X_test),
            "y_validation": y_validation.astype(int),
            "y_test": y_test.astype(int),
        },
        "lstm_pytorch": {
            "validation": torch_probabilities(torch_model, X_validation, device),
            "test": torch_probabilities(torch_model, X_test, device),
            "y_validation": y_validation.astype(int),
            "y_test": y_test.astype(int),
        },
    }
    selection = {}
    for name, probability in predictions.items():
        threshold, details = choose_operating_threshold(
            probability["y_validation"],
            probability["validation"],
            config.target_recall,
        )
        selection[name] = {"threshold": threshold, **details}

    artifacts = {
        "columns": columns,
        "scaler": scaler,
        "arrays": arrays,
        "numpy_history": numpy_history,
        "torch_history": torch_history,
        "device": device,
    }
    models = {"lstm_numpy": numpy_model, "lstm_pytorch": torch_model}
    return models, predictions, selection, artifacts


def regression_experiment(
    features: pd.DataFrame,
    df: pd.DataFrame,
    horizon: int,
    config: StudyConfig,
) -> dict:
    target = df[config.case_column].shift(-horizon)
    frame = features.copy()
    frame["target_cases"] = target
    frame["target_date"] = frame.index + pd.to_timedelta(7 * horizon, unit="D")
    frame = frame.dropna()
    target_date = pd.to_datetime(frame["target_date"])
    train = frame.loc[target_date <= pd.Timestamp(config.train_end)]
    validation = frame.loc[
        (target_date >= pd.Timestamp(config.validation_start))
        & (target_date <= pd.Timestamp(config.validation_end))
    ]
    test = frame.loc[
        (target_date >= pd.Timestamp(config.test_start))
        & (target_date <= pd.Timestamp(config.test_end))
    ]
    columns = [column for column in features.columns if column in frame]
    model = RandomForestRegressor(
        n_estimators=500,
        max_depth=8,
        min_samples_leaf=5,
        random_state=config.seed,
        n_jobs=-1,
    )
    model.fit(train[columns], np.log1p(train["target_cases"]))
    result = {}
    for name, part in {"validation": validation, "test": test}.items():
        prediction = np.expm1(model.predict(part[columns])).clip(min=0)
        truth = part["target_cases"].to_numpy()
        result[name] = {
            "n": int(len(part)),
            "mae": float(mean_absolute_error(truth, prediction)),
            "rmse": float(np.sqrt(mean_squared_error(truth, prediction))),
            "r2": float(r2_score(truth, prediction)),
        }
    return result


def evaluate_predictions(
    predictions: dict,
    selection: dict,
    config: StudyConfig,
    seed_offset: int,
) -> dict:
    result = {}
    for model_name, values in predictions.items():
        threshold = float(selection[model_name]["threshold"])
        test_metrics = classification_metrics(values["y_test"], values["test"], threshold)
        test_metrics["confidence_intervals"] = block_bootstrap_ci(
            values["y_test"], values["test"], threshold, config.seed + seed_offset
        )
        validation_metrics = classification_metrics(
            values["y_validation"], values["validation"], threshold
        )
        result[model_name] = {"validation": validation_metrics, "test": test_metrics}
    return result


def run_single_experiment(
    df: pd.DataFrame,
    features: pd.DataFrame,
    targets: pd.DataFrame,
    outbreak: pd.Series,
    horizon: int,
    target_kind: TargetKind,
    config: StudyConfig,
) -> tuple[dict, dict]:
    sample = assemble_samples(features, targets, outbreak, horizon, target_kind)
    splits = temporal_split(sample, config)
    tabular_models, tabular_predictions, tabular_selection = fit_tabular_models(splits, config)
    sequence_models, sequence_predictions, sequence_selection, sequence_artifacts = fit_sequence_models(
        features, sample, splits, config
    )
    predictions = {**tabular_predictions, **sequence_predictions}
    selection = {**tabular_selection, **sequence_selection}
    metrics = evaluate_predictions(predictions, selection, config, horizon + (100 if target_kind == "window" else 0))
    split_summary = {
        name: {
            "n": int(len(part)),
            "positive": int(part["target"].sum()),
            "prevalence": float(part["target"].mean()),
            "first_issue_date": str(part.index.min().date()),
            "last_issue_date": str(part.index.max().date()),
            "first_target_date": str(pd.to_datetime(part["target_date"]).min().date()),
            "last_target_date": str(pd.to_datetime(part["target_date"]).max().date()),
        }
        for name, part in splits.items()
    }
    result = {
        "horizon_weeks": horizon,
        "target_kind": target_kind,
        "splits": split_summary,
        "selection": selection,
        "metrics": metrics,
    }
    artifacts = {
        "sample": sample,
        "splits": splits,
        "models": {**tabular_models, **sequence_models},
        "predictions": predictions,
        "sequence": sequence_artifacts,
    }
    return result, artifacts


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Tipo não serializável: {type(value)}")


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")


def save_experiment_artifacts(
    output_dir: Path,
    experiment: dict,
    artifacts: dict,
) -> None:
    """Persiste modelos, previsões, históricos e metadados necessários à auditoria."""
    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir = output_dir / "modelos"
    prediction_dir = output_dir / "predicoes"
    model_dir.mkdir(parents=True, exist_ok=True)
    prediction_dir.mkdir(parents=True, exist_ok=True)

    models = artifacts["models"]
    joblib.dump(models["logistic_regression"], model_dir / "regressao_logistica.joblib")
    joblib.dump(models["random_forest"], model_dir / "random_forest.joblib")
    joblib.dump(artifacts["sequence"]["scaler"], model_dir / "scaler_lstm.joblib")
    torch.save(models["lstm_pytorch"].state_dict(), model_dir / "lstm_pytorch_state_dict.pt")
    np.savez(model_dir / "lstm_numpy_parametros.npz", **models["lstm_numpy"].params)
    save_json(
        model_dir / "metadados_lstm.json",
        {
            "features": artifacts["sequence"]["columns"],
            "sequence_length": int(artifacts["sequence"]["arrays"]["train"][0].shape[1]),
            "pytorch_device_during_training": artifacts["sequence"]["device"],
            "numpy_hidden_size": int(models["lstm_numpy"].hidden_size),
            "pytorch_hidden_size": int(models["lstm_pytorch"].lstm.hidden_size),
        },
    )
    artifacts["sequence"]["numpy_history"].to_csv(output_dir / "historico_lstm_numpy.csv", index=False)
    artifacts["sequence"]["torch_history"].to_csv(output_dir / "historico_lstm_pytorch.csv", index=False)

    for model_name, values in artifacts["predictions"].items():
        for split_name in ("validation", "test"):
            if model_name.startswith("lstm_"):
                dates = artifacts["sequence"]["arrays"][split_name][2]
            else:
                dates = artifacts["splits"][split_name].index
            threshold = float(experiment["selection"][model_name]["threshold"])
            probability = np.asarray(values[split_name], dtype=float)
            truth = np.asarray(values[f"y_{split_name}"], dtype=int)
            prediction = (probability >= threshold).astype(int)
            frame = pd.DataFrame(
                {
                    "issue_date": pd.DatetimeIndex(dates),
                    "target": truth,
                    "probability": probability,
                    "threshold": threshold,
                    "prediction": prediction,
                }
            )
            frame.to_csv(prediction_dir / f"{model_name}_{split_name}.csv", index=False)


def run_study(config: StudyConfig) -> tuple[dict, dict]:
    set_reproducible_seed(config.seed)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    df = load_weekly_data(config)
    audit = audit_data(df, config)
    endemic = causal_endemic_channel(df, config)
    targets = create_targets(endemic["outbreak"], config.horizons)
    features = engineer_features(df, config)
    save_json(config.output_dir / "configuracao.json", config.to_json())
    save_json(config.output_dir / "auditoria_dados.json", audit)
    endemic.to_csv(config.output_dir / "canal_endemico_causal.csv", index_label="date")

    results = {"config": config.to_json(), "data_audit": audit, "experiments": {}}
    artifacts = {}
    for target_kind in config.target_kinds:
        results["experiments"][target_kind] = {}
        artifacts[target_kind] = {}
        for horizon in config.horizons:
            print(f"[estudo] iniciando alvo={target_kind}, horizonte={horizon} semanas", flush=True)
            experiment, experiment_artifacts = run_single_experiment(
                df, features, targets, endemic["outbreak"], horizon, target_kind, config
            )
            results["experiments"][target_kind][str(horizon)] = experiment
            artifacts[target_kind][horizon] = experiment_artifacts
            save_json(
                config.output_dir / target_kind / f"{horizon:02d}_semanas" / "resultados.json",
                experiment,
            )
            save_experiment_artifacts(
                config.output_dir / target_kind / f"{horizon:02d}_semanas",
                experiment,
                experiment_artifacts,
            )
            print(f"[estudo] concluído alvo={target_kind}, horizonte={horizon} semanas", flush=True)

    results["regression"] = {
        str(horizon): regression_experiment(features, df, horizon, config)
        for horizon in config.horizons
    }
    save_json(config.output_dir / "resultados_completos.json", results)
    return results, artifacts
