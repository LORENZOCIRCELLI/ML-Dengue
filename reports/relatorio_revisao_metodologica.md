# Relatório técnico da revisão metodológica

## 1. Objetivo

O estudo avalia se informações disponíveis até a semana de emissão `t` permitem prever semanas classificadas como surto de dengue em Ribeirão Preto com 4, 8, 12 e 16 semanas de antecedência. A análise principal prevê o estado de surto exatamente em `t+h`. A análise complementar avalia a ocorrência de pelo menos uma semana de surto entre `t+1` e `t+h`.

## 2. Dados auditados

- Período: 2010-12-26 a 2025-12-28.
- Observações semanais: 784.
- Colunas originais: 73.
- Datas duplicadas: 0.
- Valores ausentes: 0.
- Frequência inferida: W-SUN.
- Casos semanais: mínimo 6, mediana 126.5, média 476.8 e máximo 6013.

As colunas espaciais e `Trend SP` foram excluídas desta primeira análise confirmatória porque sua proveniência, população de referência e latência de publicação ainda precisam ser documentadas. A soma das colunas espaciais não coincide com o alvo municipal em nenhuma observação, impedindo tratá-las como decomposição direta de `n dengue`.

## 3. Definição temporal

Cada amostra possui uma data de emissão e uma data-alvo. Casos de dengue entram nas features com atraso mínimo de uma semana; clima da semana de emissão pode ser utilizado ao final dessa semana. O alvo da análise principal é `surto(t+h)`. O alvo complementar é o máximo de `surto(t+1)` até `surto(t+h)`.

O canal endêmico é calculado de maneira causal. Para cada semana, o percentil 75 usa somente os cinco anos anteriores, semanas epidemiológicas em uma vizinhança de ±2 e pelo menos três anos históricos. Uma semana é rotulada como surto quando os casos excedem esse limite e a média móvel de três semanas supera 110% do limite.

### 3.1 Justificativa da vizinhança epidemiológica

Uma semana epidemiológica isolada oferece no máximo uma observação por ano. A vizinhança de ±2 semanas aumenta a amostra histórica sem misturar estações distantes. A janela móvel de cinco anos permite adaptação gradual do canal endêmico. Esses parâmetros são hipóteses metodológicas e devem ser submetidos a análise de sensibilidade antes da redação final da tese.

### 3.2 Disponibilidade das entradas

Os casos entram com defasagem mínima de uma semana para representar atraso de consolidação da vigilância. Temperatura, umidade e chuva da semana `t` pressupõem emissão do alerta após o encerramento da semana. ONI, AMM e AAO foram tratados como disponíveis no período correspondente; uma versão prospectiva deverá incorporar a data real de publicação de cada índice.

## 4. Partições e prevenção de vazamento

- Treino: datas-alvo até 2021-12-26.
- Validação: datas-alvo de 2022-01-02 a 2023-12-31.
- Teste final: datas-alvo de 2024-01-07 a 2025-12-28.

Normalizadores são ajustados somente no treino. Hiperparâmetros do Random Forest são escolhidos por validação expansiva anual dentro do treino. Early stopping e limiares operacionais usam a validação. O teste final não participa dessas escolhas.

### 4.1 Composição das partições para o alvo exato

