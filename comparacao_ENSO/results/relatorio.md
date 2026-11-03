# Comparação consolidada ONI/ENSO

Três variantes, três modelos e quatro horizontes. Mesmas amostras, alvos, datas, sementes, padronização no treino, regras de seleção e limiar 0,5. A base sem ENSO é a v1 original, com checkpoints recarregados e previsões reproduzidas antes da comparação.

F1 e PR-AUC (Average Precision) são os indicadores principais definidos no protocolo. Não se escolhe uma variante ou configuração pelo teste. Não há refit.

## Horizonte de 4 semanas — teste histórico

| Modelo | Variante | F1 | PR-AUC | Recall | Acurácia |
|---|---|---:|---:|---:|---:|
| Random Forest | Sem ENSO | 0.740 | 0.888 | 0.587 | 0.876 |
| Random Forest | ONI contínuo | 0.571 | 0.730 | 0.435 | 0.804 |
| Random Forest | ENSO binário | 0.640 | 0.738 | 0.522 | 0.824 |
| RNN | Sem ENSO | 0.825 | 0.916 | 0.717 | 0.908 |
| RNN | ONI contínuo | 0.658 | 0.840 | 0.543 | 0.830 |
| RNN | ENSO binário | 0.620 | 0.746 | 0.478 | 0.824 |
| LSTM | Sem ENSO | 0.740 | 0.930 | 0.587 | 0.876 |
| LSTM | ONI contínuo | 0.500 | 0.773 | 0.348 | 0.791 |
| LSTM | ENSO binário | 0.609 | 0.752 | 0.457 | 0.824 |

## Horizonte de 8 semanas — teste histórico

| Modelo | Variante | F1 | PR-AUC | Recall | Acurácia |
|---|---|---:|---:|---:|---:|
| Random Forest | Sem ENSO | 0.036 | 0.721 | 0.019 | 0.644 |
| Random Forest | ONI contínuo | 0.423 | 0.746 | 0.278 | 0.725 |
| Random Forest | ENSO binário | 0.578 | 0.758 | 0.481 | 0.745 |
| RNN | Sem ENSO | 0.731 | 0.891 | 0.630 | 0.832 |
| RNN | ONI contínuo | 0.681 | 0.858 | 0.574 | 0.805 |
| RNN | ENSO binário | 0.660 | 0.815 | 0.574 | 0.785 |
| LSTM | Sem ENSO | 0.621 | 0.834 | 0.500 | 0.779 |
| LSTM | ONI contínuo | 0.705 | 0.829 | 0.574 | 0.826 |
| LSTM | ENSO binário | 0.674 | 0.823 | 0.537 | 0.812 |

## Horizonte de 12 semanas — teste histórico

| Modelo | Variante | F1 | PR-AUC | Recall | Acurácia |
|---|---|---:|---:|---:|---:|
| Random Forest | Sem ENSO | 0.348 | 0.859 | 0.214 | 0.690 |
| Random Forest | ONI contínuo | 0.486 | 0.867 | 0.321 | 0.738 |
| Random Forest | ENSO binário | 0.545 | 0.871 | 0.375 | 0.759 |
| RNN | Sem ENSO | 0.781 | 0.878 | 0.732 | 0.841 |
| RNN | ONI contínuo | 0.788 | 0.895 | 0.732 | 0.848 |
| RNN | ENSO binário | 0.788 | 0.897 | 0.732 | 0.848 |
| LSTM | Sem ENSO | 0.772 | 0.907 | 0.696 | 0.841 |
| LSTM | ONI contínuo | 0.780 | 0.907 | 0.696 | 0.848 |
| LSTM | ENSO binário | 0.772 | 0.902 | 0.696 | 0.841 |

## Horizonte de 16 semanas — teste histórico

