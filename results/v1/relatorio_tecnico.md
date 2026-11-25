# V1 — relatório técnico

Entradas sem ENSO, escolhidas pelo conjunto de resultados anteriores. Três famílias e horizontes de 4, 8, 12 e 16 semanas.

Cada saída é a média de cinco sementes fixas; não se escolhe uma semente pelo teste. RF selecionado por F1, redes por perda BCE de validação. Limiar fixo 0,5.

O alvo compara os casos da semana t+h à média das quatro semanas disponíveis antes de t, e não às quatro semanas imediatamente anteriores ao alvo. O critério é crescimento de casos, não confirmação epidemiológica de surto.

As fronteiras são fixas, com remoção de amostras que cruzariam as datas de desfecho entre partições; scaler ajustado somente nas janelas do treino. O número de semanas avaliadas varia entre horizontes.

O teste histórico já foi examinado em experimentos anteriores. As métricas são retrospectivas e exploratórias, não avaliação independente. As cinco sementes não substituem validação temporal externa. Não há refit após a avaliação: o ensemble da previsão é o mesmo ensemble avaliado historicamente.

A última semana da base é a referência automática da previsão. Com a hipótese de disponibilidade de uma semana, as entradas e a média de referência terminam na semana anterior. Atualizar a base atualiza essas datas, sem mudar artificialmente seu calendário.

O acerto histórico não é a probabilidade individual de acerto. Escores do modelo não foram calibrados. Dados podem sofrer atraso ou revisão; particularidades locais e mudanças de transmissão podem reduzir desempenho futuro.

SHAP e Captum explicam a média das saídas dos cinco modelos (0–1). IG usa zero padronizado, a média do treino. Atribuições não demonstram causalidade. Gini é média das importâncias de cada floresta, com DP entre sementes.

## Métricas do teste histórico

horizon_weeks,model,split,f1,precision,recall,roc_auc,pr_auc,accuracy,n_samples,n_positive,predicted_positive
4,random_forest,teste,0.73972602739726,1.0,0.58695652173913,0.930312880942706,0.88834736554509,0.875816993464052,153,46,27
4,rnn,teste,0.825,0.970588235294118,0.717391304347826,0.9315318976026,0.915763463528662,0.908496732026144,153,46,34
4,lstm,teste,0.73972602739726,1.0,0.58695652173913,0.946566436407964,0.929970292104852,0.875816993464052,153,46,27
8,random_forest,teste,0.036363636363636,1.0,0.018518518518519,0.858479532163743,0.72093757628676,0.644295302013423,149,54,1
8,rnn,teste,0.731182795698925,0.871794871794872,0.62962962962963,0.925730994152047,0.891167559708494,0.832214765100671,149,54,39
8,lstm,teste,0.620689655172414,0.818181818181818,0.5,0.90448343079922,0.834175527147523,0.778523489932886,149,54,33
12,random_forest,teste,0.347826086956522,0.923076923076923,0.214285714285714,0.922752808988764,0.858510527318316,0.689655172413793,145,56,13
12,rnn,teste,0.780952380952381,0.836734693877551,0.732142857142857,0.928170144462279,0.878094412224801,0.841379310344828,145,56,49
12,lstm,teste,0.772277227722772,0.866666666666667,0.696428571428571,0.94161316211878,0.907096869645718,0.841379310344828,145,56,45
16,random_forest,teste,0.1875,0.666666666666667,0.109090909090909,0.947357293868922,0.820304607414873,0.631205673758865,141,55,9
16,rnn,teste,0.854368932038835,0.916666666666667,0.8,0.969133192389006,0.944269669677466,0.893617021276596,141,55,48
16,lstm,teste,0.82,0.911111111111111,0.745454545454546,0.973361522198732,0.95388947971193,0.872340425531915,141,55,45