| horizon | split | n | positive | prevalence | first_target_date | last_target_date |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | test | 104.000 | 67.000 | 0.644 | 2024-01-07 | 2025-12-28 |
| 4 | train | 421.000 | 100.000 | 0.238 | 2013-12-08 | 2021-12-26 |
| 4 | validation | 105.000 | 70.000 | 0.667 | 2022-01-02 | 2023-12-31 |
| 8 | test | 104.000 | 67.000 | 0.644 | 2024-01-07 | 2025-12-28 |
| 8 | train | 421.000 | 100.000 | 0.238 | 2013-12-08 | 2021-12-26 |
| 8 | validation | 105.000 | 70.000 | 0.667 | 2022-01-02 | 2023-12-31 |
| 12 | test | 104.000 | 67.000 | 0.644 | 2024-01-07 | 2025-12-28 |
| 12 | train | 421.000 | 100.000 | 0.238 | 2013-12-08 | 2021-12-26 |
| 12 | validation | 105.000 | 70.000 | 0.667 | 2022-01-02 | 2023-12-31 |
| 16 | test | 104.000 | 67.000 | 0.644 | 2024-01-07 | 2025-12-28 |
| 16 | train | 421.000 | 100.000 | 0.238 | 2013-12-08 | 2021-12-26 |
| 16 | validation | 105.000 | 70.000 | 0.667 | 2022-01-02 | 2023-12-31 |

A prevalência muda de aproximadamente 24% no treino para 67% na validação e 64% no teste. Essa mudança de regime altera precisão, calibração e valor preditivo dos modelos. Por isso, resultados altos de recall obtidos pela previsão constante da classe positiva não são suficientes para caracterizar um bom sistema de alerta.

## 5. Modelos

Foram comparados baseline sazonal, baseline de persistência com atraso de uma semana, regressão logística, Random Forest, LSTM NumPy e LSTM PyTorch. O LSTM NumPy agora possui backpropagation através do tempo para todos os pesos das quatro portas, estado recorrente e camada de saída. O LSTM PyTorch retorna logits e usa `BCEWithLogitsLoss`, peso da classe positiva, gradient clipping e early stopping.

## 6. Métricas e regra operacional

O limiar de cada modelo é selecionado na validação para obter a maior precisão possível mantendo recall mínimo de 0,80. Quando essa meta não é atingida, utiliza-se o maior F2. São reportados PR-AUC, ROC-AUC, recall, precisão, especificidade, F1, F2, Brier score e alarmes falsos por ano. Intervalos de 95% são estimados por bootstrap em blocos de oito semanas.

### 6.1 Limiar escolhido antes do teste

| horizon | model_label | threshold | validation_precision | validation_recall |
| --- | --- | --- | --- | --- |
| 4 | Baseline persistência | 0.000 | 0.667 | 1.000 |
| 4 | Baseline sazonal | 0.125 | 0.670 | 0.986 |
| 4 | LSTM NumPy (BPTT) | 0.391 | 0.882 | 0.857 |
| 4 | LSTM PyTorch | 0.616 | 0.881 | 0.843 |
| 4 | Random Forest | 0.502 | 0.864 | 0.814 |
| 4 | Regressão logística | 0.038 | 0.827 | 0.886 |
| 8 | Baseline persistência | 0.000 | 0.667 | 1.000 |
| 8 | Baseline sazonal | 0.125 | 0.670 | 0.986 |
| 8 | LSTM NumPy (BPTT) | 0.422 | 0.862 | 0.800 |
| 8 | LSTM PyTorch | 0.532 | 0.812 | 0.800 |
| 8 | Random Forest | 0.274 | 0.824 | 0.800 |
| 8 | Regressão logística | 0.006 | 0.718 | 0.800 |
| 12 | Baseline persistência | 0.000 | 0.667 | 1.000 |
| 12 | Baseline sazonal | 0.125 | 0.670 | 0.986 |
| 12 | LSTM NumPy (BPTT) | 0.407 | 0.890 | 0.929 |
| 12 | LSTM PyTorch | 0.331 | 0.767 | 0.986 |
| 12 | Random Forest | 0.102 | 0.759 | 0.943 |
| 12 | Regressão logística | 0.001 | 0.681 | 0.886 |
| 16 | Baseline persistência | 0.000 | 0.667 | 1.000 |
| 16 | Baseline sazonal | 0.125 | 0.670 | 0.986 |
| 16 | LSTM NumPy (BPTT) | 0.414 | 0.848 | 0.800 |
| 16 | LSTM PyTorch | 0.351 | 0.753 | 0.914 |
| 16 | Random Forest | 0.125 | 0.764 | 0.971 |
| 16 | Regressão logística | 0.000 | 0.683 | 0.986 |

