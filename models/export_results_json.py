"""Exporta os resultados existentes, sem treinar modelos ou modificar os CSVs."""

from pathlib import Path
import csv
import json
import math


SPLIT_LABELS = {"treino": "Treino", "validacao": "Validação", "teste": "Teste"}
METRIC_LABELS = {"f1": "F1", "roc_auc": "ROC-AUC", "accuracy": "Acurácia", "recall": "Recall"}
MODEL_LABELS = {"random_forest": "Random Forest", "rnn": "RNN", "lstm": "LSTM"}


def parse_value(value):
    """Preserva textos; representa valores ausentes/não finitos como JSON null."""
    if value is None or value.strip().lower() in {"", "nan", "inf", "-inf", "infinity", "-infinity"}:
        return None
    try:
        return int(value)
    except ValueError:
        try:
            number = float(value)
            return number if math.isfinite(number) else None
        except ValueError:
            return value


def read_table(path):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        # pandas exporta o índice das matrizes sem nome no cabeçalho.
        return [{key or "classe_real": parse_value(value) for key, value in row.items()}
                for row in reader]


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8")


def export_model(results):
    results = Path(results).resolve()
    metadata = json.loads((results / "metadata.json").read_text(encoding="utf-8"))
    model_key = metadata["model"]
    model_title = MODEL_LABELS[model_key]
    tables = {}
    paths = []
    for group in ["data", "metrics", "explainability", "eda"]:
        for source in sorted((results / group).glob("*.csv")):
            key = f"{group}/{source.stem}"
            tables[key] = read_table(source)
            destination = results / "json" / group / f"{source.stem}.json"
            write_json(destination, tables[key])
            paths.append(destination)

    def table(group, name):
        return tables[f"{group}/{name}"]

    graphs = []

    def add_graph(graph_id, title, kind, x_label, y_label, series, **extra):
        graphs.append({"id": graph_id, "titulo": title, "tipo": kind,
                       "eixoX": x_label, "eixoY": y_label, "series": series, **extra})

    history = table("metrics", "historico_treinamento")
    metrics = table("metrics", "metricas_finais")
    roc = table("metrics", "curvas_roc")
    step_label = "Número de árvores (contagem)" if model_key == "random_forest" else "Época (contagem)"
    for metric, label in METRIC_LABELS.items():
        series = [{"id": split, "titulo": SPLIT_LABELS[split],
                   "cor": metadata["colors"][split],
                   "pontos": [{"x": row["step"], "y": row[metric]}
                              for row in history if row["split"] == split]}
                  for split in ["treino", "validacao"]]
        add_graph(f"01_historico_metricas/{metric}", f"{model_title} — {label}",
                  "linha", step_label, "Escore (0–1)", series,
                  passoSelecionado=metadata["selected_step"], dominioY=[0, 1.03])
        add_graph(f"02_metricas_finais/{metric}", f"{model_title} — {label}", "barras",
                  "Partição", "Escore (0–1)",
                  [{"id": row["split"], "titulo": SPLIT_LABELS[row["split"]],
                    "cor": metadata["colors"][row["split"]],
                    "pontos": [{"x": SPLIT_LABELS[row["split"]], "y": row[metric]}]}
                   for row in metrics], dominioY=[0, 1.14])

    add_graph("03_curvas_roc", f"{model_title} — curvas ROC", "linha",
              "Taxa de falsos positivos (0–1)", "Recall / taxa de verdadeiros positivos (0–1)",
              [{"id": split, "titulo": SPLIT_LABELS[split],
                "cor": metadata["colors"][split],
                "auc": next(row["roc_auc"] for row in metrics if row["split"] == split),
                "pontos": [{"x": row["false_positive_rate"], "y": row["true_positive_rate"],
                            "limiar": row["threshold"]} for row in roc if row["split"] == split]}
               for split in SPLIT_LABELS],
              referencia={"titulo": "Referência aleatória", "cor": "#64748B",
                          "pontos": [{"x": 0, "y": 0}, {"x": 1, "y": 1}]},
              dominioX=[0, 1], dominioY=[0, 1.02])

    confusion = {split: table("metrics", f"matriz_confusao_{split}") for split in SPLIT_LABELS}
    cm = confusion["teste"]
    add_graph("04_matriz_confusao_teste", f"{model_title} — matriz de confusão no teste",
              "mapa_calor", "Classe prevista", "Classe real", [],
              rotulosX=["Benigno", "Maligno"], rotulosY=["Benigno", "Maligno"],
              valores=[[row["previsto_benigno"], row["previsto_maligno"]] for row in cm],
              unidade="Amostras (contagem)", mapaCores="Blues")

    explanations = {}
    methods = ["shap"] if model_key == "random_forest" else ["saliency", "integrated_gradients"]
    for method in methods:
        importance = table("explainability", f"{method}_importancia")
        unit = {"shap": "probabilidade: 0–1", "saliency": "logit por unidade padronizada",
                "integrated_gradients": "logit"}[method]
        explanations[method] = {"unidade": unit, "classeExplicada": "maligno",
            "importancia": importance,
            "atribuicoes": table("explainability", f"{method}_atribuicoes")}
        if method == "shap":
            explanations[method]["aditividade"] = table("explainability", "shap_aditividade")
        if method == "integrated_gradients":
            explanations[method]["baseline"] = "Vetor zero padronizado: média do treino"
            explanations[method]["convergencia"] = table("explainability", "integrated_gradients_convergencia")
        add_graph(f"05_{method}_importancia",
                  f'{model_title} — {method.replace("_", " ").title()} — teste',
                  "barras_horizontais", f"Média da atribuição absoluta ({unit})",
                  "Atributo padronizado",
                  [{"id": method, "titulo": method.replace("_", " ").title(),
                    "cor": metadata["colors"][method],
                    "pontos": [{"x": row["mean_absolute_attribution"], "y": row["feature"]}
                               for row in importance[:15][::-1]]}],
                  limiteAtributos=15, ordenacao="15 maiores, menor para maior")

    # Os campos antigos permanecem; EDA e importância Gini são extensões opcionais.
    eda = {key.split("/", 1)[1]: rows for key, rows in tables.items() if key.startswith("eda/")}
    if eda:
        class_rows = eda["distribuicao_classes"]
        add_graph("00_eda_distribuicao_classes", f"{model_title} — distribuição das classes",
                  "barras_agrupadas", "Partição", "Amostras (contagem)",
                  [{"id": key, "titulo": label, "cor": metadata["colors"][key],
                    "pontos": [{"x": SPLIT_LABELS[row["split"]], "y": row["count"],
                                "proporcao": row["proportion"]}
                               for row in class_rows if row["class_id"] == cls]}
                   for cls, key, label in [(0, "benigno", "Benigno"), (1, "maligno", "Maligno")]])
        add_graph("00_eda_gini_classes", f"{model_title} — impureza Gini das classes",
                  "barras", "Partição", "Impureza Gini (0–0,5)",
                  [{"id": row["split"], "titulo": SPLIT_LABELS[row["split"]],
                    "cor": metadata["colors"][row["split"]],
                    "pontos": [{"x": SPLIT_LABELS[row["split"]], "y": row["gini_impurity"]}]}
                   for row in eda["gini_classes"]], dominioY=[0, 0.55])
        add_graph("00_eda_valores_ausentes", f"{model_title} — valores ausentes no treino",
                  "barras_horizontais", "Valores ausentes (contagem)", "Atributo",
                  [{"id": "dados", "titulo": "Treino", "cor": metadata["colors"]["dados"],
                    "pontos": [{"x": row["missing_count"], "y": row["feature"]}
                               for row in eda["valores_ausentes_treino"][::-1]]}])
        for feature in metadata["features"]:
            bins = [row for row in eda["histogramas_treino"] if row["feature"] == feature]
            add_graph(f"00_eda_histogramas_treino/{feature}",
                      f"{model_title} — treino — {feature}", "histograma",
                      "Valor padronizado (DP)", "Amostras (contagem)",
                      [{"id": "dados", "titulo": "Treino", "cor": metadata["colors"]["dados"],
                        "pontos": [{"x": row["bin_center"], "y": row["count"],
                                    "limiteInferior": row["bin_left"], "limiteSuperior": row["bin_right"],
                                    "largura": row["bin_width"]} for row in bins]}])
        for cls, key, label in [(0, "benigno", "Benigno"), (1, "maligno", "Maligno")]:
            add_graph(f"00_eda_boxplots_treino/{key}", f"{model_title} — treino — {label}",
                      "boxplot_horizontal", "Valor padronizado (DP)", "Atributo", [],
                      cor=metadata["colors"][key],
                      estatisticas=[row for row in eda["boxplots_treino"] if row["class_id"] == cls],
                      outliers=[row for row in eda["boxplots_outliers_treino"] if row["class_id"] == cls],
                      regraLimites="1,5 IQR; outliers preservados")
        correlations = {(row["feature_y"], row["feature_x"]): row["correlation"]
                        for row in eda["correlacoes_treino"]}
        add_graph("00_eda_correlacoes_treino", f"{model_title} — correlação de Pearson no treino",
                  "mapa_calor", "Atributo", "Atributo", [],
                  rotulosX=metadata["features"], rotulosY=metadata["features"],
                  valores=[[correlations[(y, x)] for x in metadata["features"]] for y in metadata["features"]],
                  mapaCores="RdBu_r", minimo=-1, maximo=1, unidade="Correlação de Pearson (−1 a 1)")

    if "explainability/gini_importancia" in tables:
        gini = table("explainability", "gini_importancia")
        explanations["gini"] = {"metodo": "MDI — redução ponderada da impureza Gini",
            "particao": "treino", "unidade": "importância normalizada (0–1)",
            "importancia": gini, "barrasErro": "DP entre árvores; não é intervalo de confiança"}
        add_graph("06_gini_importancia", f"{model_title} — importância por redução de Gini — treino",
                  "barras_horizontais", "Importância normalizada (0–1); barras: DP entre árvores",
                  "Atributo", [{"id": "gini", "titulo": "Gini (MDI)", "cor": metadata["colors"]["gini"],
                    "pontos": [{"x": row["importance"], "y": row["feature"],
                                "erroX": row["std_across_trees"]} for row in gini[:15][::-1]]}],
                  limiteAtributos=15)

    report = json.loads((results / "metrics/relatorios_classificacao.json").read_text(encoding="utf-8"))
    payload = {"schemaVersion": "1.1.0", "modelo": model_key, "titulo": model_title,
        "metadados": metadata,
        "estilo": {"fonte": metadata["font"], "cores": metadata["colors"],
                   "rotulosParticoes": SPLIT_LABELS, "rotulosMetricas": METRIC_LABELS},
        "metricas": metrics, "historicoTreinamento": history, "curvasRoc": roc,
        "matrizesConfusao": confusion, "relatoriosClassificacao": report,
        "previsoes": {split: table("data", f"previsoes_{split}") for split in SPLIT_LABELS},
        "explicabilidade": explanations, "analiseDados": eda, "graficos": graphs,
        "tabelas": [{"origem": key + ".csv", "json": "json/" + key + ".json",
                     "registros": len(rows)} for key, rows in tables.items()]}
    destination = results / "app_resultados.json"
    write_json(destination, payload)
    paths.append(destination)

    files = [{"path": str(path.relative_to(results)), "bytes": path.stat().st_size}
             for path in sorted(results.rglob("*")) if path.is_file() and path.name != "manifest.csv"]
    with (results / "manifest.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "bytes"])
        writer.writeheader()
        writer.writerows(files)
    return paths


if __name__ == "__main__":
    for model in MODEL_LABELS:
        exported = export_model(Path(__file__).resolve().parent / model / "results")
        print(f"{model}: {len(exported)} arquivos JSON exportados")
