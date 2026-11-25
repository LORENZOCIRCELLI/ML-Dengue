# ONI contínuo, ENSO binário e ausência de ENSO

Validação somente, com cinco sementes fixas. Redes selecionadas pela menor perda BCE; RF pelo maior F1. Limiar 0,5, mesmo alvo de quatro semanas, mesmas datas e entradas de base. ONI contínuo e indicadores binários têm atraso de quatro semanas.

| Modelo | Sem ENSO — F1 média ± DP | ENSO binário — F1 média ± DP | ONI contínuo — F1 média ± DP |
|---|---:|---:|---:|
| Random Forest | 0.716 ± 0.014 | 0.340 ± 0.033 | 0.270 ± 0.032 |
| RNN | 0.635 ± 0.014 | 0.253 ± 0.003 | 0.354 ± 0.107 |
| LSTM | 0.653 ± 0.011 | 0.260 ± 0.005 | 0.272 ± 0.003 |
| Tendência recente | 0.571 ± 0.000 | 0.571 ± 0.000 | 0.571 ± 0.000 |

A tendência recente é determinística (uma execução). DP de cinco sementes não é intervalo de confiança nem variação em novos anos. A validação seleciona checkpoints e já orientou mudanças anteriores: esta comparação é exploratória e não confirma generalização ou causalidade. Nenhum ajuste foi escolhido pelo teste, e o teste não foi reavaliado nesta rodada.