O limiar é parte do sistema preditivo. Um modelo pode ordenar corretamente o risco e ainda produzir alertas ruins quando o limiar não se transfere entre períodos com prevalências diferentes. Essa distinção explica parte dos resultados de 12 e 16 semanas.

## 7. Resultado principal no teste 2024–2025

| horizon | model_label | prevalence | pr_auc | roc_auc | precision | recall_sensitivity | f2 | false_alarms_per_year |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | Regressão logística | 0.644 | 0.962 | 0.921 | 0.980 | 0.731 | 0.770 | 0.502 |
| 4 | LSTM PyTorch | 0.644 | 0.894 | 0.802 | 0.868 | 0.881 | 0.878 | 4.515 |
| 4 | LSTM NumPy (BPTT) | 0.644 | 0.850 | 0.680 | 0.644 | 1.000 | 0.901 | 18.563 |
| 4 | Baseline persistência | 0.644 | 0.784 | 0.744 | 0.644 | 1.000 | 0.901 | 18.563 |
| 4 | Random Forest | 0.644 | 0.781 | 0.602 | 0.808 | 0.313 | 0.357 | 2.509 |
| 4 | Baseline sazonal | 0.644 | 0.626 | 0.437 | 0.647 | 0.985 | 0.892 | 18.061 |
| 8 | LSTM PyTorch | 0.644 | 0.927 | 0.841 | 0.652 | 0.896 | 0.833 | 16.055 |
| 8 | Regressão logística | 0.644 | 0.876 | 0.783 | 0.759 | 0.657 | 0.675 | 7.024 |
| 8 | LSTM NumPy (BPTT) | 0.644 | 0.800 | 0.635 | 0.644 | 1.000 | 0.901 | 18.563 |
| 8 | Baseline persistência | 0.644 | 0.751 | 0.696 | 0.644 | 1.000 | 0.901 | 18.563 |
| 8 | Random Forest | 0.644 | 0.742 | 0.542 | 0.680 | 0.254 | 0.290 | 4.014 |
| 8 | Baseline sazonal | 0.644 | 0.626 | 0.437 | 0.647 | 0.985 | 0.892 | 18.061 |
| 12 | LSTM PyTorch | 0.644 | 0.927 | 0.851 | 0.644 | 1.000 | 0.901 | 18.563 |
| 12 | Regressão logística | 0.644 | 0.917 | 0.867 | 1.000 | 0.343 | 0.395 | 0.000 |
| 12 | Random Forest | 0.644 | 0.766 | 0.575 | 0.654 | 0.761 | 0.737 | 13.546 |
| 12 | Baseline persistência | 0.644 | 0.765 | 0.717 | 0.644 | 1.000 | 0.901 | 18.563 |
| 12 | Baseline sazonal | 0.644 | 0.626 | 0.437 | 0.647 | 0.985 | 0.892 | 18.061 |
| 12 | LSTM NumPy (BPTT) | 0.644 | 0.610 | 0.507 | 0.644 | 1.000 | 0.901 | 18.563 |
| 16 | LSTM PyTorch | 0.644 | 0.901 | 0.819 | 0.644 | 1.000 | 0.901 | 18.563 |
| 16 | Random Forest | 0.644 | 0.891 | 0.766 | 0.701 | 0.701 | 0.701 | 10.034 |
| 16 | Regressão logística | 0.644 | 0.843 | 0.727 | 0.875 | 0.418 | 0.467 | 2.007 |
| 16 | Baseline persistência | 0.644 | 0.761 | 0.711 | 0.644 | 1.000 | 0.901 | 18.563 |
| 16 | LSTM NumPy (BPTT) | 0.644 | 0.650 | 0.584 | 0.640 | 0.955 | 0.870 | 18.061 |
| 16 | Baseline sazonal | 0.644 | 0.626 | 0.437 | 0.647 | 0.985 | 0.892 | 18.061 |

