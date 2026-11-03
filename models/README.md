# Modelos de classificação — exemplos básicos

Três notebooks independentes com o mesmo dataset Breast Cancer Wisconsin Diagnostic,
incluído no scikit-learn; nenhum dado de dengue é utilizado.

| Pasta | Notebook | Biblioteca | Explicabilidade |
|---|---|---|---|
| random_forest | random_forest.ipynb | scikit-learn | SHAP TreeExplainer |
| rnn | rnn.ipynb | PyTorch nn.RNN | Captum Saliency + Integrated Gradients |
| lstm | lstm.ipynb | PyTorch nn.LSTM | Captum Saliency + Integrated Gradients |

## Execução

Na raiz do projeto, instale `models/requirements.txt` no ambiente Python escolhido
(`.venv/bin/python -m pip install -r models/requirements.txt`). Selecione esse ambiente
como kernel e execute cada notebook do início ao fim. São aceitos os diretórios de
trabalho: raiz do projeto, models ou a própria pasta do modelo.

Os notebooks entregues já contêm resultados de uma execução completa. As versões
efetivamente utilizadas são registradas no metadata.json de cada modelo.

## Protocolo comum

- Semente 42; mesmas amostras em treino (341), validação (114) e teste (114).
- Divisão estratificada aproximada de 60% / 20% / 20%.
- Classe positiva: maligno = 1; benigno = 0 (recodifica o alvo original).
- StandardScaler ajustado exclusivamente no treino.
- Seleção pelo F1 de validação, com limiar fixo 0,5; teste não participa da seleção.
- Random Forest: 25, 50, 100 e 200 árvores. Redes: até 150 épocas,
  parada após 20 épocas sem melhora do F1 de validação; restauração do melhor estado.
- RNN e LSTM recebem um passo com 30 atributos. O dataset é tabular;
  esse formato demonstra as camadas, mas não avalia dependências temporais.

## Exportações por modelo

Cada pasta results contém data, metrics, figures, explainability e artifacts,
além de metadata.json e manifest.csv. Dados são exportados em CSV/JSON,
gráficos em PNG/SVG, scaler em joblib e modelo em joblib ou checkpoint PyTorch.
Os arquivos com os mesmos nomes são atualizados na reexecução.

Fonte DejaVu Sans; azul para treino, laranja para validação, verde para teste.
F1, ROC-AUC, acurácia, recall e probabilidades: escala 0–1; matriz de confusão:
contagem de amostras; atributos tratados: desvios padrão da média do treino.
SHAP explica probabilidade positiva; Saliency explica gradiente do logit por unidade
padronizada; Integrated Gradients explica diferença de logit em relação à média
do treino. As magnitudes desses métodos possuem unidades diferentes.

Os exemplos usam uma semente e uma divisão. Explicações descrevem o comportamento
dos modelos e não estabelecem causalidade ou validade para uso clínico.

## JSON para aplicativos e gráficos

Cada `results/app_resultados.json` reúne metadados, padrão visual, métricas,
histórico de treinamento, curvas ROC, matrizes de confusão, relatórios de
classificação, previsões por amostra e explicabilidade completa.

O campo `graficos` fornece título, tipo, eixos, cores e séries `pontos` com `x`/`y`
para reproduzir todos os gráficos exportados. Os painéis de F1, ROC-AUC, acurácia
e recall são representados por quatro gráficos individuais. Matrizes de confusão
incluem rótulos e valores; gráficos de explicabilidade preservam os 15 atributos
exibidos, enquanto `explicabilidade` mantém todos os atributos e atribuições.

Além do consolidado, cada CSV em data, metrics e explainability possui uma versão
JSON em `results/json/<pasta>/<nome>.json`, como uma lista de registros. Os
identificadores `sample_id` são preservados. O índice sem nome das matrizes passa
a se chamar `classe_real`. Ausências e valores não finitos viram `null`; escores
e probabilidades permanecem números na escala 0–1, sem arredondamento de exibição.
O JSON consolidado inclui `schemaVersion: "1.1.0"` e o inventário `tabelas`.
Essa versão adiciona `analiseDados`, gráficos de EDA e importância Gini,
preservando os campos anteriores.

A última seção de cada notebook exporta esses arquivos automaticamente. Para
converter os resultados existentes sem treinar novamente, execute na raiz:

```bash
.venv/bin/python models/export_results_json.py
```

O exportador usa apenas a biblioteca padrão Python, mantém os CSVs e imagens
existentes e atualiza o manifest.csv para incluir os novos arquivos.

## Exploração dos dados e Gini

Os três notebooks incluem, após a divisão dos dados:

- Distribuição das classes por partição, com contagens e proporções.
- Impureza Gini das classes: `1 − soma(p²)`, na escala 0–0,5 para duas classes.
- Estatísticas descritivas nas escalas original e padronizada.
- Histogramas dos 30 atributos do treino, com 20 intervalos cada.
- Boxplots dos atributos por classe no treino, preservando outliers.
- Matriz de correlação de Pearson e contagem de valores ausentes no treino.

Os gráficos dos atributos usam somente o treino. Histogramas e boxplots usam
desvios padrão (DP) da média do treino para comparar atributos de escalas distintas.
Dados ficam em `results/eda`, versões JSON em `results/json/eda`, imagens em
`results/figures` e dados consolidados em `app_resultados.json/analiseDados`.

O Random Forest também inclui importância por redução de Gini (MDI): valores
normalizados que somam 1, com desvio padrão entre árvores. Isso é diferente da
impureza das classes: mede contribuição dos atributos no modelo treinado. O
gráfico exibe os 15 maiores; CSV e JSON mantêm todos os 30. Barras de erro não
são intervalos de confiança. A MDI pode favorecer atributos com muitos valores
distintos e repartir importância entre atributos correlacionados. RNN e LSTM
mantêm Captum, pois não possuem divisões de árvores baseadas em Gini.
