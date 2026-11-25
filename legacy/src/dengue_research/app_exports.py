"""Exportações estáveis para o aplicativo, sem alterar o JSON legado."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
import json
import math
import os
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from .climate import classify_enso_phase, feature_labels
from .explainability import explain_single_torch_lstm
from .pipeline import seasonal_baseline, torch_probabilities


SCHEMA_VERSION = "1.0.0"


def _clean_json(value: Any) -> Any:
    """Converte objetos científicos e troca não-finitos por null."""
    if is_dataclass(value):
        return _clean_json(asdict(value))
    if isinstance(value, dict):
        return {str(key): _clean_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray, pd.Index, pd.Series)):
        return [_clean_json(item) for item in list(value)]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if value is pd.NA:
        return None
    return value


def save_strict_json(path: Path, payload: dict) -> None:
    """Grava JSON padrão de forma atômica; NaN e Infinity são proibidos."""
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = _clean_json(payload)
    serialized = json.dumps(clean, ensure_ascii=False, indent=2, allow_nan=False)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(serialized + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _risk_level(probability: float, threshold: float) -> str:
    """Faixas relativas ao limiar validado; não são categorias clínicas."""
    if threshold <= 0:
        return "indeterminado"
    ratio = probability / threshold
    if ratio < 0.5:
        return "baixo"
    if ratio < 1.0:
        return "moderado"
    return "alto"


def latest_scaled_sequence(
    features: pd.DataFrame,
    columns: list[str],
    scaler,
    sequence_length: int,
) -> tuple[np.ndarray, pd.DatetimeIndex]:
    valid = features[columns].dropna()
    if len(valid) < sequence_length:
        raise ValueError("Não há semanas suficientes para a previsão mais recente.")
    tail = valid.iloc[-sequence_length:]
    expected = pd.date_range(tail.index[0], tail.index[-1], freq="W-SUN")
    if not tail.index.equals(expected):
        raise ValueError("A sequência final não contém semanas consecutivas.")
    transformed = scaler.transform(tail).astype(np.float32)
    return transformed[None, ...], pd.DatetimeIndex(tail.index)


def _scientific_status(test_metrics: dict) -> dict:
    pr_auc = float(test_metrics.get("pr_auc", np.nan))
    prevalence = float(test_metrics.get("prevalence", np.nan))
    if np.isfinite(pr_auc) and np.isfinite(prevalence) and pr_auc > prevalence:
        code = "acima_da_referencia_de_prevalencia"
    else:
        code = "nao_superou_referencia_de_prevalencia"
    return {
        "code": code,
        "researchOnly": True,
        "publicHealthDecisionReady": False,
        "message": (
            "Resultado destinado à pesquisa. Não deve ser usado isoladamente para decisões de saúde pública."
        ),
    }


def _historical_prediction_rows(
    dates: pd.DatetimeIndex,
    probabilities: np.ndarray,
    truths: np.ndarray,
    threshold: float,
    horizon: int,
) -> list[dict]:
    rows = []
    for issue_date, probability, truth in zip(dates, probabilities, truths):
        target_date = issue_date + pd.Timedelta(weeks=horizon)
        rows.append(
            {
                "dataEmissao": str(issue_date.date()),
                "dataAlvo": str(target_date.date()),
                "probabilidade": float(probability),
                "limiar": float(threshold),
                "alertaPrevisto": bool(probability >= threshold),
                "alertaObservado": bool(truth),
            }
        )
    return rows


def _save_explanation_figures(payload: dict, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    features = pd.DataFrame(payload["explicacaoAtual"]["importanciaVariaveis"])
    top = features.head(12).sort_values("importanciaNormalizada")
    colors = ["#c95a48" if value == "aumentou" else "#3975a6" for value in top["direcao"]]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top["nomeExibicao"], top["importanciaNormalizada"], color=colors)
    ax.set_xlabel("Importância normalizada")
    ax.set_title("Fatores da previsão atual — Integrated Gradients", fontweight="bold")
    fig.tight_layout()
    fig.savefig(figure_dir / "captum_importancia_variaveis.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    temporal = pd.DataFrame(payload["explicacaoAtual"]["importanciaTemporal"])
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(temporal["semanasAtras"].astype(str), temporal["atribuicaoAbsoluta"], color="#245987")
    ax.set_xlabel("Semanas anteriores na sequência")
    ax.set_ylabel("Atribuição absoluta")
    ax.set_title("Importância temporal da previsão atual", fontweight="bold")
    fig.tight_layout()
    fig.savefig(figure_dir / "captum_importancia_temporal.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def export_horizon_app_payloads(
    *,
    app_root: Path,
    horizon: int,
    features: pd.DataFrame,
    raw_data: pd.DataFrame,
    channel: pd.DataFrame,
    experiment: dict,
    artifacts: dict,
    global_explanation_dir: Path,
    model_version: str,
    source_notebook: str,
) -> dict[str, Path]:
    """Exporta previsões e Captum; ``app_dados_dengue.json`` não é tocado."""
    horizon_root = app_root / f"{horizon:02d}_semanas"
    data_dir = horizon_root / "dados"
    metrics_dir = horizon_root / "metricas"
    figure_dir = horizon_root / "figuras"
    data_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    sequence = artifacts["sequence"]
    model = artifacts["models"]["lstm_pytorch"]
    columns = list(sequence["columns"])
    device = sequence["device"]
    scaler = sequence["scaler"]
    threshold = float(experiment["selection"]["lstm_pytorch"]["threshold"])
    latest_X, latest_dates = latest_scaled_sequence(
        features, columns, scaler, int(sequence["arrays"]["train"][0].shape[1])
    )
    probability = float(torch_probabilities(model, latest_X, device)[0])
    issue_date = latest_dates[-1]
    target_date = issue_date + pd.Timedelta(weeks=horizon)
    explanation = explain_single_torch_lstm(model, latest_X, columns, device)
    labels = feature_labels(columns)

    feature_rows = [
        {
            "variavel": row["feature"],
            "nomeExibicao": labels[row["feature"]],
            "importanciaNormalizada": row["normalized_importance"],
            "atribuicaoAbsoluta": row["absolute_attribution"],
            "contribuicao": row["signed_attribution"],
            "direcao": row["direction"],
        }
        for row in explanation["feature_importance"]
    ]
    temporal_rows = [
        {
            "semanaRelativa": row["relative_week"],
            "semanasAtras": row["weeks_ago"],
            "atribuicaoAbsoluta": row["absolute_attribution"],
            "contribuicao": row["signed_attribution"],
        }
        for row in explanation["temporal_importance"]
    ]
    heatmap_rows = [
        {
            "semanaRelativa": row["relative_week"],
            "semanasAtras": row["weeks_ago"],
            "variavel": row["feature"],
            "nomeExibicao": labels[row["feature"]],
            "contribuicao": row["signed_attribution"],
            "atribuicaoAbsoluta": row["absolute_attribution"],
        }
        for row in explanation["heatmap"]
    ]

    global_features_path = global_explanation_dir / "integrated_gradients_features.csv"
    global_time_path = global_explanation_dir / "integrated_gradients_tempo.csv"
    global_features = pd.read_csv(global_features_path) if global_features_path.exists() else pd.DataFrame()
    global_time = pd.read_csv(global_time_path) if global_time_path.exists() else pd.DataFrame()
    global_feature_rows = []
    if not global_features.empty:
        total = float(global_features["mean_absolute_attribution"].sum())
        for row in global_features.itertuples(index=False):
            global_feature_rows.append(
                {
                    "variavel": row.feature,
                    "nomeExibicao": labels.get(row.feature, row.feature),
                    "importanciaMediaAbsoluta": row.mean_absolute_attribution,
                    "contribuicaoMedia": row.mean_signed_attribution,
                    "importanciaNormalizada": row.mean_absolute_attribution / total if total else 0.0,
                }
            )

    phase = "indisponivel"
    oni_available = None
    if "ONI" in raw_data:
        available = pd.to_numeric(raw_data["ONI"], errors="coerce").shift(4)
        phase = str(classify_enso_phase(available).iloc[-1])
        oni_available = float(available.iloc[-1]) if np.isfinite(available.iloc[-1]) else None

    generated_at = datetime.now(timezone.utc).isoformat()
    current_probabilities: dict[str, float] = {"lstm_pytorch": probability}
    current_probabilities["lstm_numpy"] = float(
        artifacts["models"]["lstm_numpy"].predict_proba(latest_X)[0]
    )
    for model_name in ("logistic_regression", "random_forest"):
        tabular_model = artifacts["models"][model_name]
        model_columns = list(tabular_model.feature_names_in_)
        current_probabilities[model_name] = float(
            tabular_model.predict_proba(features.loc[[issue_date], model_columns])[:, 1][0]
        )
    target_frame = pd.DataFrame({"target_date": [target_date]}, index=[issue_date])
    current_probabilities["seasonal_baseline"] = float(
        seasonal_baseline(artifacts["splits"]["train"], target_frame)[0]
    )
    current_probabilities["persistence_baseline"] = float(
        channel["alert_state"].shift(1).loc[issue_date]
    )

    current_predictions = []
    for model_name, current_probability in current_probabilities.items():
        model_threshold = float(experiment["selection"][model_name]["threshold"])
        validation_pr_auc = float(experiment["metrics"][model_name]["validation"]["pr_auc"])
        test_pr_auc = float(experiment["metrics"][model_name]["test"]["pr_auc"])
        current_predictions.append(
            {
                "modelo": model_name,
                "probabilidade": current_probability,
                "limiar": model_threshold,
                "alertaPrevisto": bool(current_probability >= model_threshold),
                "nivelRisco": _risk_level(current_probability, model_threshold),
                "prAucValidacao": validation_pr_auc,
                "prAucTesteRetrospectivo": test_pr_auc,
            }
        )
    # A escolha usa somente a validação. O teste permanece descritivo.
    current_predictions.sort(key=lambda row: row["prAucValidacao"], reverse=True)
    selected_current = dict(current_predictions[0])
    selected_current.update(
        {
            "semanaReferencia": str(issue_date.date()),
            "dataAlvo": str(target_date.date()),
            "regraSelecaoModelo": "maior PR AUC na validação",
            "regraNivelRisco": "baixo < 50% do limiar; moderado < limiar; alto >= limiar",
        }
    )

    prediction_payload = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "municipio": "Ribeirão Preto",
        "horizonteSemanas": int(horizon),
        "modeloSelecionado": selected_current["modelo"],
        "versaoModelo": model_version,
        "fonteNotebook": source_notebook,
        "treinamento": {
            "ultimaDataAlvoTreino": experiment["splits"]["train"]["last_target_date"],
            "periodoValidacao": {
                "inicio": experiment["splits"]["validation"]["first_target_date"],
                "fim": experiment["splits"]["validation"]["last_target_date"],
            },
            "reajustadoComTeste": False,
            "observacao": (
                "O teste retrospectivo não foi incorporado ao ajuste deste artefato de pesquisa."
            ),
        },
        "previsaoAtual": selected_current,
        "previsoesAtuais": current_predictions,
        "situacaoClimaticaDisponivel": {
            "faseEnsoOperacional": phase,
            "oniComAtrasoDeQuatroSemanas": oni_available,
        },
        "linhaTempoPrevisoes": _historical_prediction_rows(
            sequence["arrays"]["test"][2],
            artifacts["predictions"]["lstm_pytorch"]["test"],
            artifacts["predictions"]["lstm_pytorch"]["y_test"],
            threshold,
            horizon,
        ),
        "statusCientifico": _scientific_status(
            experiment["metrics"][selected_current["modelo"]]["test"]
        ),
    }

    top_names = [row["nomeExibicao"] for row in feature_rows[:3]]
    explanation_payload = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "municipio": "Ribeirão Preto",
        "horizonteSemanas": int(horizon),
        "modelo": "lstm_pytorch",
        "versaoModelo": model_version,
        "previsaoExplicada": {
            "modelo": "lstm_pytorch",
            "semanaReferencia": str(issue_date.date()),
            "dataAlvo": str(target_date.date()),
            "probabilidade": probability,
            "limiar": threshold,
            "alertaPrevisto": bool(probability >= threshold),
            "nivelRisco": _risk_level(probability, threshold),
            "observacao": (
                "A explicação é da LSTM PyTorch, mesmo quando outro modelo foi selecionado "
                "pela validação para a previsão principal."
            ),
        },
        "resumo": {
            "texto": "Principais fatores usados pelo modelo: " + ", ".join(top_names) + ".",
            "aviso": (
                "As atribuições explicam o comportamento da LSTM em relação ao baseline; "
                "não demonstram causalidade epidemiológica."
            ),
        },
        "explicacaoAtual": {
            "metodo": explanation["method"],
            "baseline": explanation["baseline"],
            "deltaConvergencia": explanation["convergence_delta"],
            "importanciaVariaveis": feature_rows,
            "importanciaTemporal": temporal_rows,
            "mapaCalor": heatmap_rows,
        },
        "explicacaoGlobalTeste": {
            "importanciaVariaveis": global_feature_rows,
            "importanciaTemporal": (
                [
                    {
                        "semanaRelativa": int(row.relative_week),
                        "semanasAtras": int(abs(row.relative_week)),
                        "importanciaMediaAbsoluta": row.mean_absolute_attribution,
                        "contribuicaoMedia": row.mean_signed_attribution,
                    }
                    for row in global_time.itertuples(index=False)
                ]
                if not global_time.empty
                else []
            ),
        },
    }

    metrics_payload = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "horizonteSemanas": int(horizon),
        "definicaoPrincipal": "estado de alerta do canal endêmico em t+h",
        "metricas": experiment["metrics"],
        "selecaoLimiar": experiment["selection"],
        "particoes": experiment["splits"],
        "aviso": "2024–2025 é avaliação retrospectiva já examinada durante o desenvolvimento.",
    }

    prediction_path = data_dir / "app_previsoes.json"
    explanation_path = data_dir / "app_explicabilidade_lstm.json"
    metrics_path = metrics_dir / "metricas_projeto_mestre.json"
    save_strict_json(prediction_path, prediction_payload)
    save_strict_json(explanation_path, explanation_payload)
    save_strict_json(metrics_path, metrics_payload)
    _save_explanation_figures(explanation_payload, figure_dir)
    return {
        "predictions": prediction_path,
        "explainability": explanation_path,
        "metrics": metrics_path,
    }