### 7.1 Interpretação por horizonte

- **4 semanas:** a regressão logística teve a maior PR-AUC (0,962) e aproximadamente 0,5 alarme falso por ano, mas seu recall no teste foi 0,731. O LSTM PyTorch alcançou recall 0,881 e PR-AUC 0,894, com cerca de 4,5 alarmes falsos por ano.
- **8 semanas:** o LSTM PyTorch apresentou a maior PR-AUC (0,927) e recall 0,896. O custo operacional foi alto: aproximadamente 16 alarmes falsos por ano.
- **12 semanas:** o LSTM PyTorch manteve boa discriminação por PR-AUC e ROC-AUC, porém o limiar transferido da validação classificou todas as semanas de teste como positivas. O recall de 1,0, isoladamente, não demonstra utilidade operacional.
- **16 semanas:** o LSTM PyTorch novamente classificou praticamente todo o teste como positivo. O Random Forest apresentou PR-AUC 0,891, precisão e recall de 0,701, constituindo a opção operacional mais equilibrada nesse horizonte entre os modelos avaliados.

### 7.2 Incerteza dos dois melhores modelos por PR-AUC

| horizon | model_label | pr_auc | pr_auc_ci | recall | recall_ci |
| --- | --- | --- | --- | --- | --- |
| 4 | Regressão logística | 0.962 | 0.882–0.997 | 0.731 | 0.446–0.910 |
| 4 | LSTM PyTorch | 0.894 | 0.700–0.980 | 0.881 | 0.618–1.000 |
| 8 | LSTM PyTorch | 0.927 | 0.776–0.986 | 0.896 | 0.708–1.000 |
| 8 | Regressão logística | 0.876 | 0.689–0.981 | 0.657 | 0.378–0.890 |
| 12 | LSTM PyTorch | 0.927 | 0.776–0.989 | 1.000 | 1.000–1.000 |
| 12 | Regressão logística | 0.917 | 0.804–0.996 | 0.343 | 0.076–0.538 |
| 16 | LSTM PyTorch | 0.901 | 0.711–0.981 | 1.000 | 1.000–1.000 |
| 16 | Random Forest | 0.891 | 0.637–0.977 | 0.701 | 0.379–0.888 |

Os intervalos preservam a dependência local por blocos de oito semanas, mas continuam condicionados a um único período final de teste. Generalização geográfica e validação prospectiva exigem novas bases.

### 7.3 LSTM NumPy

O BPTT completo tornou o modelo tecnicamente treinável, mas os resultados mostram discriminação inferior ao PyTorch e instabilidade nos horizontes longos. Em vários cenários, o limiar levou à classificação de quase todas as semanas como surto. O LSTM NumPy cumpre sua função comparativa e didática; os resultados não sustentam seu uso operacional nesta configuração.

## 8. Regressão da quantidade de casos

| horizon | n | mae | rmse | r2 |
| --- | --- | --- | --- | --- |
| 4 | 104.000 | 694.176 | 941.931 | 0.002 |
| 8 | 104.000 | 751.174 | 1012.912 | -0.155 |
| 12 | 104.000 | 728.854 | 964.549 | -0.047 |
| 16 | 104.000 | 786.073 | 1058.930 | -0.262 |

O R² é próximo de zero em quatro semanas e negativo nos demais horizontes. Isso significa que o Random Forest de regressão não supera de forma consistente uma referência baseada na média do teste. A transformação `log1p` reduz a influência dos picos durante o treinamento, mas não resolve a mudança de regime de 2024–2025. A regressão deve permanecer como resultado negativo documentado até que novas covariáveis ou modelos probabilísticos para contagens sejam avaliados.

