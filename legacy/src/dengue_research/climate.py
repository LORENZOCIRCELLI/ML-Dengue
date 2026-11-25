"""Camada climática do Projeto Mestre.

Esta camada mantém duas regras simples e auditáveis:

* casos e clima local só entram depois de pelo menos uma semana;
* índices oceânico-atmosféricos entram depois de quatro semanas, como hipótese
  conservadora de disponibilidade. A latência real deve ser confirmada na fonte.

As fases ENSO são categorias descritivas baseadas no ONI. Elas não substituem a
classificação oficial de episódios da NOAA e não são usadas como prova causal.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from .epidemiology import EpidemiologicalConfig


LOCAL_CLIMATE_COLUMNS = (
    "media_temperatura_semana",
    "amplitude_termica_semana",
    "media_ponto_orvalho_semana",
    "media_umidade_semana",
    "chuva_total_mm",
    "numero_dias_com_chuva_semana",
    "dias_com_tempestade",
)

GLOBAL_CLIMATE_COLUMNS = ("ONI", "AMM_SST", "AMM_WIND", "AAO_SAM")

FEATURE_LABELS = {
    "week_sin": "Sazonalidade anual (seno)",
    "week_cos": "Sazonalidade anual (cosseno)",
    "media_temperatura_semana": "Temperatura média disponível",
    "media_umidade_semana": "Umidade média disponível",
    "chuva_total_mm": "Chuva total disponível",
    "ONI": "Índice ONI disponível",
    "AMM_SST": "Temperatura do Atlântico tropical disponível",
    "AMM_WIND": "Vento do Atlântico tropical disponível",
    "AAO_SAM": "Oscilação Antártica disponível",
}


def classify_enso_phase(
    oni: pd.Series,
    warm_threshold: float = 0.5,
    cold_threshold: float = -0.5,
) -> pd.Series:
    """Classificação operacional simples para descrição e exportação.

    ONI já é um índice de média móvel trimestral. A persistência oficial de cinco
    estações sobrepostas não é inferida aqui porque a proveniência da coluna ainda
    precisa ser documentada. Por isso, o resultado é chamado de ``fase_operacional``.
    """
    numeric = pd.to_numeric(oni, errors="coerce")
    phase = pd.Series("neutro", index=numeric.index, dtype="object")
    phase.loc[numeric >= warm_threshold] = "el_nino"
    phase.loc[numeric <= cold_threshold] = "la_nina"
    phase.loc[numeric.isna()] = "indisponivel"
    return phase


def _week_series(df: pd.DataFrame) -> pd.Series:
    if "semana_epidemiologica" in df:
        return df["semana_epidemiologica"].astype(float)
    return pd.Series(
        (df.index + pd.Timedelta(days=1)).isocalendar().week.to_numpy(dtype=float),
        index=df.index,
    )


def build_master_features(
    df: pd.DataFrame,
    channel: pd.DataFrame,
    config: EpidemiologicalConfig,
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Cria atributos causais e os grupos usados na análise de remoção.

    Os nomes canônicos ``media_temperatura_semana``, ``media_umidade_semana``,
    ``chuva_total_mm`` e ``ONI`` são mantidos para compatibilidade com a LSTM
    existente. Nesta camada eles significam o valor *mais recente disponível*:
    uma semana de atraso para clima local e quatro semanas para ONI.
    """
    incidence = channel["incidence_per_100k"].astype(float)
    observed_incidence = incidence.shift(1)
    week = _week_series(df)

    values: dict[str, pd.Series | np.ndarray] = {}
    groups: dict[str, list[str]] = {
        "seasonality": [],
        "epidemiology": [],
        "local_climate": [],
        "enso": [],
        "other_global_climate": [],
    }

    def add(name: str, value: pd.Series | np.ndarray, group: str) -> None:
        values[name] = value
        groups[group].append(name)

    add("week_sin", np.sin(2 * np.pi * week / 52.1775), "seasonality")
    add("week_cos", np.cos(2 * np.pi * week / 52.1775), "seasonality")
    time_index = np.arange(len(df), dtype=float) / max(len(df) - 1, 1)
    add("time_trend", time_index, "seasonality")

    for lag in (1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 26, 52):
        add(f"incidence_lag_{lag}", incidence.shift(lag), "epidemiology")
        add(f"log_incidence_lag_{lag}", np.log1p(incidence.shift(lag)), "epidemiology")

    for window in (4, 8, 12, 26, 52):
        rolling = observed_incidence.rolling(window, min_periods=window)
        add(f"incidence_mean_{window}", rolling.mean(), "epidemiology")
        add(f"incidence_std_{window}", rolling.std(), "epidemiology")
        add(f"incidence_max_{window}", rolling.max(), "epidemiology")
        add(f"incidence_min_{window}", rolling.min(), "epidemiology")

    add("incidence_diff_1", observed_incidence.diff(1), "epidemiology")
    add("incidence_diff_4", observed_incidence.diff(4), "epidemiology")
    add("incidence_pct_1", observed_incidence.pct_change(1), "epidemiology")
    add("incidence_pct_4", observed_incidence.pct_change(4), "epidemiology")
    add("channel_upper_current", channel["channel_upper"].astype(float), "epidemiology")
    add(
        "incidence_ratio_upper_lag1",
        observed_incidence / channel["channel_upper"].astype(float),
        "epidemiology",
    )
    add(
        "incidence_excess_upper_lag1",
        observed_incidence - channel["channel_upper"].astype(float),
        "epidemiology",
    )

    for column in LOCAL_CLIMATE_COLUMNS:
        if column not in df:
            continue
        series = pd.to_numeric(df[column], errors="coerce")
        # Alias compatível com a seleção fixa da LSTM; o conteúdo é t-1.
        add(column, series.shift(1), "local_climate")
        for lag in (1, 2, 4, 8, 12, 16, 26):
            name = f"{column}_lag_{lag}"
            if name not in values:
                add(name, series.shift(lag), "local_climate")
        observed = series.shift(1)
        for window in (4, 8, 12):
            add(
                f"{column}_mean_{window}",
                observed.rolling(window, min_periods=window).mean(),
                "local_climate",
            )

    for column in GLOBAL_CLIMATE_COLUMNS:
        if column not in df:
            continue
        series = pd.to_numeric(df[column], errors="coerce")
        group = "enso" if column == "ONI" else "other_global_climate"
        # Alias compatível com a LSTM; hipótese conservadora de t-4.
        add(column, series.shift(4), group)
        for lag in (4, 8, 12, 16, 26, 52):
            name = f"{column}_lag_{lag}"
            if name not in values:
                add(name, series.shift(lag), group)

    if "ONI" in df:
        phase = classify_enso_phase(pd.to_numeric(df["ONI"], errors="coerce").shift(4))
        for category in ("el_nino", "la_nina", "neutro"):
            add(
                f"enso_{category}_lag_4",
                phase.eq(category).astype(float),
                "enso",
            )

    features = pd.DataFrame(values, index=df.index).replace([np.inf, -np.inf], np.nan)
    seasonality = groups["seasonality"]
    epidemiology = groups["epidemiology"]
    local = groups["local_climate"]
    enso = groups["enso"]
    other_global = groups["other_global_climate"]
    groups.update(
        {
            "seasonal_only": list(seasonality),
            "epidemiology_only": list(dict.fromkeys(seasonality + epidemiology)),
            "climate_only": list(dict.fromkeys(seasonality + local + enso + other_global)),
            "full_without_enso": list(
                dict.fromkeys(seasonality + epidemiology + local + other_global)
            ),
            "full": list(
                dict.fromkeys(seasonality + epidemiology + local + enso + other_global)
            ),
        }
    )
    return features, groups


