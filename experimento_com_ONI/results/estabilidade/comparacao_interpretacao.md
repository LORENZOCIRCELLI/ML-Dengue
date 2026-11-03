# Comparação de estabilidade na validação

Cinco sementes fixas; mesmas entradas de base, alvo de quatro semanas e partições. Somente os indicadores ENSO são acrescentados no segundo experimento. O teste não foi reavaliado.

| Modelo | F1 sem ENSO (média ± DP) | F1 com ENSO (média ± DP) |
|---|---:|---:|
| Random Forest | 0.716 ± 0.014 | 0.340 ± 0.033 |
| RNN | 0.659 ± 0.023 | 0.441 ± 0.116 |
| LSTM | 0.506 ± 0.289 | 0.448 ± 0.156 |
| Tendência recente | 0.571 ± 0.000 | 0.571 ± 0.000 |

DP representa variação entre sementes no mesmo período; não é intervalo de confiança. A tendência recente é determinística e foi executada uma vez por experimento.

- Random Forest: diferença média de F1 com menos sem ENSO = -0.377; melhorou em 0 de 5 sementes.
- RNN: diferença média de F1 com menos sem ENSO = -0.217; melhorou em 0 de 5 sementes.
- LSTM: diferença média de F1 com menos sem ENSO = -0.058; melhorou em 1 de 5 sementes.

## Diagnóstico da LSTM, semente 42

- Sem ENSO: parada original na época 21, F1 da época de parada 0.000; maior F1 posterior na continuação diagnóstica 0.667. Checkpoint original preservado.
- Com ENSO: parada original na época 24, F1 da época de parada 0.255; maior F1 posterior na continuação diagnóstica 0.255. Checkpoint original preservado.

A comparação mantém o protocolo original. A continuação mostra uma possível limitação da parada por F1, mas não foi usada para substituir o modelo principal.

Os resultados são de desenvolvimento: a validação seleciona checkpoints e a variação entre sementes não substitui avaliação temporal em novos períodos. A evidência atual não autoriza concluir causalidade ou relevância geral de ENSO.