## 9. Explicabilidade

O LSTM PyTorch é explicado fora da amostra com Integrated Gradients e Occlusion. O baseline do Integrated Gradients é o vetor zero no espaço padronizado, equivalente à média de treino. As atribuições são calculadas para cada feature e cada posição das 12 semanas de contexto. Elas descrevem como o modelo produziu o logit previsto e não demonstram causalidade epidemiológica.

### 9.1 Principais atribuições globais

| horizon | rank | feature | mean_absolute_attribution | mean_signed_attribution |
| --- | --- | --- | --- | --- |
| 4 | 1.000 | log_cases_lag_1 | 0.066 | 0.066 |
| 4 | 2.000 | log_cases_lag_52 | 0.063 | -0.061 |
| 4 | 3.000 | log_cases_lag_2 | 0.051 | 0.051 |
| 4 | 4.000 | log_cases_lag_4 | 0.041 | 0.041 |
| 4 | 5.000 | ONI | 0.036 | -0.001 |
| 8 | 1.000 | log_cases_lag_1 | 0.041 | 0.041 |
| 8 | 2.000 | log_cases_lag_52 | 0.039 | -0.038 |
| 8 | 3.000 | log_cases_lag_2 | 0.035 | 0.035 |
| 8 | 4.000 | log_cases_lag_4 | 0.023 | 0.023 |
| 8 | 5.000 | ONI | 0.023 | 0.003 |
| 12 | 1.000 | log_cases_lag_1 | 0.037 | 0.037 |
| 12 | 2.000 | log_cases_lag_52 | 0.036 | -0.034 |
| 12 | 3.000 | log_cases_lag_2 | 0.032 | 0.032 |
| 12 | 4.000 | ONI | 0.024 | 0.004 |
| 12 | 5.000 | log_cases_lag_4 | 0.020 | 0.020 |
| 16 | 1.000 | log_cases_lag_52 | 0.034 | -0.032 |
| 16 | 2.000 | log_cases_lag_1 | 0.033 | 0.033 |
| 16 | 3.000 | log_cases_lag_2 | 0.027 | 0.027 |
| 16 | 4.000 | ONI | 0.024 | 0.006 |
| 16 | 5.000 | log_cases_lag_4 | 0.018 | 0.018 |

Os quatro horizontes dependem principalmente dos casos recentes, do histórico de 52 semanas e do ONI. Integrated Gradients e Occlusion concordam no núcleo desse ranking. O sinal negativo médio de `log_cases_lag_52` é condicionado às demais entradas e ao baseline; ele não deve ser interpretado como efeito epidemiológico protetor.

As explicações foram calculadas nas 104 amostras de teste. Occlusion foi aplicada a 32 amostras distribuídas ao longo do período. O erro médio de convergência do Integrated Gradients ficou abaixo de `7×10⁻⁸` em todos os horizontes.

## 10. Principais correções em relação ao notebook original

| Problema original | Correção aplicada | Motivo |
|---|---|---|
| Percentil de surto calculado com toda a série | Canal endêmico causal com anos anteriores | Impedir uso do futuro na definição operacional |
| Divisão única 80/20 | Treino, validação, teste e folds anuais expansivos | Separar desenvolvimento da avaliação final |
| MinMaxScaler ajustado antes da divisão | StandardScaler ajustado somente no treino | Evitar vazamento de distribuição |
| Teste usado no early stopping | Validação exclusiva | Preservar independência do teste |
| Limiar escolhido no teste | Limiar escolhido na validação | Evitar otimização sobre o resultado final |
| LSTM NumPy atualizava somente `Wy` e `by` | BPTT completo para todos os parâmetros | Tornar a comparação tecnicamente válida |
| GridSearch retornava ROC-AUC indefinido | Folds anuais com duas classes e PR-AUC | Adequar seleção ao desbalanceamento |
| Acurácia enfatizada | PR-AUC, recall, F2 e falsos alarmes | Medir utilidade de um sistema de alerta |
| Blocos repetidos por horizonte | Funções e configuração únicas | Reduzir inconsistências e facilitar auditoria |
| Explicações por sensibilidade ad hoc | Captum Integrated Gradients e Occlusion | Padronizar a análise do LSTM PyTorch |

