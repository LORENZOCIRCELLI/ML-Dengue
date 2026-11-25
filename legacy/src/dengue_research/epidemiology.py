"""Definição epidemiológica causal e avaliação orientada a episódios.

Esta camada não substitui a revisão estatística anterior. Ela cria uma segunda
especificação, baseada em incidência, canal endêmico em escala logarítmica e
estados operacionais alinhados ao plano brasileiro de contingência.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Literal

import numpy as np
import pandas as pd

from .pipeline import (
    StudyConfig,
    _circular_week_distance,
    audit_data,
    load_weekly_data,
    regression_experiment,
    run_single_experiment,
    save_experiment_artifacts,
    save_json,
    set_reproducible_seed,
)


UpperMethod = Literal["mean_plus_1_96_sd", "p90", "p95"]


@dataclass(frozen=True)
class EpidemiologicalConfig(StudyConfig):
    output_dir: Path = Path("outputs/revisao_epidemiologica")
    population_column: str = "dem"
    endemic_lookback_years: int = 7
    endemic_week_radius: int = 2
    endemic_min_years: int = 3
    persistence_weeks: int = 4
    upper_method: UpperMethod = "mean_plus_1_96_sd"
    upper_z: float = 1.96


def _run_length(condition: np.ndarray) -> np.ndarray:
    result = np.zeros(len(condition), dtype=int)
    for idx, value in enumerate(condition):
        if bool(value):
            result[idx] = 1 + (result[idx - 1] if idx else 0)
    return result


def population_audit(df: pd.DataFrame, config: EpidemiologicalConfig) -> dict:
    population = df[config.population_column].astype(float)
    changes = df.loc[population.ne(population.shift()), [config.population_column]]
    return {
        "column": config.population_column,
        "interpretation_status": (
            "hipótese operacional de população residente; confirmar no dicionário e na fonte da base"
        ),
        "missing": int(population.isna().sum()),
        "non_positive": int((population <= 0).sum()),
        "minimum": float(population.min()),
        "maximum": float(population.max()),
        "n_unique": int(population.nunique()),
        "changes": [
            {"date": str(date.date()), "value": float(row[config.population_column])}
            for date, row in changes.iterrows()
        ],
    }


def causal_epidemiological_channel(
    df: pd.DataFrame,
    config: EpidemiologicalConfig,
) -> pd.DataFrame:
    """Canal causal: usa somente anos anteriores à semana que está sendo rotulada."""
    population = df[config.population_column].astype(float)
    if population.isna().any() or (population <= 0).any():
        raise ValueError("O denominador populacional contém valores ausentes ou não positivos.")

    incidence = df[config.case_column].astype(float) / population * 100_000.0
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
    log_incidence = np.log1p(incidence.to_numpy(dtype=float))
    n = len(df)
    center = np.full(n, np.nan, dtype=float)
    median = np.full(n, np.nan, dtype=float)
    upper = np.full(n, np.nan, dtype=float)
    history_n = np.zeros(n, dtype=int)
    history_years = np.zeros(n, dtype=int)

    for pos, (year, week) in enumerate(zip(years, weeks)):
        past_year = (years < year) & (years >= year - config.endemic_lookback_years)
        similar_week = _circular_week_distance(weeks, int(week)) <= config.endemic_week_radius
        mask = past_year & similar_week
        n_years = len(np.unique(years[mask]))
        history_years[pos] = n_years
        history_n[pos] = int(mask.sum())
        if n_years < config.endemic_min_years:
            continue
        history_log = log_incidence[mask]
        history_raw = incidence.to_numpy(dtype=float)[mask]
        center[pos] = float(np.expm1(np.mean(history_log)))
        median[pos] = float(np.median(history_raw))
        if config.upper_method == "mean_plus_1_96_sd":
            upper[pos] = float(
                np.expm1(np.mean(history_log) + config.upper_z * np.std(history_log, ddof=1))
            )
        elif config.upper_method == "p90":
            upper[pos] = float(np.quantile(history_raw, 0.90))
        elif config.upper_method == "p95":
            upper[pos] = float(np.quantile(history_raw, 0.95))
        else:
            raise ValueError(f"Método de limite superior desconhecido: {config.upper_method}")

    values = incidence.to_numpy(dtype=float)
    valid = ~np.isnan(upper)
    above_median = valid & (values > median)
    above_upper = valid & (values > upper)
    # Mobilização exige permanência acima da mediana e abaixo do limite superior.
    mobilization_condition = above_median & ~above_upper
    mobilization_run = _run_length(mobilization_condition)
    alert_run = _run_length(above_upper)
    alert = valid & (alert_run >= config.persistence_weeks)
    mobilization = valid & ~alert & (mobilization_run >= config.persistence_weeks)
    state = np.full(n, np.nan, dtype=float)
    state[valid] = 0.0
    state[mobilization] = 1.0
    state[alert] = 2.0
    alert_state = np.full(n, np.nan, dtype=float)
    alert_state[valid] = alert[valid].astype(float)
    previous_alert = np.r_[False, alert[:-1]]
    alert_onset = np.full(n, np.nan, dtype=float)
    alert_onset[valid] = (alert & ~previous_alert)[valid].astype(float)

    return pd.DataFrame(
        {
            "incidence_per_100k": incidence,
            "channel_geometric_mean": center,
            "channel_median": median,
            "channel_upper": upper,
            "channel_history_n": history_n,
            "channel_history_years": history_years,
            "above_median": above_median.astype(int),
            "above_upper": above_upper.astype(int),
            "mobilization_run": mobilization_run,
            "alert_run": alert_run,
            "operational_state": pd.Series(state, index=df.index, dtype="Float64"),
            "alert_state": pd.Series(alert_state, index=df.index, dtype="Float64"),
            "alert_onset": pd.Series(alert_onset, index=df.index, dtype="Float64"),
        },
        index=df.index,
    )


def create_epidemiological_targets(
    alert_state: pd.Series,
    alert_onset: pd.Series,
    horizons: Iterable[int],
) -> pd.DataFrame:
    """Primário: estado de alerta em t+h; secundário: início de episódio em t+1..t+h."""
    targets = pd.DataFrame(index=alert_state.index)
    for horizon in horizons:
        targets[f"target_exact_{horizon}"] = alert_state.shift(-horizon)
        future_onsets = pd.concat(
            [alert_onset.shift(-step) for step in range(1, horizon + 1)], axis=1
        )
        targets[f"target_window_{horizon}"] = future_onsets.max(axis=1, skipna=False)
    return targets


def engineer_incidence_features(
    df: pd.DataFrame,
    channel: pd.DataFrame,
    config: EpidemiologicalConfig,
) -> pd.DataFrame:
    """Features disponíveis na emissão; incidência notificada entra com uma semana de atraso."""
    incidence = channel["incidence_per_100k"].astype(float)
    observed = incidence.shift(1)
    feature_series: dict[str, pd.Series | np.ndarray] = {}
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
        feature_series[f"incidence_lag_{lag}"] = incidence.shift(lag)
        feature_series[f"log_incidence_lag_{lag}"] = np.log1p(incidence.shift(lag))

    for window in (4, 8, 12, 26, 52):
        rolling = observed.rolling(window, min_periods=window)
        feature_series[f"incidence_mean_{window}"] = rolling.mean()
        feature_series[f"incidence_std_{window}"] = rolling.std()
        feature_series[f"incidence_max_{window}"] = rolling.max()
        feature_series[f"incidence_min_{window}"] = rolling.min()

    feature_series["incidence_diff_1"] = observed.diff(1)
    feature_series["incidence_diff_4"] = observed.diff(4)
    feature_series["incidence_pct_1"] = observed.pct_change(1)
    feature_series["incidence_pct_4"] = observed.pct_change(4)
    feature_series["channel_upper_current"] = channel["channel_upper"].astype(float)
    feature_series["incidence_ratio_upper_lag1"] = observed / channel["channel_upper"].astype(float)
    feature_series["incidence_excess_upper_lag1"] = observed - channel["channel_upper"].astype(float)

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
            feature_series[f"{column}_mean_{window}"] = series.rolling(
                window, min_periods=window
            ).mean()

    for column in ("ONI", "AMM_SST", "AMM_WIND", "AAO_SAM"):
        if column not in df:
            continue
        series = df[column].astype(float)
        feature_series[column] = series
        for lag in (4, 8, 12):
            feature_series[f"{column}_lag_{lag}"] = series.shift(lag)

    return pd.DataFrame(feature_series, index=df.index).replace([np.inf, -np.inf], np.nan)


def episode_table(channel: pd.DataFrame) -> pd.DataFrame:
    alert = channel["alert_state"].fillna(0).astype(bool).to_numpy()
    starts = np.flatnonzero(alert & ~np.r_[False, alert[:-1]])
    rows = []
    for episode_id, start in enumerate(starts, start=1):
        end = start
        while end + 1 < len(alert) and alert[end + 1]:
            end += 1
        segment = channel.iloc[start : end + 1]
        rows.append(
            {
                "episode_id": episode_id,
                "start": channel.index[start],
                "end": channel.index[end],
                "duration_weeks": int(end - start + 1),
                "peak_incidence_per_100k": float(segment["incidence_per_100k"].max()),
                "mean_incidence_per_100k": float(segment["incidence_per_100k"].mean()),
            }
        )
    return pd.DataFrame(rows)


def episode_warning_metrics(
    prediction_dates: pd.DatetimeIndex,
    probabilities: np.ndarray,
    threshold: float,
    onset: pd.Series,
    horizon: int,
    config: EpidemiologicalConfig,
) -> dict:
    predicted = np.asarray(probabilities, dtype=float) >= float(threshold)
    prediction_dates = pd.DatetimeIndex(prediction_dates)
    test_onsets = onset.loc[
        (onset.index >= pd.Timestamp(config.test_start))
        & (onset.index <= pd.Timestamp(config.test_end))
        & (onset.fillna(0).astype(int) == 1)
    ].index
    detections = []
    linked_prediction = np.zeros(len(prediction_dates), dtype=bool)
    for onset_date in test_onsets:
        earliest = onset_date - pd.Timedelta(weeks=horizon)
        latest = onset_date - pd.Timedelta(weeks=1)
        in_window = (prediction_dates >= earliest) & (prediction_dates <= latest)
        positive_in_window = in_window & predicted
        linked_prediction |= positive_in_window
        dates = prediction_dates[positive_in_window]
        detections.append(
            {
                "onset_date": str(onset_date.date()),
                "detected": bool(len(dates)),
                "maximum_lead_weeks": (
                    int((onset_date - dates.min()).days // 7) if len(dates) else None
                ),
                "last_warning_lead_weeks": (
                    int((onset_date - dates.max()).days // 7) if len(dates) else None
                ),
                "n_warning_weeks": int(len(dates)),
            }
        )
    lead_times = [row["maximum_lead_weeks"] for row in detections if row["detected"]]
    n_years = max(len(prediction_dates) / 52.1775, 1e-9)
    false_warning_weeks = int(np.sum(predicted & ~linked_prediction))
    return {
        "n_test_episodes": int(len(test_onsets)),
        "episodes_detected": int(sum(row["detected"] for row in detections)),
        "episode_recall": (
            float(np.mean([row["detected"] for row in detections])) if detections else np.nan
        ),
        "median_maximum_lead_weeks": float(np.median(lead_times)) if lead_times else np.nan,
        "false_warning_weeks": false_warning_weeks,
        "false_warning_weeks_per_year": float(false_warning_weeks / n_years),
        "episode_details": detections,
    }


def sensitivity_analysis(
    df: pd.DataFrame,
    primary: pd.DataFrame,
    config: EpidemiologicalConfig,
) -> pd.DataFrame:
    primary_alert = primary["alert_state"].fillna(0).astype(bool)
    rows = []
    for lookback in (5, 7):
        for radius in (1, 2):
            for method in ("mean_plus_1_96_sd", "p90", "p95"):
                for persistence in (3, 4):
                    variant = replace(
                        config,
                        endemic_lookback_years=lookback,
                        endemic_week_radius=radius,
                        upper_method=method,
                        persistence_weeks=persistence,
                    )
                    channel = causal_epidemiological_channel(df, variant)
                    alert = channel["alert_state"].fillna(0).astype(bool)
                    valid = primary["alert_state"].notna() & channel["alert_state"].notna()
                    intersection = int((primary_alert[valid] & alert[valid]).sum())
                    union = int((primary_alert[valid] | alert[valid]).sum())
                    episodes = episode_table(channel)
                    rows.append(
                        {
                            "lookback_years": lookback,
                            "week_radius": radius,
                            "upper_method": method,
                            "persistence_weeks": persistence,
                            "alert_weeks": int(alert.sum()),
                            "episodes": int(len(episodes)),
                            "jaccard_vs_primary": float(intersection / union) if union else 1.0,
                            "train_alert_weeks": int(
                                alert.loc[alert.index <= pd.Timestamp(config.train_end)].sum()
                            ),
                            "validation_alert_weeks": int(
                                alert.loc[
                                    (alert.index >= pd.Timestamp(config.validation_start))
                                    & (alert.index <= pd.Timestamp(config.validation_end))
                                ].sum()
                            ),
                            "test_alert_weeks": int(
                                alert.loc[
                                    (alert.index >= pd.Timestamp(config.test_start))
                                    & (alert.index <= pd.Timestamp(config.test_end))
                                ].sum()
                            ),
                            "is_primary": bool(
                                lookback == config.endemic_lookback_years
                                and radius == config.endemic_week_radius
                                and method == config.upper_method
                                and persistence == config.persistence_weeks
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def run_epidemiological_study(config: EpidemiologicalConfig) -> tuple[dict, dict]:
    set_reproducible_seed(config.seed)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    df = load_weekly_data(config)
    audit = audit_data(df, config)
    pop_audit = population_audit(df, config)
    channel = causal_epidemiological_channel(df, config)
    targets = create_epidemiological_targets(
        channel["alert_state"], channel["alert_onset"], config.horizons
    )
    features = engineer_incidence_features(df, channel, config)
    episodes = episode_table(channel)
    sensitivity = sensitivity_analysis(df, channel, config)

    save_json(config.output_dir / "configuracao.json", config.to_json())
    save_json(config.output_dir / "auditoria_dados.json", audit)
    save_json(config.output_dir / "auditoria_denominador.json", pop_audit)
    channel.to_csv(config.output_dir / "canal_endemico_epidemiologico.csv", index_label="date")
    episodes.to_csv(config.output_dir / "episodios_alerta.csv", index=False)
    sensitivity.to_csv(config.output_dir / "sensibilidade_definicao.csv", index=False)

    results = {
        "config": config.to_json(),
        "data_audit": audit,
        "population_audit": pop_audit,
        "definition": {
            "incidence_scale": "casos por 100.000 habitantes",
            "primary_target": "estado de alerta em t+h",
            "secondary_target": "início de episódio de alerta entre t+1 e t+h",
            "state_codes": {"0": "rotina", "1": "mobilização", "2": "alerta"},
            "terminology_note": (
                "alerta pelo canal endêmico; não equivale sozinho à declaração oficial de epidemia"
            ),
        },
        "episode_summary": {
            "n_episodes": int(len(episodes)),
            "n_alert_weeks": int(channel["alert_state"].fillna(0).sum()),
            "episodes": episodes.assign(
                start=episodes["start"].astype(str), end=episodes["end"].astype(str)
            ).to_dict(orient="records"),
        },
        "sensitivity_summary": {
            "n_specifications": int(len(sensitivity)),
            "jaccard_min": float(sensitivity["jaccard_vs_primary"].min()),
            "jaccard_median": float(sensitivity["jaccard_vs_primary"].median()),
            "jaccard_max": float(sensitivity["jaccard_vs_primary"].max()),
        },
        "experiments": {},
    }
    artifacts: dict = {}
    for target_kind in config.target_kinds:
        results["experiments"][target_kind] = {}
        artifacts[target_kind] = {}
        baseline_state = channel["alert_state"] if target_kind == "exact" else channel["alert_onset"]
        for horizon in config.horizons:
            print(
                f"[epidemiologia] iniciando alvo={target_kind}, horizonte={horizon} semanas",
                flush=True,
            )
            experiment, experiment_artifacts = run_single_experiment(
                df,
                features,
                targets,
                baseline_state,
                horizon,
                target_kind,
                config,
            )
            if target_kind == "window":
                event_metrics = {}
                for model_name, values in experiment_artifacts["predictions"].items():
                    if model_name.startswith("lstm_"):
                        dates = experiment_artifacts["sequence"]["arrays"]["test"][2]
                    else:
                        dates = experiment_artifacts["splits"]["test"].index
                    event_metrics[model_name] = episode_warning_metrics(
                        dates,
                        values["test"],
                        experiment["selection"][model_name]["threshold"],
                        channel["alert_onset"],
                        horizon,
                        config,
                    )
                experiment["episode_metrics"] = event_metrics
            results["experiments"][target_kind][str(horizon)] = experiment
            artifacts[target_kind][horizon] = experiment_artifacts
            experiment_dir = config.output_dir / target_kind / f"{horizon:02d}_semanas"
            save_json(experiment_dir / "resultados.json", experiment)
            save_experiment_artifacts(experiment_dir, experiment, experiment_artifacts)
            print(
                f"[epidemiologia] concluído alvo={target_kind}, horizonte={horizon} semanas",
                flush=True,
            )

    incidence_df = df.copy()
    incidence_df["incidence_per_100k"] = channel["incidence_per_100k"]
    incidence_config = EpidemiologicalConfig(
        **{**config.__dict__, "case_column": "incidence_per_100k"}
    )
    results["regression_incidence"] = {
        str(horizon): regression_experiment(features, incidence_df, horizon, incidence_config)
        for horizon in config.horizons
    }
    save_json(config.output_dir / "resultados_completos.json", results)
    return results, artifacts