| Modelo | Variante | F1 | PR-AUC | Recall | Acurácia |
|---|---|---:|---:|---:|---:|
| Random Forest | Sem ENSO | 0.188 | 0.820 | 0.109 | 0.631 |
| Random Forest | ONI contínuo | 0.553 | 0.915 | 0.382 | 0.759 |
| Random Forest | ENSO binário | 0.553 | 0.905 | 0.382 | 0.759 |
| RNN | Sem ENSO | 0.854 | 0.944 | 0.800 | 0.894 |
| RNN | ONI contínuo | 0.843 | 0.937 | 0.782 | 0.887 |
| RNN | ENSO binário | 0.851 | 0.941 | 0.782 | 0.894 |
| LSTM | Sem ENSO | 0.820 | 0.954 | 0.745 | 0.872 |
| LSTM | ONI contínuo | 0.832 | 0.921 | 0.764 | 0.879 |
| LSTM | ENSO binário | 0.812 | 0.923 | 0.709 | 0.872 |

## Diferenças pareadas e incerteza

As diferenças são variante menos sem ENSO. O bootstrap móvel pareado usa as mesmas semanas nas variantes e 1.000 reamostragens, em blocos de max(12, horizonte) semanas. Reamostras sem ambas as classes são excluídas, com contagem registrada. Os intervalos são percentis de 95%, condicionados aos modelos ajustados. Não são testes de equivalência nem intervalos simultâneos para todos os contrastes.

| Horizonte | Modelo | Variante | Métrica | Δ | Intervalo exploratório 95% |
|---:|---|---|---|---:|---|
| 4 | Random Forest | ONI contínuo | f1 | -0.168 | [-0.444; +0.063] |
| 4 | Random Forest | ONI contínuo | pr_auc | -0.158 | [-0.375; +0.041] |
| 4 | Random Forest | ENSO binário | f1 | -0.100 | [-0.382; +0.229] |
| 4 | Random Forest | ENSO binário | pr_auc | -0.150 | [-0.364; +0.046] |
| 4 | RNN | ONI contínuo | f1 | -0.167 | [-0.333; +0.059] |
| 4 | RNN | ONI contínuo | pr_auc | -0.076 | [-0.200; +0.006] |
| 4 | RNN | ENSO binário | f1 | -0.205 | [-0.423; +0.079] |
| 4 | RNN | ENSO binário | pr_auc | -0.170 | [-0.374; -0.006] |
| 4 | LSTM | ONI contínuo | f1 | -0.240 | [-0.710; +0.156] |
| 4 | LSTM | ONI contínuo | pr_auc | -0.157 | [-0.362; -0.013] |
| 4 | LSTM | ENSO binário | f1 | -0.131 | [-0.353; +0.172] |
| 4 | LSTM | ENSO binário | pr_auc | -0.178 | [-0.389; -0.014] |
| 8 | Random Forest | ONI contínuo | f1 | +0.386 | [+0.000; +0.706] |
| 8 | Random Forest | ONI contínuo | pr_auc | +0.025 | [-0.115; +0.227] |
| 8 | Random Forest | ENSO binário | f1 | +0.541 | [+0.296; +0.792] |
| 8 | Random Forest | ENSO binário | pr_auc | +0.037 | [-0.077; +0.223] |
| 8 | RNN | ONI contínuo | f1 | -0.050 | [-0.125; +0.079] |
| 8 | RNN | ONI contínuo | pr_auc | -0.033 | [-0.104; +0.032] |
| 8 | RNN | ENSO binário | f1 | -0.072 | [-0.145; +0.067] |
| 8 | RNN | ENSO binário | pr_auc | -0.076 | [-0.178; +0.007] |
| 8 | LSTM | ONI contínuo | f1 | +0.084 | [-0.050; +0.299] |
| 8 | LSTM | ONI contínuo | pr_auc | -0.005 | [-0.137; +0.063] |
| 8 | LSTM | ENSO binário | f1 | +0.054 | [-0.052; +0.246] |
| 8 | LSTM | ENSO binário | pr_auc | -0.011 | [-0.142; +0.063] |
| 12 | Random Forest | ONI contínuo | f1 | +0.139 | [-0.151; +0.289] |
| 12 | Random Forest | ONI contínuo | pr_auc | +0.009 | [-0.105; +0.086] |
| 12 | Random Forest | ENSO binário | f1 | +0.198 | [+0.054; +0.332] |
| 12 | Random Forest | ENSO binário | pr_auc | +0.012 | [-0.106; +0.100] |
| 12 | RNN | ONI contínuo | f1 | +0.008 | [-0.061; +0.121] |
| 12 | RNN | ONI contínuo | pr_auc | +0.016 | [-0.041; +0.072] |
| 12 | RNN | ENSO binário | f1 | +0.008 | [-0.036; +0.121] |
| 12 | RNN | ENSO binário | pr_auc | +0.019 | [-0.064; +0.079] |
| 12 | LSTM | ONI contínuo | f1 | +0.008 | [-0.073; +0.161] |
| 12 | LSTM | ONI contínuo | pr_auc | -0.000 | [-0.069; +0.053] |
| 12 | LSTM | ENSO binário | f1 | +0.000 | [-0.032; +0.103] |
| 12 | LSTM | ENSO binário | pr_auc | -0.005 | [-0.076; +0.053] |
| 16 | Random Forest | ONI contínuo | f1 | +0.365 | [-0.087; +0.624] |
| 16 | Random Forest | ONI contínuo | pr_auc | +0.095 | [-0.098; +0.143] |
| 16 | Random Forest | ENSO binário | f1 | +0.365 | [-0.078; +0.628] |
| 16 | Random Forest | ENSO binário | pr_auc | +0.085 | [-0.068; +0.131] |
| 16 | RNN | ONI contínuo | f1 | -0.011 | [-0.072; +0.073] |
| 16 | RNN | ONI contínuo | pr_auc | -0.007 | [-0.049; +0.016] |
| 16 | RNN | ENSO binário | f1 | -0.003 | [-0.057; +0.095] |
| 16 | RNN | ENSO binário | pr_auc | -0.003 | [-0.066; +0.037] |
| 16 | LSTM | ONI contínuo | f1 | +0.012 | [-0.059; +0.092] |
| 16 | LSTM | ONI contínuo | pr_auc | -0.033 | [-0.114; +0.003] |
| 16 | LSTM | ENSO binário | f1 | -0.007 | [-0.120; +0.089] |
| 16 | LSTM | ENSO binário | pr_auc | -0.030 | [-0.108; +0.015] |