def _moving_block_indices(
    n: int,
    block_length: int,
    rng: np.random.Generator,
) -> np.ndarray:
    positions: list[int] = []
    while len(positions) < n:
        start = int(rng.integers(0, max(n - block_length + 1, 1)))
        positions.extend(range(start, min(start + block_length, n)))
    return np.asarray(positions[:n], dtype=int)


def _spearman_with_ci(
    x: np.ndarray,
    y: np.ndarray,
    seed: int,
    n_bootstrap: int,
    block_length: int = 8,
) -> tuple[float, float, float]:
    valid = np.isfinite(x) & np.isfinite(y)
    x = np.asarray(x[valid], dtype=float)
    y = np.asarray(y[valid], dtype=float)
    if len(x) < 20 or np.unique(x).size < 2 or np.unique(y).size < 2:
        return np.nan, np.nan, np.nan
    estimate = float(pd.Series(x).corr(pd.Series(y), method="spearman"))
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(n_bootstrap):
        idx = _moving_block_indices(len(x), block_length, rng)
        value = pd.Series(x[idx]).corr(pd.Series(y[idx]), method="spearman")
        if np.isfinite(value):
            samples.append(float(value))
    if not samples:
        return estimate, np.nan, np.nan
    return estimate, float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))


def climate_lag_associations(
    features: pd.DataFrame,
    channel: pd.DataFrame,
    horizons: Iterable[int],
    seed: int = 42,
    n_bootstrap: int = 300,
) -> pd.DataFrame:
    """Associações descritivas com IC em blocos; não são estimativas causais."""
    candidates = [
        name
        for name in (
            "media_temperatura_semana_lag_1",
            "media_temperatura_semana_lag_4",
            "media_temperatura_semana_lag_8",
            "media_temperatura_semana_lag_12",
            "media_umidade_semana_lag_1",
            "media_umidade_semana_lag_4",
            "media_umidade_semana_lag_8",
            "media_umidade_semana_lag_12",
            "chuva_total_mm_lag_1",
            "chuva_total_mm_lag_4",
            "chuva_total_mm_lag_8",
            "chuva_total_mm_lag_12",
            "ONI_lag_4",
            "ONI_lag_8",
            "ONI_lag_12",
            "ONI_lag_16",
            "ONI_lag_26",
        )
        if name in features
    ]
    rows: list[dict] = []
    for horizon in horizons:
        future_incidence = channel["incidence_per_100k"].shift(-horizon)
        future_alert = channel["alert_state"].shift(-horizon)
        for offset, feature in enumerate(candidates):
            x = features[feature].to_numpy(dtype=float)
            for outcome_name, outcome in (
                ("incidencia_futura", future_incidence),
                ("alerta_futuro", future_alert),
            ):
                estimate, lower, upper = _spearman_with_ci(
                    x,
                    pd.to_numeric(outcome, errors="coerce").to_numpy(dtype=float),
                    seed + 1000 * horizon + 10 * offset + (1 if outcome_name == "alerta_futuro" else 0),
                    n_bootstrap,
                )
                rows.append(
                    {
                        "horizon_weeks": int(horizon),
                        "feature": feature,
                        "outcome": outcome_name,
                        "spearman": estimate,
                        "lower_95": lower,
                        "upper_95": upper,
                        "interpretation": "associação descritiva; não causal",
                    }
                )
    return pd.DataFrame(rows)


