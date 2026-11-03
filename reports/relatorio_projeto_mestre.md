# Relatório do Projeto Mestre — clima, ENSO e dengue

## Conclusão central

A série mostra diferenças descritivas entre as fases ENSO operacionais, mas o clima não apresentou ganho preditivo consistente sobre o histórico epidemiológico. O conjunto completo não venceu de forma estável entre modelos e horizontes, e a LSTM PyTorch apresentou desempenho baixo e sensível à semente. O achado deve ser relatado como associação histórica e teste de contribuição preditiva, não como causalidade.

## Pergunta principal

variáveis climáticas e ENSO acrescentam capacidade de antecipar alertas de dengue?

## Melhor conjunto por modelo e horizonte

| horizon_weeks | model | feature_set | pr_auc | prevalence | brier |
| --- | --- | --- | --- | --- | --- |
| 4 | logistic_regression | epidemiology_only | 0.339 | 0.183 | 0.133 |
| 4 | random_forest | epidemiology_only | 0.444 | 0.183 | 0.125 |
| 8 | logistic_regression | epidemiology_only | 0.375 | 0.183 | 0.145 |
| 8 | random_forest | climate_only | 0.24 | 0.183 | 0.198 |
| 12 | logistic_regression | epidemiology_only | 0.257 | 0.183 | 0.24 |
| 12 | random_forest | full | 0.216 | 0.183 | 0.179 |
| 16 | logistic_regression | full_without_enso | 0.283 | 0.183 | 0.184 |
| 16 | random_forest | climate_only | 0.23 | 0.183 | 0.173 |

A escolha acima é descritiva no teste e não autoriza selecionar retrospectivamente um novo modelo principal.

## ENSO

| horizon_weeks | enso_phase | n_weeks | mean_future_incidence | future_alert_prevalence |
| --- | --- | --- | --- | --- |
| 4 | el_nino | 194 | 129.67 | 0.17 |
| 4 | la_nina | 190 | 41.519 | 0.068 |
| 4 | neutro | 247 | 33.868 | 0.069 |
| 8 | el_nino | 194 | 129.939 | 0.17 |
| 8 | la_nina | 186 | 44.021 | 0.07 |
| 8 | neutro | 251 | 31.929 | 0.068 |
| 12 | el_nino | 194 | 125.273 | 0.17 |
| 12 | la_nina | 185 | 43.34 | 0.07 |
| 12 | neutro | 252 | 36.069 | 0.067 |
| 16 | el_nino | 194 | 120.294 | 0.186 |
| 16 | la_nina | 185 | 40.549 | 0.07 |
| 16 | neutro | 252 | 41.951 | 0.056 |

As categorias ENSO são operacionais e a diferença pode refletir sazonalidade e outros fatores.

## Associações de maior magnitude

| horizon_weeks | feature | outcome | spearman | lower_95 | upper_95 |
| --- | --- | --- | --- | --- | --- |
| 12 | media_temperatura_semana_lag_1 | incidencia_futura | 0.389 | 0.257 | 0.501 |
| 4 | media_temperatura_semana_lag_8 | incidencia_futura | 0.387 | 0.252 | 0.503 |
| 8 | media_temperatura_semana_lag_4 | incidencia_futura | 0.387 | 0.246 | 0.496 |
| 4 | media_temperatura_semana_lag_12 | incidencia_futura | 0.367 | 0.225 | 0.48 |
| 8 | media_temperatura_semana_lag_8 | incidencia_futura | 0.367 | 0.23 | 0.489 |
| 12 | media_temperatura_semana_lag_4 | incidencia_futura | 0.367 | 0.229 | 0.5 |
| 8 | media_temperatura_semana_lag_1 | incidencia_futura | 0.361 | 0.206 | 0.491 |
| 16 | media_temperatura_semana_lag_1 | incidencia_futura | 0.358 | 0.205 | 0.48 |
| 16 | media_umidade_semana_lag_12 | incidencia_futura | -0.355 | -0.458 | -0.21 |
| 4 | media_temperatura_semana_lag_4 | incidencia_futura | 0.346 | 0.203 | 0.461 |
| 8 | chuva_total_mm_lag_1 | incidencia_futura | 0.321 | 0.203 | 0.431 |
| 8 | chuva_total_mm_lag_4 | incidencia_futura | 0.319 | 0.209 | 0.42 |
| 4 | chuva_total_mm_lag_8 | incidencia_futura | 0.319 | 0.19 | 0.41 |
| 12 | chuva_total_mm_lag_1 | incidencia_futura | 0.306 | 0.172 | 0.402 |
| 4 | chuva_total_mm_lag_4 | incidencia_futura | 0.304 | 0.157 | 0.409 |
| 4 | media_umidade_semana_lag_1 | incidencia_futura | 0.298 | 0.137 | 0.416 |

Os intervalos foram obtidos por bootstrap em blocos de oito semanas. São associações descritivas.

## Estabilidade da LSTM

| horizon_weeks | pr_auc_mean | pr_auc_sd | pr_auc_min | pr_auc_max |
| --- | --- | --- | --- | --- |
| 4 | 0.18 | 0.04 | 0.135 | 0.204 |
| 8 | 0.159 | 0.033 | 0.126 | 0.193 |
| 12 | 0.129 | 0.028 | 0.111 | 0.162 |
| 16 | 0.165 | 0.041 | 0.12 | 0.199 |

Uma única execução da rede não é suficiente para sustentar conclusão de superioridade.

## Limites da conclusão

- seis episódios na série e dois no teste retrospectivo;
- uma única série municipal;
- ausência atual de validação independente com eventos oficiais;
- denominador populacional e latência das fontes ainda precisam de confirmação formal;
- 2024–2025 foi examinado durante o desenvolvimento;
- Captum explica o cálculo da LSTM e não causalidade epidemiológica.

## Exportações

Os quatro horizontes receberam `app_previsoes.json`, `app_explicabilidade_lstm.json` e `metricas_projeto_mestre.json`. O JSON legado foi preservado.
