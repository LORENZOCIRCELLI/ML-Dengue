"""Relatórios e figuras da especificação epidemiológica."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.calibration import calibration_curve
from sklearn.metrics import precision_recall_curve, roc_curve

from .reporting import MODEL_LABELS, markdown_table, metrics_frame, save_comparison_plots, save_prevalence_plot, split_frame


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def episode_metrics_frame(results: dict) -> pd.DataFrame:
    rows = []
    for horizon, experiment in results["experiments"]["window"].items():
        for model, values in experiment.get("episode_metrics", {}).items():
            rows.append(
                {
                    "horizon": int(horizon),
                    "model": model,
                    "model_label": MODEL_LABELS.get(model, model),
                    **{key: value for key, value in values.items() if key != "episode_details"},
                }
            )
    return pd.DataFrame(rows)


def save_channel_figure(channel: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")
    for suffix, frame in (
        ("completo", channel),
        ("teste_2024_2025", channel.loc["2024":"2025"]),
    ):
        fig, ax = plt.subplots(figsize=(16, 6))
        ax.plot(frame.index, frame["incidence_per_100k"], color="#264653", lw=1.7, label="Incidência")
        ax.plot(frame.index, frame["channel_median"], color="#2a9d8f", lw=1.3, label="Mediana histórica")
        ax.plot(frame.index, frame["channel_upper"], color="#e76f51", lw=1.5, label="Limite superior")
        alert = frame["alert_state"].fillna(0).astype(bool)
        ax.fill_between(
            frame.index,
            0,
            frame["incidence_per_100k"],
            where=alert,
            color="#d62828",
            alpha=0.25,
            label="Estado de alerta",
        )
        ax.set_title("Canal endêmico causal em incidência por 100 mil", fontweight="bold")
        ax.set_xlabel("Semana epidemiológica")
        ax.set_ylabel("Casos por 100 mil habitantes")
        ax.legend(ncol=4, loc="upper right")
        fig.tight_layout()
        fig.savefig(output_dir / f"canal_endemico_{suffix}.png", dpi=180, bbox_inches="tight")
        plt.close(fig)


def save_sensitivity_figure(sensitivity: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = sensitivity.copy()
    frame["specification"] = (
        frame["upper_method"].replace(
            {"mean_plus_1_96_sd": "média+1,96DP", "p90": "P90", "p95": "P95"}
        )
        + "; "
        + frame["persistence_weeks"].astype(str)
        + " sem."
    )
    fig, axes = plt.subplots(1, 2, figsize=(16, 5))
    sns.boxplot(data=frame, x="specification", y="jaccard_vs_primary", ax=axes[0], color="#8ecae6")
    sns.boxplot(data=frame, x="specification", y="alert_weeks", ax=axes[1], color="#ffb703")
    axes[0].set(title="Concordância com a especificação principal", xlabel="Limite; persistência", ylabel="Jaccard")
    axes[1].set(title="Semanas classificadas em alerta", xlabel="Limite; persistência", ylabel="Semanas")
    for ax in axes:
        ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(output_dir / "sensibilidade_definicao.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_diagnostic_curves(project_root: Path, output_dir: Path) -> None:
    colors = {"logistic_regression": "#2a9d8f", "random_forest": "#457b9d", "lstm_pytorch": "#e63946"}
    output_dir.mkdir(parents=True, exist_ok=True)
    for horizon in (4, 8, 12, 16):
        prediction_dir = project_root / "outputs/revisao_epidemiologica/exact" / f"{horizon:02d}_semanas/predicoes"
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        prevalence = None
        for model, color in colors.items():
            frame = pd.read_csv(prediction_dir / f"{model}_test.csv")
            y = frame["target"].to_numpy()
            probability = frame["probability"].to_numpy()
            prevalence = float(y.mean())
            precision, recall, _ = precision_recall_curve(y, probability)
            fpr, tpr, _ = roc_curve(y, probability)
            observed, predicted = calibration_curve(y, probability, n_bins=5, strategy="quantile")
            label = MODEL_LABELS[model]
            axes[0].plot(recall, precision, label=label, color=color, linewidth=2)
            axes[1].plot(fpr, tpr, label=label, color=color, linewidth=2)
            axes[2].plot(predicted, observed, marker="o", label=label, color=color, linewidth=2)
        axes[0].axhline(prevalence, color="gray", linestyle="--", linewidth=1, label="Prevalência")
        axes[0].set(title="Precisão–recall", xlabel="Recall", ylabel="Precisão", xlim=(0, 1), ylim=(0, 1.02))
        axes[1].plot([0, 1], [0, 1], "k--", linewidth=1)
        axes[1].set(title="ROC", xlabel="Taxa de falsos positivos", ylabel="Taxa de verdadeiros positivos", xlim=(0, 1), ylim=(0, 1.02))
        axes[2].plot([0, 1], [0, 1], "k--", linewidth=1)
        axes[2].set(title="Calibração", xlabel="Probabilidade prevista", ylabel="Frequência observada", xlim=(0, 1), ylim=(0, 1.02))
        for ax in axes:
            ax.legend(fontsize=8)
        fig.suptitle(f"Diagnóstico do estado de alerta — horizonte {horizon} semanas", fontweight="bold")
        fig.tight_layout()
        fig.savefig(output_dir / f"diagnostico_{horizon:02d}_semanas.png", dpi=180, bbox_inches="tight")
        plt.close(fig)


def _best_by_horizon(metrics: pd.DataFrame) -> pd.DataFrame:
    return (
        metrics.loc[(metrics.target_kind == "exact") & (metrics.split == "test")]
        .sort_values(["horizon", "pr_auc"], ascending=[True, False])
        .groupby("horizon", as_index=False)
        .head(1)
    )


def build_comparison(old: dict, new: dict, project_root: Path) -> tuple[str, pd.DataFrame]:
    old_metrics = metrics_frame(old)
    new_metrics = metrics_frame(new)
    old_best = _best_by_horizon(old_metrics).assign(definition="P75 causal anterior")
    new_best = _best_by_horizon(new_metrics).assign(definition="Incidência/canal oficial-alinhado")
    best = pd.concat([old_best, new_best], ignore_index=True)
    old_channel = pd.read_csv(project_root / "outputs/revisao_metodologica/canal_endemico_causal.csv", parse_dates=["date"]).set_index("date")
    new_channel = pd.read_csv(project_root / "outputs/revisao_epidemiologica/canal_endemico_epidemiologico.csv", parse_dates=["date"]).set_index("date")
    aligned = old_channel[["outbreak"]].join(new_channel[["alert_state"]], how="inner").dropna()
    old_label = aligned["outbreak"].astype(int).astype(bool)
    new_label = aligned["alert_state"].astype(int).astype(bool)
    intersection = int((old_label & new_label).sum())
    union = int((old_label | new_label).sum())
    agreement = float((old_label == new_label).mean())
    jaccard = float(intersection / union) if union else 1.0
    table = best[["definition", "horizon", "model_label", "prevalence", "pr_auc", "precision", "recall_sensitivity", "false_alarms_per_year"]]
    text = f"""# Comparação entre as duas definições de desfecho