## Limitações e interpretação

- Um município e uma divisão temporal; teste já examinado no desenvolvimento.
- Resultados retrospectivos e exploratórios; não validação prospectiva independente.
- Ausência de ganho consistente não demonstra equivalência nem ausência de efeito climático.
- ONI histórico da planilha, sem vintages ou datas originais de publicação; atraso de quatro semanas é hipótese.
- ONI usa médias trimestrais e pode sofrer revisões; atraso fixo não garante ausência de informação revisada.
- Indicadores por limiares semanais não identificam episódios ENSO oficiais com persistência.
- Intervalos percentis por blocos são exploratórios, condicionados aos modelos fixos, sem correção por multiplicidade.
- Blocos preservam dependência local, mas não asseguram estacionariedade ou independência entre epidemias.
- DP entre cinco sementes mede instabilidade de treinamento, não incerteza em novos anos.
- Mais entradas mudam a contagem de parâmetros das redes e o número implícito de atributos do RF com sqrt.
- A análise mede ganho condicional às variáveis locais, não efeito causal total de ENSO sobre dengue.

Não se deve concluir antecipadamente que ONI/ENSO ajuda ou não ajuda. Diferenças devem ser descritas por modelo, horizonte, validação/teste e estabilidade entre sementes. Mesmo um intervalo que inclui zero não prova ausência de benefício.

## Referências metodológicas

- NOAA/CPC — definição e revisões do ONI: https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v5/
- Hyndman e Athanasopoulos — bootstrap por blocos em séries temporais: https://otexts.com/fpp3/bootstrap.html
