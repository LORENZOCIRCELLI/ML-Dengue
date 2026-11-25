"""Explicabilidade do LSTM PyTorch com Captum."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import torch
from captum.attr import IntegratedGradients, Occlusion
import matplotlib.pyplot as plt
import seaborn as sns


def explain_single_torch_lstm(
    model: torch.nn.Module,
    sequence: np.ndarray,
    feature_names: list[str],
    device: str,
    n_steps: int = 64,
) -> dict:
    """Explica uma previsão para exportação ao aplicativo.

    O baseline zero corresponde à média do treino no espaço padronizado. O sinal
    informa se a entrada deslocou o logit para cima ou para baixo em relação a
    esse baseline; não representa efeito causal epidemiológico.
    """
    array = np.asarray(sequence, dtype=np.float32)
    if array.ndim == 2:
        array = array[None, ...]
    if array.ndim != 3 or array.shape[0] != 1:
        raise ValueError("A explicação individual exige uma única sequência 3D.")
    if array.shape[2] != len(feature_names):
        raise ValueError("Quantidade de nomes não corresponde às features da sequência.")

    model.eval()
    inputs = torch.tensor(array, dtype=torch.float32, device=device, requires_grad=True)
    baseline = torch.zeros_like(inputs)
    method = IntegratedGradients(model)
    attribution, delta = method.attribute(
        inputs,
        baselines=baseline,
        n_steps=n_steps,
        method="gausslegendre",
        return_convergence_delta=True,
    )
    values = attribution.detach().cpu().numpy()[0]
    feature_signed = values.sum(axis=0)
    feature_absolute = np.abs(values).sum(axis=0)
    time_signed = values.sum(axis=1)
    time_absolute = np.abs(values).sum(axis=1)
    absolute_total = float(feature_absolute.sum())

    feature_rows = []
    for name, signed, absolute in zip(feature_names, feature_signed, feature_absolute):
        feature_rows.append(
            {
                "feature": name,
                "signed_attribution": float(signed),
                "absolute_attribution": float(absolute),
                "normalized_importance": float(absolute / absolute_total) if absolute_total else 0.0,
                "direction": "aumentou" if signed > 0 else "reduziu" if signed < 0 else "neutro",
            }
        )
    feature_rows.sort(key=lambda row: row["absolute_attribution"], reverse=True)

    relative_weeks = np.arange(-array.shape[1] + 1, 1)
    time_rows = [
        {
            "relative_week": int(relative_week),
            "weeks_ago": int(abs(relative_week)),
            "signed_attribution": float(signed),
            "absolute_attribution": float(absolute),
        }
        for relative_week, signed, absolute in zip(relative_weeks, time_signed, time_absolute)
    ]
    heatmap_rows = []
    for time_idx, relative_week in enumerate(relative_weeks):
        for feature_idx, feature in enumerate(feature_names):
            heatmap_rows.append(
                {
                    "relative_week": int(relative_week),
                    "weeks_ago": int(abs(relative_week)),
                    "feature": feature,
                    "signed_attribution": float(values[time_idx, feature_idx]),
                    "absolute_attribution": float(abs(values[time_idx, feature_idx])),
                }
            )
    return {
        "method": "integrated_gradients",
        "baseline": "zero no espaço padronizado (média do treino)",
        "convergence_delta": float(delta.detach().cpu().numpy().reshape(-1)[0]),
        "feature_importance": feature_rows,
        "temporal_importance": time_rows,
        "heatmap": heatmap_rows,
        "interpretation": (
            "contribuição ao logit previsto em relação ao baseline; não representa causalidade"
        ),
    }


def explain_torch_lstm(
    model: torch.nn.Module,
    X_test: np.ndarray,
    y_test: np.ndarray,
    dates: pd.DatetimeIndex,
    feature_names: list[str],
    output_dir: Path,
    device: str,
    probabilities: np.ndarray | None = None,
    threshold: float | None = None,
    max_occlusion_samples: int = 32,
) -> dict:
    """Calcula atribuições fora da amostra; zero representa a média do treino padronizado."""
    output_dir.mkdir(parents=True, exist_ok=True)
    model.eval()
    inputs = torch.tensor(X_test, dtype=torch.float32, device=device, requires_grad=True)
    baselines = torch.zeros_like(inputs)

    integrated_gradients = IntegratedGradients(model)
    ig_attr, convergence_delta = integrated_gradients.attribute(
        inputs,
        baselines=baselines,
        n_steps=64,
        method="gausslegendre",
        return_convergence_delta=True,
    )
    ig = ig_attr.detach().cpu().numpy()
    delta = convergence_delta.detach().cpu().numpy()

    global_feature = pd.DataFrame(
        {
            "feature": feature_names,
            "mean_absolute_attribution": np.mean(np.abs(ig), axis=(0, 1)),
            "mean_signed_attribution": np.mean(ig, axis=(0, 1)),
        }
    ).sort_values("mean_absolute_attribution", ascending=False)
    global_time = pd.DataFrame(
        {
            "relative_week": np.arange(-X_test.shape[1] + 1, 1),
            "mean_absolute_attribution": np.mean(np.abs(ig), axis=(0, 2)),
            "mean_signed_attribution": np.mean(ig, axis=(0, 2)),
        }
    )
    global_feature.to_csv(output_dir / "integrated_gradients_features.csv", index=False)
    global_time.to_csv(output_dir / "integrated_gradients_tempo.csv", index=False)
    heatmap = pd.DataFrame(
        np.mean(np.abs(ig), axis=0),
        index=np.arange(-X_test.shape[1] + 1, 1),
        columns=feature_names,
    )
    heatmap.to_csv(output_dir / "integrated_gradients_mapa_tempo_feature.csv", index_label="relative_week")
    np.save(output_dir / "integrated_gradients_amostras.npy", ig)

    fig, ax = plt.subplots(figsize=(15, 6))
    sns.heatmap(heatmap, cmap="mako", ax=ax)
    ax.set_title("Integrated Gradients: atribuição absoluta média por semana e feature", fontweight="bold")
    ax.set_xlabel("Feature")
    ax.set_ylabel("Semana relativa à emissão")
    fig.tight_layout()
    fig.savefig(output_dir / "integrated_gradients_heatmap.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    sample_count = min(max_occlusion_samples, len(X_test))
    if sample_count:
        # Seleção determinística e distribuída ao longo do teste.
        selected = np.linspace(0, len(X_test) - 1, sample_count, dtype=int)
        occlusion_input = inputs[selected].detach().clone().requires_grad_(True)
        occlusion = Occlusion(model)
        occlusion_attr = occlusion.attribute(
            occlusion_input,
            baselines=torch.zeros_like(occlusion_input),
            sliding_window_shapes=(1, 1),
            strides=(1, 1),
            perturbations_per_eval=128,
        ).detach().cpu().numpy()
        occlusion_global = pd.DataFrame(
            {
                "feature": feature_names,
                "mean_absolute_attribution": np.mean(np.abs(occlusion_attr), axis=(0, 1)),
                "mean_signed_attribution": np.mean(occlusion_attr, axis=(0, 1)),
            }
        ).sort_values("mean_absolute_attribution", ascending=False)
        occlusion_global.to_csv(output_dir / "occlusion_features.csv", index=False)
    else:
        selected = np.array([], dtype=int)

    sample_summary = pd.DataFrame(
        {
            "issue_date": dates.astype(str),
            "target": y_test.astype(int),
            "ig_absolute_sum": np.abs(ig).sum(axis=(1, 2)),
            "ig_signed_sum": ig.sum(axis=(1, 2)),
            "convergence_delta": delta,
        }
    )
    if probabilities is not None and threshold is not None:
        probabilities = np.asarray(probabilities, dtype=float)
        predictions = (probabilities >= threshold).astype(int)
        sample_summary["probability"] = probabilities
        sample_summary["threshold"] = float(threshold)
        sample_summary["prediction"] = predictions
        sample_summary["outcome_group"] = np.select(
            [
                (y_test == 1) & (predictions == 1),
                (y_test == 0) & (predictions == 1),
                (y_test == 1) & (predictions == 0),
                (y_test == 0) & (predictions == 0),
            ],
            ["true_positive", "false_positive", "false_negative", "true_negative"],
            default="unknown",
        )
        group_rows = []
        for group in ("true_positive", "false_positive", "false_negative", "true_negative"):
            mask = sample_summary["outcome_group"].to_numpy() == group
            if not mask.any():
                continue
            group_attr = np.mean(np.abs(ig[mask]), axis=(0, 1))
            for feature, attribution in zip(feature_names, group_attr):
                group_rows.append(
                    {"outcome_group": group, "feature": feature, "mean_absolute_attribution": attribution}
                )
        pd.DataFrame(group_rows).to_csv(output_dir / "integrated_gradients_por_resultado.csv", index=False)
    sample_summary.to_csv(output_dir / "integrated_gradients_amostras.csv", index=False)
    return {
        "n_explained": int(len(X_test)),
        "n_occlusion": int(len(selected)),
        "mean_absolute_convergence_delta": float(np.mean(np.abs(delta))),
        "baseline": "vetor zero no espaço padronizado (média do treino)",
        "interpretation": "atribuição ao logit previsto; não representa causalidade epidemiológica",
    }
