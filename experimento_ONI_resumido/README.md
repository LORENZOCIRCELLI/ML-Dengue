# Random Forest — ONI resumido

Execute experimento_ONI_resumido.ipynb na raiz ou nesta pasta, com o ambiente do projeto.
Código: models/avaliar_oni_resumido.py. Mantém os resultados anteriores.

Três versões predefinidas: sem ENSO; único ONI de t−4; média de ONI de t−15 até t−4.
Mantém 72 entradas de base e acrescenta somente uma coluna por versão ONI.
São cinco sementes e a mesma grade de Random Forest, alvo de quatro semanas,
partições e limiar 0,5. Métricas principais: F1 e PR-AUC (Average Precision).
Treino/validação apenas; o teste não é reavaliado.

Resultados em results/data, metrics, figures, artifacts e json; app_resultados.json,
metadata.json, manifest.csv e relatorio.md na raiz de results. Gráficos PNG/SVG,
fonte DejaVu Sans, escores 0–1, barras de erro = DP entre sementes. ONI original e
média de ONI em °C de anomalia; entradas tratadas são padronizadas no treino.

As cinco sementes não são cinco períodos independentes. A comparação permanece
exploratória na validação já examinada; não prova causalidade ou irrelevância geral
caso não haja ganho. Nenhuma outra janela é pesquisada nesta rodada.
