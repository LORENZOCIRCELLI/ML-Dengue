# V1 — Random Forest, RNN e LSTM em quatro horizontes

Execute v1.ipynb na raiz do projeto ou em v1, com o ambiente Python do projeto.
Alternativa: `.venv/bin/python v1/estudo.py` na raiz.

A última semana da base define automaticamente a referência. Os alvos são as
semanas +4, +8, +12 e +16. O critério é aumento de pelo menos 50% contra a média
conhecida nas quatro semanas anteriores à emissão. Não é uma definição de surto.

Entradas sem ENSO; janela de 12 semanas; atraso de uma semana; scaler só no treino.
RF: grade 25/50/100/200 árvores, profundidade 6, folha mínima 2, maior F1 na validação.
Redes: 24 unidades, Adam 0,003, perda BCE, até 150 épocas, paciência 20 pela perda.
Cada família é a média de cinco sementes fixas. Não escolhemos uma semente vencedora.

Cada horizonte recalcula os alvos e as partições com remoção das fronteiras. O
número de semanas avaliadas pode mudar. O teste é retrospectivo e exploratório,
pois o período já foi examinado anteriormente. A previsão usa o mesmo ensemble
avaliado, sem refit posterior; atualizar a base atualiza as entradas e as datas.

## Arquivos

results/catalogo.json: índice das 12 combinações.
results/horizontes/04_semanas/random_forest (e demais combinações):

- previsao.json: sim/não, data-alvo, escore não calibrado, acerto histórico e aviso.
- metricas.json: métricas dos splits, curvas ROC e matrizes de confusão.
- explicabilidade.json: SHAP ou Saliency/IG, global e da projeção; Gini para RF.
- conclusao.json: texto pronto com acerto calculado e aviso experimental.
- resultado_completo.json: os três conjuntos acima e padrão visual.
- data, metrics, explainability: tabelas CSV e JSON.
- figures: gráficos PNG/SVG. artifacts: cinco modelos selecionados.

O scaler por horizonte e as partições estão na pasta do horizonte. EDA usa somente
o treino. Fonte DejaVu Sans; azul/laranja/verde para treino/validação/teste.
Escores 0–1, contagens em semanas, entradas em desvios padrão.

A taxa histórica não é a probabilidade de acerto individual. Atribuições explicam
o modelo, não causalidade. Avisos gerais ficam na previsão; detalhes metodológicos
em results/relatorio_tecnico.md. Nenhum aviso de idade da base é incluído na previsão.

## Verificação

Depois de executar o estudo, rode `.venv/bin/python v1/validar_resultados.py` na raiz.
O verificador recarrega os modelos, recalcula métricas e projeções, verifica
fronteiras temporais e ajuste do scaler, confere aditividade SHAP/completude IG,
mensagens, datas, CSV/JSON e o inventário. Ele não retreina modelos.

## Retrospectiva semanal

A seção 6 do notebook exporta `retrospectiva.json` por modelo/horizonte usando
somente as previsões existentes da partição de teste. Pode ser executada sem
repetir o treinamento, após a configuração de `PROJECT_ROOT`. A implementação
está em `v1/retrospectiva.py`.

Cada registro contém emissão, semana-alvo, casos observados, média de referência,
limiar de aumento, aumento previsto/observado, acerto, categoria do resultado e
escore não calibrado. As contagens e o acerto são conferidos contra as métricas
originais. Não há previsão de quantidade de casos nem mistura de treino/validação
com teste. A avaliação continua retrospectiva e exploratória.

O catálogo aponta para os 12 arquivos novos; `results/retrospectiva/resumo.json`
resume acertos e erros. A célula atualiza o inventário e a pasta `export`, agora
com 74 JSONs, sem modificar os JSONs anteriores de previsão ou métricas. A tela
de Retrospectiva do aplicativo será adaptada separadamente a esse formato binário.

## Comparação ONI/ENSO nos quatro horizontes

A seção 7 chama o experimento separado em `comparacao_ENSO/estudo.py`. Compara
sem ENSO, ONI contínuo e indicadores binários em RF, RNN e LSTM, mantendo amostras,
alvos, protocolo e sementes. A referência sem ENSO é recarregada da v1 e suas
previsões são reproduzidas. Os resultados ficam em `comparacao_ENSO/results`,
sem substituir os arquivos do aplicativo. Veja `comparacao_ENSO/INTERPRETACAO.md`
para a discussão e `comparacao_ENSO/README.md` para protocolo e limitações.
