# Interpretação da comparação consolidada

Esta discussão corresponde à execução registrada em `results/protocolo.json`, com 36 ensembles, três representações, quatro horizontes e cinco sementes por modelo. Os resultados são retrospectivos e exploratórios em Ribeirão Preto.

## Conclusão principal

**Não há um benefício uniforme de ONI/ENSO entre modelos, horizontes e períodos de avaliação. Também não é correto afirmar que os índices nunca ajudam.**

Na validação, 23 das 24 comparações variante versus ausência de ENSO pioraram tanto o F1 quanto a PR-AUC. A exceção foi RNN com ONI contínuo em 12 semanas. No teste histórico, houve 12 melhoras, um empate e 11 pioras de F1; para PR-AUC, oito melhoras e 16 pioras. São contagens descritivas de contrastes relacionados, não observações independentes ou testes de significância.

## F1 dos ensembles no teste

| Horizonte | Modelo | Sem ENSO | ONI contínuo | ENSO binário |
|---:|---|---:|---:|---:|
| 4 | Random Forest | 0,740 | 0,571 | 0,640 |
| 4 | RNN | 0,825 | 0,658 | 0,620 |
| 4 | LSTM | 0,740 | 0,500 | 0,609 |
| 8 | Random Forest | 0,036 | 0,423 | 0,578 |
| 8 | RNN | 0,731 | 0,681 | 0,660 |
| 8 | LSTM | 0,621 | 0,705 | 0,674 |
| 12 | Random Forest | 0,348 | 0,486 | 0,545 |
| 12 | RNN | 0,781 | 0,788 | 0,788 |
| 12 | LSTM | 0,772 | 0,780 | 0,772 |
| 16 | Random Forest | 0,188 | 0,553 | 0,553 |
| 16 | RNN | 0,854 | 0,843 | 0,851 |
| 16 | LSTM | 0,820 | 0,832 | 0,813 |

Todos os escores estão na escala 0–1. F1 é o indicador no limiar fixo 0,5; não é taxa de acerto ou probabilidade individual.

## Como interpretar os ganhos

Em quatro semanas, ambas as representações pioraram F1 e PR-AUC dos três modelos. Isso é compatível com os resultados anteriores para esse horizonte.

O Random Forest teve ganhos de F1 com ONI/ENSO em 8, 12 e 16 semanas, partindo de desempenho baixo da referência sem ENSO. Em oito semanas, o F1 com ENSO binário passou de 0,036 para 0,578. O intervalo exploratório pareado para a diferença foi aproximadamente [0,296; 0,792]. Já a diferença de PR-AUC foi apenas +0,037, com intervalo aproximado [−0,077; +0,223]. A melhora na decisão binária não se traduz em evidência igualmente clara de melhora da ordenação dos escores. Além disso, o F1 de validação dessa variante caiu de 0,800 para 0,353, mostrando forte dependência do período.

A LSTM melhorou o F1 em oito semanas, mas a PR-AUC caiu ligeiramente e os intervalos das diferenças incluem zero. A RNN ficou próxima da referência em 12 e 16 semanas; as pequenas vantagens de 12 semanas não têm intervalos que excluam zero.

Ganhar de uma referência fraca da mesma arquitetura não implica superar os demais modelos. Por exemplo, em oito semanas, a RNN sem ENSO mantém F1 de 0,731, acima das variantes de Random Forest. Essa observação descreve o teste; não deve ser usada para selecionar retroativamente uma configuração vencedora.

## Formulação defensável para a tese

> Nas condições avaliadas, o valor preditivo incremental de ONI/ENSO foi heterogêneo, dependente da arquitetura, do horizonte e do período de avaliação. A inclusão dos índices prejudicou o desempenho em quatro semanas e apresentou ganhos pontuais em horizontes maiores, sobretudo no Random Forest, sem evidência de vantagem uniforme entre os modelos e os períodos estudados.

Não se demonstra equivalência, ausência de efeito climático ou causalidade. Faltam vintages e datas de publicação do ONI para garantir uma reconstrução fiel da informação disponível a cada emissão. Os intervalos são exploratórios, sem correção por multiplicidade e condicionados aos modelos fixos. Uma avaliação prospectiva ou em período ainda não usado seria necessária para sustentar generalização.

O aplicativo, os JSONs publicados em `export` e as previsões operacionais da v1 foram preservados. Esta comparação não troca modelos automaticamente.