def enso_outcome_summary(
    df: pd.DataFrame,
    channel: pd.DataFrame,
    horizons: Iterable[int],
    availability_lag_weeks: int = 4,
) -> pd.DataFrame:
    """Resume desfechos futuros pela fase ENSO disponível na emissão."""
    if "ONI" not in df:
        return pd.DataFrame()
    phase = classify_enso_phase(
        pd.to_numeric(df["ONI"], errors="coerce").shift(availability_lag_weeks)
    )
    rows: list[dict] = []
    for horizon in horizons:
        frame = pd.DataFrame(
            {
                "phase": phase,
                "future_incidence": channel["incidence_per_100k"].shift(-horizon),
                "future_alert": channel["alert_state"].shift(-horizon),
            }
        ).dropna()
        for phase_name, part in frame.groupby("phase", sort=True):
            rows.append(
                {
                    "horizon_weeks": int(horizon),
                    "enso_phase": str(phase_name),
                    "n_weeks": int(len(part)),
                    "mean_future_incidence": float(part["future_incidence"].mean()),
                    "median_future_incidence": float(part["future_incidence"].median()),
                    "future_alert_prevalence": float(part["future_alert"].mean()),
                }
            )
    return pd.DataFrame(rows)


def feature_labels(features: Iterable[str]) -> dict[str, str]:
    """Rótulos legíveis sem alterar o nome técnico exportado."""
    result = {}
    for name in features:
        if name in FEATURE_LABELS:
            result[name] = FEATURE_LABELS[name]
            continue
        label = name.replace("_", " ")
        label = label.replace("lag ", "há ").replace(" mean ", " média ")
        result[name] = label.capitalize()
    return result