## 11. Limitações e ameaças à validade

O rótulo de surto é uma definição estatística construída a partir da própria série e precisa ser confrontado com a definição epidemiológica adotada no doutorado. A mudança de prevalência entre períodos indica mudança de regime e torna o teste 2024–2025 particularmente exigente. A base contém poucas centenas de semanas úteis para deep learning. Dados climáticos observados na semana de emissão pressupõem disponibilidade ao final dessa semana. A revisão ainda depende da documentação formal da origem, latência e cobertura das variáveis espaciais e de Google Trends.

A análise complementar em janela tende a produzir alta prevalência em horizontes longos quando os surtos duram muitas semanas. Por isso, seus resultados devem ser lidos como risco dentro do período e não como localização precisa do início de um evento.

### 11.1 Validade do construto

O canal endêmico causal é uma operacionalização estatística. A tese deve justificar o percentil, a largura da vizinhança epidemiológica, a janela histórica e a regra de persistência com literatura ou protocolo de vigilância. Uma análise de sensibilidade deve variar esses parâmetros e verificar se a ordenação dos modelos se mantém.

### 11.2 Validade interna

O pipeline elimina os vazamentos identificados no notebook original, mas a seleção atual de features da LSTM é pré-especificada por domínio e ainda precisa ser registrada formalmente no protocolo da pesquisa. As variáveis climáticas podem sofrer revisão após publicação; a análise prospectiva deve usar versões disponíveis na data de emissão.

### 11.3 Validade externa

Todos os dados pertencem a uma única série municipal. O desempenho não pode ser generalizado para outros municípios ou períodos sem validação externa. A epidemia de 2024–2025 constitui um regime distinto e demonstra a necessidade de monitorar drift.

### 11.4 Incerteza e multiplicidade

Foram comparados diversos modelos, horizontes e definições de alvo. A análise principal deve permanecer pré-especificada e as demais comparações devem ser apresentadas como secundárias. O bootstrap quantifica incerteza amostral no teste, mas não cobre incerteza decorrente da definição do surto, das fontes de dados ou da seleção do período.

## 12. Próximas análises necessárias para a tese

1. Validar a definição de surto com especialista e literatura epidemiológica.
2. Executar análise de sensibilidade do canal endêmico.
3. Documentar origem, cobertura e latência de todas as 73 colunas originais.
4. Avaliar calibração ou atualização de limiar em regime prospectivo sem consultar rótulos futuros.
5. Repetir LSTM PyTorch com múltiplas sementes e apresentar média e dispersão.
6. Comparar modelos probabilísticos de contagem, como Poisson e binomial negativa, para a regressão.
7. Realizar validação externa geográfica ou prospectiva antes de sugerir implantação.

## 13. Conclusão técnica

Após a correção dos vazamentos, o LSTM PyTorch continua apresentando forte capacidade de discriminar risco, sobretudo em 8 e 12 semanas. A regressão logística é superior em quatro semanas e o Random Forest oferece a operação mais equilibrada em 16 semanas. O desempenho operacional depende fortemente do limiar e da mudança de prevalência; nos horizontes longos, o LSTM produz alertas excessivos apesar da boa PR-AUC. Portanto, a evidência atual sustenta potencial preditivo, mas ainda não sustenta implantação sem calibração prospectiva e validação externa.

## 14. Reprodutibilidade

O código está em `src/dengue_research`, a execução completa em `scripts/run_revised_study.py`, as dependências em `requirements-research.txt` e os resultados em `outputs/revisao_metodologica`. O notebook original foi preservado.