## Leitura correta da comparação

As duas versões não diferem apenas em código: elas medem construtos distintos. A versão anterior usa contagens e um P75 causal com persistência de três semanas. A versão epidemiológica usa incidência por 100 mil, limite superior em escala logarítmica e quatro semanas consecutivas. Assim, diferenças de desempenho não devem ser interpretadas como uma competição direta entre modelos sobre o mesmo problema.

## Concordância dos rótulos semanais

- Semanas válidas comparadas: {len(aligned)}.
- Concordância bruta: {agreement:.3f}.
- Jaccard entre semanas positivas: {jaccard:.3f}.
- Positivos na definição anterior: {int(old_label.sum())}; positivos na nova definição: {int(new_label.sum())}.

## Melhor PR-AUC por horizonte em cada definição

{markdown_table(table.sort_values(['horizon', 'definition']), ['definition', 'horizon', 'model_label', 'prevalence', 'pr_auc', 'precision', 'recall_sensitivity', 'false_alarms_per_year'])}

## Conclusão comparativa

A especificação epidemiológica é mais defensável como desfecho primário porque normaliza por população, separa estado de alerta de início de episódio e ancora os parâmetros em orientações sanitárias. A versão P75 permanece útil como análise de sensibilidade histórica. Métricas de uma versão não validam a outra, e a estabilidade da conclusão deve ser julgada pela concordância da ordenação dos modelos, pelas curvas fora da amostra e pelo desempenho por episódio.
"""
    return text, best


def build_report(results: dict, project_root: Path) -> str:
    metrics = metrics_frame(results)
    exact_test = metrics.loc[(metrics.target_kind == "exact") & (metrics.split == "test")].sort_values(["horizon", "pr_auc"], ascending=[True, False])
    splits = split_frame(results)
    exact_splits = splits.loc[splits.target_kind == "exact"].sort_values(["horizon", "split"])
    event = episode_metrics_frame(results).sort_values(["horizon", "episode_recall", "false_warning_weeks_per_year"], ascending=[True, False, True])
    episodes = pd.DataFrame(results["episode_summary"]["episodes"])
    sensitivity = pd.read_csv(project_root / "outputs/revisao_epidemiologica/sensibilidade_definicao.csv")
    regression = pd.DataFrame(
        [{"horizon": int(h), **values["test"]} for h, values in results["regression_incidence"].items()]
    )
    captum_rows = []
    for horizon in (4, 8, 12, 16):
        path = project_root / "outputs/revisao_epidemiologica/exact" / f"{horizon:02d}_semanas/captum/integrated_gradients_features.csv"
        top = pd.read_csv(path).head(5)
        for rank, row in enumerate(top.itertuples(index=False), start=1):
            captum_rows.append({"horizon": horizon, "rank": rank, "feature": row.feature, "mean_absolute_attribution": row.mean_absolute_attribution, "mean_signed_attribution": row.mean_signed_attribution})
    captum = pd.DataFrame(captum_rows)
    audit = results["data_audit"]
    pop = results["population_audit"]
    sensitivity_primary = sensitivity.loc[sensitivity.is_primary.astype(bool)].iloc[0]
    best = _best_by_horizon(metrics)
    learned_models = exact_test.loc[
        ~exact_test["model"].isin(["seasonal_baseline", "persistence_baseline"])
    ]
    best_learned = (
        learned_models.sort_values(["horizon", "pr_auc"], ascending=[True, False])
        .groupby("horizon", as_index=False)
        .head(1)
    )
    pytorch_rows = exact_test.loc[exact_test["model"] == "lstm_pytorch"]

    return f"""# Relatório da redefinição epidemiológica e do estudo preditivo

