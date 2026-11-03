# ONI contínuo — validação controlada

Execute experimento_ONI_continuo.ipynb na raiz do projeto ou nesta pasta, com o
ambiente Python do projeto. Esta versão preserva os experimentos sem ENSO e com
ENSO binário. Não reavalia o teste.

Mesmos alvos e datas congelados, horizonte quatro semanas, 12 semanas de entrada,
ONI com atraso de quatro semanas, cinco sementes e limiar 0,5. Redes selecionam
menor perda BCE; RF seleciona maior F1. Nenhum ajuste adicional é feito.

A preparação reconstrói os seis atributos de base e acrescenta ONI contínuo,
verificando que os atributos de base padronizados coincidem com os anteriores.
O scaler usa somente o treino. Somente treino e validação são exportados.

Código comum: models/comparar_representacoes_enso.py e models/avaliar_estabilidade.py.
Resultados em results/estabilidade_perda: CSV, JSON, gráficos PNG/SVG, checkpoints,
diagnóstico separado da LSTM e relatório comparacao_interpretacao.md. Dados de
entrada em results/data e nas subpastas de cada arquitetura. JSON consolidado
em results/app_resultados.json; versões individuais em results/json.

Métricas 0–1, média ± DP entre sementes. DP não é intervalo de confiança e não
mede generalização em novos anos. A validação também seleciona checkpoints;
a análise é exploratória. PR-AUC usa Average Precision. Cores azul, laranja e
verde para sem ENSO, ENSO binário e ONI contínuo; fonte DejaVu Sans.
