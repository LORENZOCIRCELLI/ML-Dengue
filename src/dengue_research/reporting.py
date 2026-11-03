"""Tabelas, gráficos e relatório da revisão metodológica."""

from __future__ import annotations

from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.calibration import calibration_curve
from sklearn.metrics import precision_recall_curve, roc_curve


MODEL_LABELS = {
    "seasonal_baseline": "Baseline sazonal",
    "persistence_baseline": "Baseline persistência",
    "logistic_regression": "Regressão logística",
    "random_forest": "Random Forest",
    "lstm_numpy": "LSTM NumPy (BPTT)",
    "lstm_pytorch": "LSTM PyTorch",
}


def load_results(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def metrics_frame(results: dict) -> pd.DataFrame:
    rows = []
    for target_kind, horizons in results["experiments"].items():
        for horizon, experiment in horizons.items():
            for model, split_metrics in experiment["metrics"].items():
                for split, metrics in split_metrics.items():
                    row = {
                        "target_kind": target_kind,
                        "horizon": int(horizon),
                        "model": model,
                        "model_label": MODEL_LABELS.get(model, model),
                        "split": split,
                    }
                    row.update({key: value for key, value in metrics.items() if key != "confidence_intervals"})
                    rows.append(row)
    return pd.DataFrame(rows)


def split_frame(results: dict) -> pd.DataFrame:
    rows = []
    for target_kind, horizons in results["experiments"].items():
        for horizon, experiment in horizons.items():
            for split, values in experiment["splits"].items():
                rows.append({"target_kind": target_kind, "horizon": int(horizon), "split": split, **values})
    return pd.DataFrame(rows)


def save_comparison_plots(metrics: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")
    test = metrics.loc[metrics["split"] == "test"].copy()
    for target_kind in sorted(test["target_kind"].unique()):
        subset = test.loc[test["target_kind"] == target_kind]
        fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharex=True)
        for ax, metric, title in zip(
            axes,
            ("pr_auc", "recall_sensitivity", "false_alarms_per_year"),
            ("PR-AUC", "Sensibilidade (recall)", "Alarmes falsos por ano"),
        ):
            sns.lineplot(
                data=subset,
                x="horizon",
                y=metric,
                hue="model_label",
                marker="o",
                ax=ax,
            )
            ax.set_title(title)
            ax.set_xlabel("Horizonte (semanas)")
            ax.set_ylabel(title)
            ax.set_xticks([4, 8, 12, 16])
            if ax is not axes[-1]:
                ax.get_legend().remove()
        axes[-1].legend(title="Modelo", bbox_to_anchor=(1.02, 1), loc="upper left")
        fig.suptitle(f"Desempenho fora da amostra — alvo {target_kind}", fontweight="bold")
        fig.tight_layout()
        fig.savefig(output_dir / f"comparacao_{target_kind}.png", dpi=180, bbox_inches="tight")
        plt.close(fig)


def save_prevalence_plot(splits: pd.DataFrame, output_dir: Path) -> None:
    exact = splits.loc[splits["target_kind"] == "exact"].copy()
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=exact, x="horizon", y="prevalence", hue="split", ax=ax)
    ax.set_title("Prevalência do alvo por partição temporal", fontweight="bold")
    ax.set_xlabel("Horizonte (semanas)")
    ax.set_ylabel("Proporção de semanas em surto")
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(output_dir / "prevalencia_particoes.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_diagnostic_curves(project_root: Path, output_dir: Path) -> None:
    """Curvas fora da amostra dos três modelos inferenciais principais."""
    colors = {"logistic_regression": "#2a9d8f", "random_forest": "#457b9d", "lstm_pytorch": "#e63946"}
    for horizon in (4, 8, 12, 16):
        prediction_dir = (
            project_root / "outputs/revisao_metodologica/exact" / f"{horizon:02d}_semanas/predicoes"
        )
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        for model in colors:
            frame = pd.read_csv(prediction_dir / f"{model}_test.csv")
            y = frame["target"].to_numpy()
            probability = frame["probability"].to_numpy()
            precision, recall, _ = precision_recall_curve(y, probability)
            fpr, tpr, _ = roc_curve(y, probability)
            observed, predicted = calibration_curve(y, probability, n_bins=5, strategy="quantile")
            label = MODEL_LABELS[model]
            axes[0].plot(recall, precision, label=label, color=colors[model], linewidth=2)
            axes[1].plot(fpr, tpr, label=label, color=colors[model], linewidth=2)
            axes[2].plot(predicted, observed, marker="o", label=label, color=colors[model], linewidth=2)
        axes[0].axhline(y.mean(), color="gray", linestyle="--", linewidth=1, label="Prevalência")
        axes[0].set(title="Precisão–recall", xlabel="Recall", ylabel="Precisão", xlim=(0, 1), ylim=(0, 1.02))
        axes[1].plot([0, 1], [0, 1], "k--", linewidth=1)
        axes[1].set(title="ROC", xlabel="Taxa de falsos positivos", ylabel="Taxa de verdadeiros positivos", xlim=(0, 1), ylim=(0, 1.02))
        axes[2].plot([0, 1], [0, 1], "k--", linewidth=1)
        axes[2].set(title="Calibração", xlabel="Probabilidade prevista", ylabel="Frequência observada", xlim=(0, 1), ylim=(0, 1.02))
        for ax in axes:
            ax.legend(fontsize=8)
        fig.suptitle(f"Diagnóstico fora da amostra — horizonte de {horizon} semanas", fontweight="bold")
        fig.tight_layout()
        fig.savefig(output_dir / f"diagnostico_{horizon:02d}_semanas.png", dpi=180, bbox_inches="tight")
        plt.close(fig)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    selected = frame[columns].copy()
    for column in selected.select_dtypes(include=[np.number]).columns:
        if column != "horizon":
            selected[column] = selected[column].map(lambda value: f"{value:.3f}")
    headers = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in selected.to_numpy()]
    return "\n".join([headers, separator, *rows])