## 1. Pergunta de pesquisa

O sistema usa somente informações disponíveis até a semana de emissão `t` para estimar: (1) o estado operacional de alerta exatamente em `t+h`; e (2) o início de um novo episódio de alerta em qualquer semana entre `t+1` e `t+h`, para horizontes de 4, 8, 12 e 16 semanas.

O termo **alerta** é deliberado. O canal endêmico, isoladamente, não comprova transmissão epidêmica nem substitui a decisão da vigilância, que também considera crescimento, gravidade, hospitalizações, óbitos, capacidade assistencial e contexto local.

## 2. Fontes metodológicas

A especificação foi ancorada no [Plano de Contingência Nacional para Dengue, Chikungunya e Zika 2025](https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/guias-e-manuais/2025/plano-de-contingencia-nacional-para-dengue-chikungunya-e-zika.pdf/@@download/file), que descreve mobilização após incidência acima da mediana e alerta após incidência acima do limite superior por quatro semanas consecutivas, e nas [diretrizes da OMS para dengue](https://tdr.who.int/docs/librariesprovider10/meeting-reports/dengue-diagnosis-pdf.pdf?download=true&sfvrsn=ef5ec264_0), que orientam canal com cinco a sete anos históricos, média semanal e limite superior próximo de dois desvios-padrão.

## 3. Dados e auditoria

- Período: {audit['start']} a {audit['end']}.
- Observações: {audit['n_rows']} semanas, sem datas duplicadas e com frequência {audit['frequency']}.
- Casos semanais: mínimo {audit['case_min']:.0f}, mediana {audit['case_median']:.1f}, média {audit['case_mean']:.1f}, máximo {audit['case_max']:.0f}.
- Denominador `dem`: {pop['minimum']:.0f} a {pop['maximum']:.0f}, {pop['n_unique']} valores, sem ausências ou valores não positivos.

O arquivo técnico existente não contém dicionário de dados. Portanto, `dem` é tratado como hipótese operacional de população residente, não como proveniência confirmada. A série muda de 711.825 para 702.739 em 2023-02-05. Antes de submissão da tese, devem ser documentados fonte, ano de referência, método de interpolação e unidade de cada coluna.

## 4. Definição epidemiológica

### 4.1 Incidência

`incidência(t) = casos(t) / dem(t) × 100.000`.

### 4.2 Canal endêmico causal

Para cada semana `t`, o histórico inclui apenas anos anteriores, até sete anos, e semanas epidemiológicas em ±2 semanas. Exigem-se pelo menos três anos. Aplica-se `log1p` à incidência; o centro geométrico é `expm1(média(log1p))` e o limite superior é `expm1(média + 1,96 × DP)`. Nenhum dado futuro entra no canal de uma semana passada.

### 4.3 Estados operacionais

- 0 — rotina: critério persistente não preenchido;
- 1 — mobilização: incidência acima da mediana, mas não acima do limite superior, por quatro semanas consecutivas;
- 2 — alerta: incidência acima do limite superior por quatro semanas consecutivas.

O alvo binário primário é `estado == 2`. O início de episódio é a transição de não-alerta para alerta. Foram identificados {results['episode_summary']['n_episodes']} episódios e {results['episode_summary']['n_alert_weeks']} semanas em alerta.

{markdown_table(episodes, ['episode_id', 'start', 'end', 'duration_weeks', 'peak_incidence_per_100k', 'mean_incidence_per_100k'])}

## 5. Desenho temporal e prevenção de vazamento

- Treino: data-alvo até 2021-12-26.
- Validação: data-alvo de 2022-01-02 a 2023-12-31.
- Teste final: data-alvo de 2024-01-07 a 2025-12-28.
- Casos/incidência entram com atraso mínimo de uma semana.
- Escalonadores usam somente o treino.
- Random Forest usa folds anuais expansivos dentro do treino.
- Early stopping e limiares usam validação; o teste não decide parâmetros.

{markdown_table(exact_splits, ['horizon', 'split', 'n', 'positive', 'prevalence', 'first_target_date', 'last_target_date'])}

## 6. Entradas e modelos

As entradas incluem incidência defasada, transformações `log1p`, estatísticas móveis, razão entre incidência recente e limite atual, sazonalidade, clima e índices oceânico-atmosféricos. Colunas espaciais e Google Trends continuam excluídas até que proveniência, cobertura e latência sejam documentadas.

Foram comparados baseline sazonal, baseline de persistência, regressão logística, Random Forest, LSTM NumPy com BPTT completo e LSTM PyTorch. A LSTM NumPy foi preservada como comparação didática, não como candidata preferencial de implantação.

## 7. Resultado semanal do estado de alerta no teste

{markdown_table(exact_test, ['horizon', 'model_label', 'prevalence', 'pr_auc', 'roc_auc', 'precision', 'recall_sensitivity', 'specificity', 'f2', 'brier', 'false_alarms_per_year'])}

### 7.1 Maior PR-AUC global por horizonte

{markdown_table(best, ['horizon', 'model_label', 'pr_auc', 'precision', 'recall_sensitivity', 'false_alarms_per_year'])}

Nos horizontes de 4 e 8 semanas, o baseline de persistência aparece no topo, mas o limiar selecionado classifica todas as semanas como positivas: recall 1, especificidade 0 e aproximadamente 42,6 alarmes falsos por ano. Isso não representa utilidade operacional.

### 7.2 Melhor modelo aprendido por horizonte

{markdown_table(best_learned, ['horizon', 'model_label', 'pr_auc', 'precision', 'recall_sensitivity', 'specificity', 'false_alarms_per_year'])}

A regressão logística é o melhor modelo aprendido em 8, 12 e 16 semanas; a LSTM NumPy lidera entre os aprendidos em 4 semanas, embora com PR-AUC baixa. Nenhum modelo demonstra desempenho suficientemente estável para implantação.

### 7.3 Resultado específico da LSTM PyTorch

{markdown_table(pytorch_rows, ['horizon', 'prevalence', 'pr_auc', 'roc_auc', 'precision', 'recall_sensitivity', 'specificity', 'false_alarms_per_year'])}

A PR-AUC da LSTM PyTorch fica abaixo da prevalência do teste nos quatro horizontes. Assim, Captum continua útil para auditar o comportamento do modelo, mas não transforma um modelo mal generalizado em candidato operacional. PR-AUC é a métrica de discriminação principal por causa do desbalanceamento; recall e alarmes falsos descrevem a operação no limiar escolhido na validação.

## 8. Avaliação por início de episódio

O modelo secundário pergunta se um episódio começará nas próximas `h` semanas. Um episódio é detectado quando existe ao menos um alerta do modelo entre `início-h` e `início-1`. A métrica de antecedência usa o primeiro aviso dentro dessa janela. Há somente dois inícios no teste, portanto os valores são descritivos e possuem enorme incerteza.

{markdown_table(event, ['horizon', 'model_label', 'n_test_episodes', 'episodes_detected', 'episode_recall', 'median_maximum_lead_weeks', 'false_warning_weeks_per_year'])}

## 9. Regressão de incidência

{markdown_table(regression.sort_values('horizon'), ['horizon', 'n', 'mae', 'rmse', 'r2'])}

A regressão é secundária. R² negativo significa que o modelo não supera uma referência constante no período final e deve ser reportado como resultado negativo, sem seleção retrospectiva do horizonte favorável.

## 10. Explicabilidade da LSTM PyTorch

Captum Integrated Gradients e Occlusion foram aplicados somente ao teste. O baseline zero no espaço padronizado corresponde à média do treino. As atribuições explicam a saída do modelo, não relações causais nem efeitos de intervenção.

{markdown_table(captum, ['horizon', 'rank', 'feature', 'mean_absolute_attribution', 'mean_signed_attribution'])}

## 11. Sensibilidade da definição

Foram avaliadas {len(sensitivity)} especificações: cinco ou sete anos, raio ±1 ou ±2, limites média+1,96DP/P90/P95 e persistência de três ou quatro semanas. A concordância Jaccard com a principal variou de {sensitivity.jaccard_vs_primary.min():.3f} a {sensitivity.jaccard_vs_primary.max():.3f}, mediana {sensitivity.jaccard_vs_primary.median():.3f}. A especificação principal produziu {int(sensitivity_primary.alert_weeks)} semanas e {int(sensitivity_primary.episodes)} episódios.

Essa variação mostra que a incerteza do construto é material. O resultado principal deve ser acompanhado pela sensibilidade; não é aceitável escolher a definição depois de observar qual produz a melhor métrica preditiva.

## 12. O que foi modificado

| Componente | Versão anterior | Nova versão | Razão |
|---|---|---|---|
| Escala | contagem semanal | incidência por 100 mil | comparabilidade populacional |
| Canal | P75 causal | média log + 1,96DP, sete anos | alinhamento a orientação epidemiológica |
| Persistência | três semanas + média móvel | quatro semanas consecutivas | alinhamento ao plano nacional |
| Desfecho principal | surto estatístico | estado operacional de alerta | validade do construto |
| Desfecho secundário | qualquer semana positiva na janela | início de novo episódio | evita inflar o alvo por episódios longos |
| Avaliação | métricas semanais | semanais + episódios + antecedência | utilidade operacional |
| Sensibilidade | recomendada | 24 definições executadas | quantificar incerteza da definição |
| Regressão | número de casos | incidência | coerência de escala |
| Explicabilidade | Captum no LSTM | mantida com features de incidência | interpretação do modelo final |

## 13. Limitações e validade

### Validade do construto

O canal identifica um **alerta estatístico**. Sem dados de gravidade, hospitalização, óbito, sorotipo, cobertura diagnóstica e decisão oficial, não deve ser chamado de epidemia confirmada. A definição precisa de validação por epidemiologista e confronto com registros oficiais de surtos.

### Validade interna

O pipeline controla vazamento temporal conhecido, mas assume que clima da semana está disponível ao fim da semana e que índices externos têm a latência representada. Revisões tardias de casos e clima ainda não são modeladas.

### Validade externa

Há uma única série municipal. O teste 2024–2025 não substitui validação em outros municípios, validação prospectiva ou avaliação sob mudança de vigilância.

### Poder estatístico

Existem apenas seis episódios no total, dois no treino, dois na validação e dois no teste. Deep learning está em regime de amostra pequena; múltiplas sementes e incerteza entre episódios são necessárias antes de conclusões fortes.

## 14. Julgamento de defensabilidade

Esta versão é substancialmente mais defensável do que o notebook original para apresentar uma metodologia de pesquisa: o tempo está explícito, o canal é causal, o desfecho possui interpretação epidemiológica, o teste é preservado e há sensibilidade. Ela ainda não é prova suficiente para implantação clínica ou de vigilância. Para a tese, as pendências críticas são: confirmar o dicionário e as fontes; obter rótulos oficiais independentes; validar externamente; repetir sementes; e pré-registrar a especificação principal.

## 15. Reprodutibilidade

O notebook original permanece intacto. Esta especificação está em `src/dengue_research/epidemiology.py`, a execução em `scripts/run_epidemiological_study.py`, o notebook em `notebooks/Notebook_Definicao_Epidemiologica.ipynb` e os artefatos em `outputs/revisao_epidemiologica`.
"""


def generate_epidemiological_reports(project_root: Path) -> None:
    output_dir = project_root / "outputs/revisao_epidemiologica"
    results = _load(output_dir / "resultados_completos.json")
    metrics = metrics_frame(results)
    splits = split_frame(results)
    event = episode_metrics_frame(results)
    metrics.to_csv(output_dir / "metricas_consolidadas.csv", index=False)
    splits.to_csv(output_dir / "particoes_temporais.csv", index=False)
    event.to_csv(output_dir / "metricas_episodios.csv", index=False)
    figures = output_dir / "figuras"
    save_comparison_plots(metrics, figures)
    save_prevalence_plot(splits, figures)
    save_diagnostic_curves(project_root, figures)
    channel = pd.read_csv(output_dir / "canal_endemico_epidemiologico.csv", parse_dates=["date"]).set_index("date")
    sensitivity = pd.read_csv(output_dir / "sensibilidade_definicao.csv")
    save_channel_figure(channel, figures)
    save_sensitivity_figure(sensitivity, figures)

    report_dir = project_root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "relatorio_definicao_epidemiologica.md").write_text(
        build_report(results, project_root), encoding="utf-8"
    )
    old = _load(project_root / "outputs/revisao_metodologica/resultados_completos.json")
    comparison, best = build_comparison(old, results, project_root)
    (report_dir / "comparacao_definicoes.md").write_text(comparison, encoding="utf-8")
    best.to_csv(output_dir / "comparacao_melhores_modelos.csv", index=False)
