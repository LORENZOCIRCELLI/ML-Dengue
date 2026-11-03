# experimento_sem_ONI

Execute `experimento_sem_ONI.ipynb` do início ao fim usando o ambiente Python do projeto.
O diretório de execução pode ser esta pasta ou a raiz. Dependências em requirements.txt.

## Pergunta e alvo inicial

ONI melhora a previsão de aumento de pelo menos 50% nos casos daqui a quatro semanas,
em comparação à média das quatro últimas semanas conhecidas? Esse é um proxy de
crescimento de risco, não uma confirmação epidemiológica de surto.

ONI excluído; demais entradas, datas e configurações iguais ao outro experimento.
Dados: data/dataset/processado/base_modelagem_dengue_dataset.xlsx.
Casos, temperatura, umidade, chuva e sazonalidade; atraso de uma semana, e quatro para ONI.
São hipóteses de disponibilidade, sujeitas a revisão com documentação da fonte.

## Procedimento

Divisão cronológica aproximada 60/20/20 com remoção de amostras que cruzariam
fronteiras de desfecho; StandardScaler somente no treino; janelas reais de 12 semanas.
Random Forest, RNN e LSTM recebem a mesma janela de informação. Seleção por F1 na
validação, com limiar fixo 0,5. Uma semente (42); teste não escolhe configurações.

Todas as fases estão no mesmo notebook: bibliotecas, DataFrame, tratamento,
EDA, arquiteturas, treinamento, validação, teste, SHAP/Gini e Captum
(Saliency/Integrated Gradients), comparação e exportação.

## Resultados

results/data e results/eda: dados compartilhados. results/figures: EDA e comparação.
results/random_forest, results/rnn e results/lstm: dados tratados, previsões, métricas,
gráficos PNG/SVG, explicabilidade, scaler e modelo. results/json: versão de cada CSV.
results/app_resultados.json: tabelas, metadados, gráficos e relatórios consolidados.
results/manifest.csv: inventário. A reexecução atualiza os mesmos arquivos.

Fonte DejaVu Sans; azul/laranja/verde para treino/validação/teste. Escores 0–1;
casos por semana; temperatura °C; umidade %; chuva mm/semana; atributos tratados em
desvios padrão. Explicabilidade: SHAP em probabilidade, Saliency em gradiente do logit,
Integrated Gradients em logit, importância Gini normalizada. As atribuições se referem
à classe de aumento de casos e não estabelecem causalidade.

Este primeiro experimento é exploratório: um município, uma divisão e uma semente.
Nenhum código dos notebooks antigos de dengue é importado.

## Estabilidade na validação

A seção 10 repete Random Forest, RNN e LSTM nas sementes 42, 123, 2025, 7 e 99.
Mantém os atributos, o alvo, as partições e o treinamento original. Não reavalia
o teste nem escolhe a melhor semente. Média e DP são de cinco execuções no mesmo
período, não intervalos de confiança ou validação em períodos independentes.

Inclui uma referência determinística de tendência recente. PR-AUC é Average
Precision; a validação tem a mesma prevalência para todos os modelos. A LSTM da
semente 42 continua até 150 épocas somente para diagnóstico: seu checkpoint
original é preservado na comparação principal.

Arquivos em results/estabilidade: métricas por semente, resumo, previsões de
validação, histórico, diagnóstico, modelos selecionados, gráficos PNG/SVG,
app_estabilidade.json e relatório. Versões JSON das tabelas em results/json/estabilidade.
A comparação entre experimentos fica em experimento_com_ONI/results/estabilidade.

O código comum é models/avaliar_estabilidade.py. A seção pode ser executada
isoladamente após a execução inicial dos dois experimentos.

## Seleção das redes pela perda de validação

A seção 11 executa a rodada atual: RNN e LSTM selecionam a menor perda BCE de
validação, com paciência 20. Somente esse critério muda. Limiar 0,5, cinco sementes,
entradas, alvo, partições e demais hiperparâmetros são mantidos. RF e referência
simples mantêm seus critérios. O teste não é reavaliado.

Resultados separados em results/estabilidade_perda; a rodada por F1 fica preservada
em results/estabilidade. Há comparação entre critérios, modelos e experimentos,
com CSV, JSON, gráficos e checkpoints. A validação continua sendo desenvolvimento.

Execução das duas rodadas atuais, na raiz:
`.venv/bin/python models/avaliar_estabilidade.py --network-selection loss`.