def build_report(results: dict, project_root: Path) -> str:
    metrics = metrics_frame(results)
    exact_test = metrics.loc[(metrics.target_kind == "exact") & (metrics.split == "test")].copy()
    exact_test = exact_test.sort_values(["horizon", "pr_auc"], ascending=[True, False])
    regression_rows = []
    for horizon, values in results["regression"].items():
        regression_rows.append({"horizon": int(horizon), **values["test"]})
    regression = pd.DataFrame(regression_rows)
    audit = results["data_audit"]
    splits = split_frame(results)
    exact_splits = splits.loc[splits.target_kind == "exact"].copy()
    thresholds = []
    intervals = []
    for horizon, experiment in results["experiments"]["exact"].items():
        for model, selection in experiment["selection"].items():
            thresholds.append(
                {
                    "horizon": int(horizon),
                    "model_label": MODEL_LABELS.get(model, model),
                    "threshold": selection["threshold"],
                    "validation_precision": selection["validation_precision"],
                    "validation_recall": selection["validation_recall"],
                }
            )
            metric = experiment["metrics"][model]["test"]
            ci = metric["confidence_intervals"]
            intervals.append(
                {
                    "horizon": int(horizon),
                    "model_label": MODEL_LABELS.get(model, model),
                    "pr_auc": metric["pr_auc"],
                    "pr_auc_ci": f"{ci['pr_auc']['lower_95']:.3f}–{ci['pr_auc']['upper_95']:.3f}",
                    "recall": metric["recall_sensitivity"],
                    "recall_ci": f"{ci['recall_sensitivity']['lower_95']:.3f}–{ci['recall_sensitivity']['upper_95']:.3f}",
                }
            )
    thresholds = pd.DataFrame(thresholds)
    intervals = pd.DataFrame(intervals)
    best_intervals = intervals.sort_values(["horizon", "pr_auc"], ascending=[True, False]).groupby("horizon").head(2)
    captum_rows = []
    for horizon in (4, 8, 12, 16):
        path = project_root / "outputs/revisao_metodologica/exact" / f"{horizon:02d}_semanas/captum/integrated_gradients_features.csv"
        top = pd.read_csv(path).head(5)
        for rank, row in enumerate(top.itertuples(index=False), start=1):
            captum_rows.append(
                {
                    "horizon": horizon,
                    "rank": rank,
                    "feature": row.feature,
                    "mean_absolute_attribution": row.mean_absolute_attribution,
                    "mean_signed_attribution": row.mean_signed_attribution,
                }
            )
    captum = pd.DataFrame(captum_rows)

    return f"""# Relatório técnico da revisão metodológica

## 1. Objetivo

O estudo avalia se informações disponíveis até a semana de emissão `t` permitem prever semanas classificadas como surto de dengue em Ribeirão Preto com 4, 8, 12 e 16 semanas de antecedência. A análise principal prevê o estado de surto exatamente em `t+h`. A análise complementar avalia a ocorrência de pelo menos uma semana de surto entre `t+1` e `t+h`.

## 2. Dados auditados

- Período: {audit['start']} a {audit['end']}.
- Observações semanais: {audit['n_rows']}.
- Colunas originais: {audit['n_columns']}.
- Datas duplicadas: {audit['duplicated_dates']}.
- Valores ausentes: {audit['missing_values']}.
- Frequência inferida: {audit['frequency']}.
- Casos semanais: mínimo {audit['case_min']:.0f}, mediana {audit['case_median']:.1f}, média {audit['case_mean']:.1f} e máximo {audit['case_max']:.0f}.

As colunas espaciais e `Trend SP` foram excluídas desta primeira análise confirmatória porque sua proveniência, população de referência e latência de publicação ainda precisam ser documentadas. A soma das colunas espaciais não coincide com o alvo municipal em nenhuma observação, impedindo tratá-las como decomposição direta de `n dengue`.

## 3. Definição temporal

Cada amostra possui uma data de emissão e uma data-alvo. Casos de dengue entram nas features com atraso mínimo de uma semana; clima da semana de emissão pode ser utilizado ao final dessa semana. O alvo da análise principal é `surto(t+h)`. O alvo complementar é o máximo de `surto(t+1)` até `surto(t+h)`.

O canal endêmico é calculado de maneira causal. Para cada semana, o percentil 75 usa somente os cinco anos anteriores, semanas epidemiológicas em uma vizinhança de ±2 e pelo menos três anos históricos. Uma semana é rotulada como surto quando os casos excedem esse limite e a média móvel de três semanas supera 110% do limite.

### 3.1 Justificativa da vizinhança epidemiológica

Uma semana epidemiológica isolada oferece no máximo uma observação por ano. A vizinhança de ±2 semanas aumenta a amostra histórica sem misturar estações distantes. A janela móvel de cinco anos permite adaptação gradual do canal endêmico. Esses parâmetros são hipóteses metodológicas e devem ser submetidos a análise de sensibilidade antes da redação final da tese.

### 3.2 Disponibilidade das entradas

Os casos entram com defasagem mínima de uma semana para representar atraso de consolidação da vigilância. Temperatura, umidade e chuva da semana `t` pressupõem emissão do alerta após o encerramento da semana. ONI, AMM e AAO foram tratados como disponíveis no período correspondente; uma versão prospectiva deverá incorporar a data real de publicação de cada índice.

## 4. Partições e prevenção de vazamento

- Treino: datas-alvo até 2021-12-26.
- Validação: datas-alvo de 2022-01-02 a 2023-12-31.
- Teste final: datas-alvo de 2024-01-07 a 2025-12-28.

Normalizadores são ajustados somente no treino. Hiperparâmetros do Random Forest são escolhidos por validação expansiva anual dentro do treino. Early stopping e limiares operacionais usam a validação. O teste final não participa dessas escolhas.

### 4.1 Composição das partições para o alvo exato

{markdown_table(exact_splits.sort_values(['horizon', 'split']), ['horizon', 'split', 'n', 'positive', 'prevalence', 'first_target_date', 'last_target_date'])}

A prevalência muda de aproximadamente 24% no treino para 67% na validação e 64% no teste. Essa mudança de regime altera precisão, calibração e valor preditivo dos modelos. Por isso, resultados altos de recall obtidos pela previsão constante da classe positiva não são suficientes para caracterizar um bom sistema de alerta.

## 5. Modelos

Foram comparados baseline sazonal, baseline de persistência com atraso de uma semana, regressão logística, Random Forest, LSTM NumPy e LSTM PyTorch. O LSTM NumPy agora possui backpropagation através do tempo para todos os pesos das quatro portas, estado recorrente e camada de saída. O LSTM PyTorch retorna logits e usa `BCEWithLogitsLoss`, peso da classe positiva, gradient clipping e early stopping.

## 6. Métricas e regra operacional

O limiar de cada modelo é selecionado na validação para obter a maior precisão possível mantendo recall mínimo de 0,80. Quando essa meta não é atingida, utiliza-se o maior F2. São reportados PR-AUC, ROC-AUC, recall, precisão, especificidade, F1, F2, Brier score e alarmes falsos por ano. Intervalos de 95% são estimados por bootstrap em blocos de oito semanas.

### 6.1 Limiar escolhido antes do teste

{markdown_table(thresholds.sort_values(['horizon', 'model_label']), ['horizon', 'model_label', 'threshold', 'validation_precision', 'validation_recall'])}

O limiar é parte do sistema preditivo. Um modelo pode ordenar corretamente o risco e ainda produzir alertas ruins quando o limiar não se transfere entre períodos com prevalências diferentes. Essa distinção explica parte dos resultados de 12 e 16 semanas.

## 7. Resultado principal no teste 2024–2025

{markdown_table(exact_test, ['horizon', 'model_label', 'prevalence', 'pr_auc', 'roc_auc', 'precision', 'recall_sensitivity', 'f2', 'false_alarms_per_year'])}

### 7.1 Interpretação por horizonte

- **4 semanas:** a regressão logística teve a maior PR-AUC (0,962) e aproximadamente 0,5 alarme falso por ano, mas seu recall no teste foi 0,731. O LSTM PyTorch alcançou recall 0,881 e PR-AUC 0,894, com cerca de 4,5 alarmes falsos por ano.
- **8 semanas:** o LSTM PyTorch apresentou a maior PR-AUC (0,927) e recall 0,896. O custo operacional foi alto: aproximadamente 16 alarmes falsos por ano.
- **12 semanas:** o LSTM PyTorch manteve boa discriminação por PR-AUC e ROC-AUC, porém o limiar transferido da validação classificou todas as semanas de teste como positivas. O recall de 1,0, isoladamente, não demonstra utilidade operacional.
- **16 semanas:** o LSTM PyTorch novamente classificou praticamente todo o teste como positivo. O Random Forest apresentou PR-AUC 0,891, precisão e recall de 0,701, constituindo a opção operacional mais equilibrada nesse horizonte entre os modelos avaliados.

### 7.2 Incerteza dos dois melhores modelos por PR-AUC

{markdown_table(best_intervals, ['horizon', 'model_label', 'pr_auc', 'pr_auc_ci', 'recall', 'recall_ci'])}

Os intervalos preservam a dependência local por blocos de oito semanas, mas continuam condicionados a um único período final de teste. Generalização geográfica e validação prospectiva exigem novas bases.

### 7.3 LSTM NumPy

O BPTT completo tornou o modelo tecnicamente treinável, mas os resultados mostram discriminação inferior ao PyTorch e instabilidade nos horizontes longos. Em vários cenários, o limiar levou à classificação de quase todas as semanas como surto. O LSTM NumPy cumpre sua função comparativa e didática; os resultados não sustentam seu uso operacional nesta configuração.

## 8. Regressão da quantidade de casos

{markdown_table(regression.sort_values('horizon'), ['horizon', 'n', 'mae', 'rmse', 'r2'])}

O R² é próximo de zero em quatro semanas e negativo nos demais horizontes. Isso significa que o Random Forest de regressão não supera de forma consistente uma referência baseada na média do teste. A transformação `log1p` reduz a influência dos picos durante o treinamento, mas não resolve a mudança de regime de 2024–2025. A regressão deve permanecer como resultado negativo documentado até que novas covariáveis ou modelos probabilísticos para contagens sejam avaliados.

## 9. Explicabilidade

O LSTM PyTorch é explicado fora da amostra com Integrated Gradients e Occlusion. O baseline do Integrated Gradients é o vetor zero no espaço padronizado, equivalente à média de treino. As atribuições são calculadas para cada feature e cada posição das 12 semanas de contexto. Elas descrevem como o modelo produziu o logit previsto e não demonstram causalidade epidemiológica.

### 9.1 Principais atribuições globais

{markdown_table(captum, ['horizon', 'rank', 'feature', 'mean_absolute_attribution', 'mean_signed_attribution'])}

Os quatro horizontes dependem principalmente dos casos recentes, do histórico de 52 semanas e do ONI. Integrated Gradients e Occlusion concordam no núcleo desse ranking. O sinal negativo médio de `log_cases_lag_52` é condicionado às demais entradas e ao baseline; ele não deve ser interpretado como efeito epidemiológico protetor.

As explicações foram calculadas nas 104 amostras de teste. Occlusion foi aplicada a 32 amostras distribuídas ao longo do período. O erro médio de convergência do Integrated Gradients ficou abaixo de `7×10⁻⁸` em todos os horizontes.

## 10. Principais correções em relação ao notebook original

| Problema original | Correção aplicada | Motivo |
|---|---|---|
| Percentil de surto calculado com toda a série | Canal endêmico causal com anos anteriores | Impedir uso do futuro na definição operacional |
| Divisão única 80/20 | Treino, validação, teste e folds anuais expansivos | Separar desenvolvimento da avaliação final |
| MinMaxScaler ajustado antes da divisão | StandardScaler ajustado somente no treino | Evitar vazamento de distribuição |
| Teste usado no early stopping | Validação exclusiva | Preservar independência do teste |
| Limiar escolhido no teste | Limiar escolhido na validação | Evitar otimização sobre o resultado final |
| LSTM NumPy atualizava somente `Wy` e `by` | BPTT completo para todos os parâmetros | Tornar a comparação tecnicamente válida |
| GridSearch retornava ROC-AUC indefinido | Folds anuais com duas classes e PR-AUC | Adequar seleção ao desbalanceamento |
| Acurácia enfatizada | PR-AUC, recall, F2 e falsos alarmes | Medir utilidade de um sistema de alerta |
| Blocos repetidos por horizonte | Funções e configuração únicas | Reduzir inconsistências e facilitar auditoria |
| Explicações por sensibilidade ad hoc | Captum Integrated Gradients e Occlusion | Padronizar a análise do LSTM PyTorch |

## 11. Limitações e ameaças à validade

O rótulo de surto é uma definição estatística construída a partir da própria série e precisa ser confrontado com a definição epidemiológica adotada no doutorado. A mudança de prevalência entre períodos indica mudança de regime e torna o teste 2024–2025 particularmente exigente. A base contém poucas centenas de semanas úteis para deep learning. Dados climáticos observados na semana de emissão pressupõem disponibilidade ao final dessa semana. A revisão ainda depende da documentação formal da origem, latência e cobertura das variáveis espaciais e de Google Trends.

A análise complementar em janela tende a produzir alta prevalência em horizontes longos quando os surtos duram muitas semanas. Por isso, seus resultados devem ser lidos como risco dentro do período e não como localização precisa do início de um evento.

### 11.1 Validade do construto

O canal endêmico causal é uma operacionalização estatística. A tese deve justificar o percentil, a largura da vizinhança epidemiológica, a janela histórica e a regra de persistência com literatura ou protocolo de vigilância. Uma análise de sensibilidade deve variar esses parâmetros e verificar se a ordenação dos modelos se mantém.

### 11.2 Validade interna

O pipeline elimina os vazamentos identificados no notebook original, mas a seleção atual de features da LSTM é pré-especificada por domínio e ainda precisa ser registrada formalmente no protocolo da pesquisa. As variáveis climáticas podem sofrer revisão após publicação; a análise prospectiva deve usar versões disponíveis na data de emissão.

### 11.3 Validade externa

Todos os dados pertencem a uma única série municipal. O desempenho não pode ser generalizado para outros municípios ou períodos sem validação externa. A epidemia de 2024–2025 constitui um regime distinto e demonstra a necessidade de monitorar drift.

### 11.4 Incerteza e multiplicidade

Foram comparados diversos modelos, horizontes e definições de alvo. A análise principal deve permanecer pré-especificada e as demais comparações devem ser apresentadas como secundárias. O bootstrap quantifica incerteza amostral no teste, mas não cobre incerteza decorrente da definição do surto, das fontes de dados ou da seleção do período.

## 12. Próximas análises necessárias para a tese

1. Validar a definição de surto com especialista e literatura epidemiológica.
2. Executar análise de sensibilidade do canal endêmico.
3. Documentar origem, cobertura e latência de todas as 73 colunas originais.
4. Avaliar calibração ou atualização de limiar em regime prospectivo sem consultar rótulos futuros.
5. Repetir LSTM PyTorch com múltiplas sementes e apresentar média e dispersão.
6. Comparar modelos probabilísticos de contagem, como Poisson e binomial negativa, para a regressão.
7. Realizar validação externa geográfica ou prospectiva antes de sugerir implantação.

## 13. Conclusão técnica

Após a correção dos vazamentos, o LSTM PyTorch continua apresentando forte capacidade de discriminar risco, sobretudo em 8 e 12 semanas. A regressão logística é superior em quatro semanas e o Random Forest oferece a operação mais equilibrada em 16 semanas. O desempenho operacional depende fortemente do limiar e da mudança de prevalência; nos horizontes longos, o LSTM produz alertas excessivos apesar da boa PR-AUC. Portanto, a evidência atual sustenta potencial preditivo, mas ainda não sustenta implantação sem calibração prospectiva e validação externa.

## 14. Reprodutibilidade

O código está em `src/dengue_research`, a execução completa em `scripts/run_revised_study.py`, as dependências em `requirements-research.txt` e os resultados em `outputs/revisao_metodologica`. O notebook original foi preservado.
"""


def generate_all_reports(project_root: Path) -> None:
    output_dir = project_root / "outputs/revisao_metodologica"
    results = load_results(output_dir / "resultados_completos.json")
    metrics = metrics_frame(results)
    splits = split_frame(results)
    metrics.to_csv(output_dir / "metricas_consolidadas.csv", index=False)
    splits.to_csv(output_dir / "particoes_temporais.csv", index=False)
    save_comparison_plots(metrics, output_dir / "figuras")
    save_prevalence_plot(splits, output_dir / "figuras")
    save_diagnostic_curves(project_root, output_dir / "figuras")
    report = build_report(results, project_root)
    report_dir = project_root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "relatorio_revisao_metodologica.md").write_text(report, encoding="utf-8")
