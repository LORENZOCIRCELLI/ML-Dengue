"""Relatório automático e figuras sintéticas do Projeto Mestre."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


FEATURE_SET_LABELS = {
    "seasonal_only": "Sazonalidade",
    "epidemiology_only": "Epidemiologia",
    "climate_only": "Clima",
    "full_without_enso": "Completo sem ENSO",
    "full": "Completo",
}


def _markdown_table(frame: pd.DataFrame, decimals: int = 3) -> str:
    rounded = frame.round(decimals).copy()
    headers = [str(column) for column in rounded.columns]
    rows = [headers, ["---"] * len(headers)]
    for values in rounded.itertuples(index=False, name=None):
        rows.append(["" if pd.isna(value) else str(value) for value in values])
    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def generate_master_report(project_root: Path) -> Path:
    output = project_root / "outputs/projeto_mestre"
    report_dir = project_root / "reports"
    figure_dir = output / "figuras"
    report_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    results = json.loads((output / "resultados_completos.json").read_text(encoding="utf-8"))
    ablation = pd.read_csv(output / "comparacao_com_sem_clima.csv")
    stability = pd.read_csv(output / "estabilidade_lstm_sementes.csv")
    enso = pd.read_csv(output / "resumo_enso.csv")
    associations = pd.read_csv(output / "associacoes_climaticas.csv")

    plot_ablation = ablation.copy()
    plot_ablation["Conjunto"] = plot_ablation["feature_set"].map(FEATURE_SET_LABELS)
    plot_ablation["Modelo"] = plot_ablation["model"].map(
        {"logistic_regression": "Regressão logística", "random_forest": "Random Forest"}
    )
    chart = sns.catplot(
        data=plot_ablation,
        x="horizon_weeks",
        y="pr_auc",
        hue="Conjunto",
        col="Modelo",
        kind="bar",
        height=5,
        aspect=1.15,
        sharey=True,
    )
    chart.set_axis_labels("Horizonte (semanas)", "PR AUC no teste retrospectivo")
    chart.figure.suptitle("Contribuição preditiva dos grupos de informação", y=1.04, fontweight="bold")
    chart.figure.savefig(figure_dir / "comparacao_com_sem_clima.png", dpi=180, bbox_inches="tight")
    plt.close(chart.figure)

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(
        data=enso,
        x="horizon_weeks",
        y="future_alert_prevalence",
        hue="enso_phase",
        ax=ax,
    )
    ax.set_xlabel("Horizonte (semanas)")
    ax.set_ylabel("Proporção futura de semanas em alerta")
    ax.set_title("Descrição do alerta futuro por fase ENSO operacional", fontweight="bold")
    fig.tight_layout()
    fig.savefig(figure_dir / "alerta_por_fase_enso.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.stripplot(data=stability, x="horizon_weeks", y="pr_auc", hue="seed", size=8, ax=ax)
    for position, horizon in enumerate(sorted(stability["horizon_weeks"].unique())):
        prevalence = float(
            ablation.loc[ablation["horizon_weeks"].eq(horizon), "prevalence"].iloc[0]
        )
        ax.hlines(
            prevalence,
            position - 0.4,
            position + 0.4,
            color="black",
            linestyle="--",
            alpha=0.35,
        )
    ax.set_xlabel("Horizonte (semanas)")
    ax.set_ylabel("PR AUC")
    ax.set_title("Instabilidade da LSTM PyTorch entre sementes", fontweight="bold")
    fig.tight_layout()
    fig.savefig(figure_dir / "estabilidade_lstm.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    best = (
        ablation.sort_values("pr_auc", ascending=False)
        .groupby(["horizon_weeks", "model"], as_index=False)
        .first()[["horizon_weeks", "model", "feature_set", "pr_auc", "prevalence", "brier"]]
    )
    top_assoc = (
        associations.assign(abs_spearman=associations["spearman"].abs())
        .sort_values("abs_spearman", ascending=False)
        .head(16)[
            ["horizon_weeks", "feature", "outcome", "spearman", "lower_95", "upper_95"]
        ]
    )
    stability_summary = stability.groupby("horizon_weeks", as_index=False).agg(
        pr_auc_mean=("pr_auc", "mean"),
        pr_auc_sd=("pr_auc", "std"),
        pr_auc_min=("pr_auc", "min"),
        pr_auc_max=("pr_auc", "max"),
    )

    lines = [
        "# Relatório do Projeto Mestre — clima, ENSO e dengue",
        "",
        "## Conclusão central",
        "",
        (
            "A série mostra diferenças descritivas entre as fases ENSO operacionais, mas o clima "
            "não apresentou ganho preditivo consistente sobre o histórico epidemiológico. O conjunto "
            "completo não venceu de forma estável entre modelos e horizontes, e a LSTM PyTorch "
            "apresentou desempenho baixo e sensível à semente. O achado deve ser relatado como "
            "associação histórica e teste de contribuição preditiva, não como causalidade."
        ),
        "",
        "## Pergunta principal",
        "",
        results["scope"]["primary_question"],
        "",
        "## Melhor conjunto por modelo e horizonte",
        "",
        _markdown_table(best),
        "",
        "A escolha acima é descritiva no teste e não autoriza selecionar retrospectivamente um novo modelo principal.",
        "",
        "## ENSO",
        "",
        _markdown_table(
            enso[
                [
                    "horizon_weeks",
                    "enso_phase",
                    "n_weeks",
                    "mean_future_incidence",
                    "future_alert_prevalence",
                ]
            ]
        ),
        "",
        "As categorias ENSO são operacionais e a diferença pode refletir sazonalidade e outros fatores.",
        "",
        "## Associações de maior magnitude",
        "",
        _markdown_table(top_assoc),
        "",
        "Os intervalos foram obtidos por bootstrap em blocos de oito semanas. São associações descritivas.",
        "",
        "## Estabilidade da LSTM",
        "",
        _markdown_table(stability_summary),
        "",
        "Uma única execução da rede não é suficiente para sustentar conclusão de superioridade.",
        "",
        "## Limites da conclusão",
        "",
        "- seis episódios na série e dois no teste retrospectivo;",
        "- uma única série municipal;",
        "- ausência atual de validação independente com eventos oficiais;",
        "- denominador populacional e latência das fontes ainda precisam de confirmação formal;",
        "- 2024–2025 foi examinado durante o desenvolvimento;",
        "- Captum explica o cálculo da LSTM e não causalidade epidemiológica.",
        "",
        "## Exportações",
        "",
        "Os quatro horizontes receberam `app_previsoes.json`, `app_explicabilidade_lstm.json` e `metricas_projeto_mestre.json`. O JSON legado foi preservado.",
    ]
    report_path = report_dir / "relatorio_projeto_mestre.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path
