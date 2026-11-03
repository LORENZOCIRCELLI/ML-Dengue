# Comparação de estabilidade na validação

Cinco sementes fixas; mesmas entradas de base, alvo de quatro semanas e partições. Somente os indicadores ENSO são acrescentados no segundo experimento. O teste não foi reavaliado.

Critério de seleção das redes nesta rodada: loss. Limiar fixo 0,5.

| Modelo | F1 sem ENSO (média ± DP) | F1 com ENSO (média ± DP) |
|---|---:|---:|
| Random Forest | 0.716 ± 0.014 | 0.340 ± 0.033 |
| RNN | 0.635 ± 0.014 | 0.253 ± 0.003 |
| LSTM | 0.653 ± 0.011 | 0.260 ± 0.005 |
| Tendência recente | 0.571 ± 0.000 | 0.571 ± 0.000 |

DP representa variação entre sementes no mesmo período; não é intervalo de confiança. A tendência recente é determinística e foi executada uma vez por experimento.

- Random Forest: diferença média de F1 com menos sem ENSO = -0.377; melhorou em 0 de 5 sementes.
- RNN: diferença média de F1 com menos sem ENSO = -0.382; melhorou em 0 de 5 sementes.
- LSTM: diferença média de F1 com menos sem ENSO = -0.393; melhorou em 0 de 5 sementes.

## Diagnóstico da LSTM, semente 42

- Sem ENSO: parada original na época 55, F1 da época de parada 0.611; maior F1 posterior na continuação diagnóstica 0.629. Checkpoint original preservado.
- Com ENSO: parada original na época 41, F1 da época de parada 0.245; maior F1 posterior na continuação diagnóstica 0.250. Checkpoint original preservado.

A continuação diagnóstica não substitui o checkpoint escolhido pelo critério desta rodada.

Os resultados são de desenvolvimento: a validação seleciona checkpoints e a variação entre sementes não substitui avaliação temporal em novos períodos. A evidência atual não autoriza concluir causalidade ou relevância geral de ENSO.
