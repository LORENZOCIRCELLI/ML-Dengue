# Relatório da redefinição epidemiológica e do estudo preditivo

## 1. Pergunta de pesquisa

O sistema usa somente informações disponíveis até a semana de emissão `t` para estimar: (1) o estado operacional de alerta exatamente em `t+h`; e (2) o início de um novo episódio de alerta em qualquer semana entre `t+1` e `t+h`, para horizontes de 4, 8, 12 e 16 semanas.

O termo **alerta** é deliberado. O canal endêmico, isoladamente, não comprova transmissão epidêmica nem substitui a decisão da vigilância, que também considera crescimento, gravidade, hospitalizações, óbitos, capacidade assistencial e contexto local.

## 2. Fontes metodológicas

A especificação foi ancorada no [Plano de Contingência Nacional para Dengue, Chikungunya e Zika 2025](https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/guias-e-manuais/2025/plano-de-contingencia-nacional-para-dengue-chikungunya-e-zika.pdf/@@download/file), que descreve mobilização após incidência acima da mediana e alerta após incidência acima do limite superior por quatro semanas consecutivas, e nas [diretrizes da OMS para dengue](https://tdr.who.int/docs/librariesprovider10/meeting-reports/dengue-diagnosis-pdf.pdf?download=true&sfvrsn=ef5ec264_0), que orientam canal com cinco a sete anos históricos, média semanal e limite superior próximo de dois desvios-padrão.

## 3. Dados e auditoria

- Período: 2010-12-26 a 2025-12-28.
- Observações: 784 semanas, sem datas duplicadas e com frequência W-SUN.
- Casos semanais: mínimo 6, mediana 126.5, média 476.8, máximo 6013.
- Denominador `dem`: 702739 a 711825, 2 valores, sem ausências ou valores não positivos.

O arquivo técnico existente não contém dicionário de dados. Portanto, `dem` é tratado como hipótese operacional de população residente, não como proveniência confirmada. A série muda de 711.825 para 702.739 em 2023-02-05. Antes de submissão da tese, devem ser documentados fonte, ano de referência, método de interpolação e unidade de cada coluna.

## 4. Definição epidemiológica

### 4.1 Incidência

`incidência(t) = casos(t) / dem(t) × 100.000`.

### 4.2 Canal endêmico causal

Para cada semana `t`, o histórico inclui apenas anos anteriores, até sete anos, e semanas epidemiológicas em ±2 semanas. Exigem-se pelo menos três anos. Aplica-se `log1p` à incidência; o centro geométrico é `expm1(média(log1p))` e o limite superior é `expm1(média + 1,96 × DP)`. Nenhum dado futuro entra no canal de uma semana passada.

### 4.3 Estados operacionais

- 0 — rotina: critério persistente não preenchido;
- 1 — mobilização: incidência acima da mediana, mas não acima do limite superior, por quatro semanas consecutivas;
- 2 — alerta: incidência acima do limite superior por quatro semanas consecutivas.

O alvo binário primário é `estado == 2`. O início de episódio é a transição de não-alerta para alerta. Foram identificados 6 episódios e 63 semanas em alerta.

| episode_id | start | end | duration_weeks | peak_incidence_per_100k | mean_incidence_per_100k |
| --- | --- | --- | --- | --- | --- |
| 1.000 | 2015-11-29 | 2016-02-21 | 13.000 | 844.730 | 425.666 |
| 2.000 | 2019-05-26 | 2019-07-14 | 8.000 | 149.756 | 67.555 |
| 3.000 | 2022-08-14 | 2022-11-06 | 13.000 | 33.997 | 24.974 |
| 4.000 | 2023-10-15 | 2023-12-17 | 10.000 | 50.944 | 36.842 |
| 5.000 | 2024-01-21 | 2024-01-28 | 2.000 | 243.618 | 221.206 |
| 6.000 | 2024-09-01 | 2024-12-22 | 17.000 | 110.994 | 69.350 |

## 5. Desenho temporal e prevenção de vazamento

- Treino: data-alvo até 2021-12-26.
- Validação: data-alvo de 2022-01-02 a 2023-12-31.
- Teste final: data-alvo de 2024-01-07 a 2025-12-28.
- Casos/incidência entram com atraso mínimo de uma semana.
- Escalonadores usam somente o treino.
- Random Forest usa folds anuais expansivos dentro do treino.
- Early stopping e limiares usam validação; o teste não decide parâmetros.

| horizon | split | n | positive | prevalence | first_target_date | last_target_date |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | test | 104.000 | 19.000 | 0.183 | 2024-01-07 | 2025-12-28 |
| 4 | train | 417.000 | 21.000 | 0.050 | 2014-01-05 | 2021-12-26 |
| 4 | validation | 105.000 | 23.000 | 0.219 | 2022-01-02 | 2023-12-31 |
| 8 | test | 104.000 | 19.000 | 0.183 | 2024-01-07 | 2025-12-28 |
| 8 | train | 413.000 | 21.000 | 0.051 | 2014-02-02 | 2021-12-26 |
| 8 | validation | 105.000 | 23.000 | 0.219 | 2022-01-02 | 2023-12-31 |
| 12 | test | 104.000 | 19.000 | 0.183 | 2024-01-07 | 2025-12-28 |
| 12 | train | 409.000 | 21.000 | 0.051 | 2014-03-02 | 2021-12-26 |
| 12 | validation | 105.000 | 23.000 | 0.219 | 2022-01-02 | 2023-12-31 |
| 16 | test | 104.000 | 19.000 | 0.183 | 2024-01-07 | 2025-12-28 |
| 16 | train | 405.000 | 21.000 | 0.052 | 2014-03-30 | 2021-12-26 |
| 16 | validation | 105.000 | 23.000 | 0.219 | 2022-01-02 | 2023-12-31 |

## 6. Entradas e modelos

As entradas incluem incidência defasada, transformações `log1p`, estatísticas móveis, razão entre incidência recente e limite atual, sazonalidade, clima e índices oceânico-atmosféricos. Colunas espaciais e Google Trends continuam excluídas até que proveniência, cobertura e latência sejam documentadas.

Foram comparados baseline sazonal, baseline de persistência, regressão logística, Random Forest, LSTM NumPy com BPTT completo e LSTM PyTorch. A LSTM NumPy foi preservada como comparação didática, não como candidata preferencial de implantação.

## 7. Resultado semanal do estado de alerta no teste

| horizon | model_label | prevalence | pr_auc | roc_auc | precision | recall_sensitivity | specificity | f2 | brier | false_alarms_per_year |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | Baseline persistência | 0.183 | 0.462 | 0.789 | 0.183 | 1.000 | 0.000 | 0.528 | 0.144 | 42.645 |
| 4 | LSTM NumPy (BPTT) | 0.183 | 0.342 | 0.620 | 0.258 | 0.421 | 0.729 | 0.374 | 0.280 | 11.539 |
| 4 | Random Forest | 0.183 | 0.264 | 0.681 | 0.276 | 0.421 | 0.753 | 0.381 | 0.159 | 10.536 |
| 4 | Regressão logística | 0.183 | 0.248 | 0.668 | 0.188 | 0.316 | 0.694 | 0.278 | 0.211 | 13.044 |
| 4 | Baseline sazonal | 0.183 | 0.172 | 0.454 | 0.183 | 1.000 | 0.000 | 0.528 | 0.174 | 42.645 |
| 4 | LSTM PyTorch | 0.183 | 0.135 | 0.321 | 0.175 | 0.737 | 0.224 | 0.449 | 0.280 | 33.113 |
| 8 | Baseline persistência | 0.183 | 0.289 | 0.669 | 0.183 | 1.000 | 0.000 | 0.528 | 0.240 | 42.645 |
| 8 | Regressão logística | 0.183 | 0.266 | 0.637 | 0.071 | 0.105 | 0.694 | 0.096 | 0.209 | 13.044 |
| 8 | LSTM NumPy (BPTT) | 0.183 | 0.215 | 0.551 | 0.200 | 0.474 | 0.576 | 0.372 | 0.277 | 18.061 |
| 8 | Baseline sazonal | 0.183 | 0.178 | 0.464 | 0.183 | 1.000 | 0.000 | 0.528 | 0.174 | 42.645 |
| 8 | Random Forest | 0.183 | 0.174 | 0.356 | 0.130 | 0.368 | 0.447 | 0.269 | 0.187 | 23.580 |
| 8 | LSTM PyTorch | 0.183 | 0.134 | 0.232 | 0.120 | 0.526 | 0.141 | 0.314 | 0.255 | 36.625 |
| 12 | Regressão logística | 0.183 | 0.254 | 0.601 | 0.062 | 0.105 | 0.647 | 0.093 | 0.249 | 15.051 |
| 12 | LSTM NumPy (BPTT) | 0.183 | 0.220 | 0.583 | 0.188 | 0.316 | 0.694 | 0.278 | 0.257 | 13.044 |
| 12 | Baseline persistência | 0.183 | 0.190 | 0.523 | 0.183 | 1.000 | 0.000 | 0.528 | 0.346 | 42.645 |
| 12 | Random Forest | 0.183 | 0.170 | 0.360 | 0.049 | 0.105 | 0.541 | 0.085 | 0.187 | 19.567 |
| 12 | Baseline sazonal | 0.183 | 0.170 | 0.453 | 0.183 | 1.000 | 0.000 | 0.528 | 0.174 | 42.645 |
| 12 | LSTM PyTorch | 0.183 | 0.118 | 0.155 | 0.073 | 0.316 | 0.106 | 0.190 | 0.237 | 38.130 |
| 16 | Regressão logística | 0.183 | 0.277 | 0.631 | 0.167 | 0.316 | 0.647 | 0.268 | 0.202 | 15.051 |
| 16 | LSTM NumPy (BPTT) | 0.183 | 0.209 | 0.557 | 0.197 | 0.789 | 0.282 | 0.493 | 0.252 | 30.604 |
| 16 | Baseline persistência | 0.183 | 0.183 | 0.329 | 0.183 | 1.000 | 0.000 | 0.528 | 0.462 | 42.645 |
| 16 | Random Forest | 0.183 | 0.170 | 0.432 | 0.190 | 0.632 | 0.400 | 0.432 | 0.185 | 25.587 |
| 16 | Baseline sazonal | 0.183 | 0.170 | 0.453 | 0.183 | 1.000 | 0.000 | 0.528 | 0.174 | 42.645 |
| 16 | LSTM PyTorch | 0.183 | 0.121 | 0.224 | 0.115 | 0.368 | 0.365 | 0.255 | 0.231 | 27.092 |

### 7.1 Maior PR-AUC global por horizonte

| horizon | model_label | pr_auc | precision | recall_sensitivity | false_alarms_per_year |
| --- | --- | --- | --- | --- | --- |
| 4 | Baseline persistência | 0.462 | 0.183 | 1.000 | 42.645 |
| 8 | Baseline persistência | 0.289 | 0.183 | 1.000 | 42.645 |
| 12 | Regressão logística | 0.254 | 0.062 | 0.105 | 15.051 |
| 16 | Regressão logística | 0.277 | 0.167 | 0.316 | 15.051 |

Nos horizontes de 4 e 8 semanas, o baseline de persistência aparece no topo, mas o limiar selecionado classifica todas as semanas como positivas: recall 1, especificidade 0 e aproximadamente 42,6 alarmes falsos por ano. Isso não representa utilidade operacional.

### 7.2 Melhor modelo aprendido por horizonte

| horizon | model_label | pr_auc | precision | recall_sensitivity | specificity | false_alarms_per_year |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | LSTM NumPy (BPTT) | 0.342 | 0.258 | 0.421 | 0.729 | 11.539 |
| 8 | Regressão logística | 0.266 | 0.071 | 0.105 | 0.694 | 13.044 |
| 12 | Regressão logística | 0.254 | 0.062 | 0.105 | 0.647 | 15.051 |
| 16 | Regressão logística | 0.277 | 0.167 | 0.316 | 0.647 | 15.051 |

A regressão logística é o melhor modelo aprendido em 8, 12 e 16 semanas; a LSTM NumPy lidera entre os aprendidos em 4 semanas, embora com PR-AUC baixa. Nenhum modelo demonstra desempenho suficientemente estável para implantação.

### 7.3 Resultado específico da LSTM PyTorch

| horizon | prevalence | pr_auc | roc_auc | precision | recall_sensitivity | specificity | false_alarms_per_year |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 0.183 | 0.135 | 0.321 | 0.175 | 0.737 | 0.224 | 33.113 |
| 8 | 0.183 | 0.134 | 0.232 | 0.120 | 0.526 | 0.141 | 36.625 |
| 12 | 0.183 | 0.118 | 0.155 | 0.073 | 0.316 | 0.106 | 38.130 |
| 16 | 0.183 | 0.121 | 0.224 | 0.115 | 0.368 | 0.365 | 27.092 |

A PR-AUC da LSTM PyTorch fica abaixo da prevalência do teste nos quatro horizontes. Assim, Captum continua útil para auditar o comportamento do modelo, mas não transforma um modelo mal generalizado em candidato operacional. PR-AUC é a métrica de discriminação principal por causa do desbalanceamento; recall e alarmes falsos descrevem a operação no limiar escolhido na validação.

## 8. Avaliação por início de episódio

O modelo secundário pergunta se um episódio começará nas próximas `h` semanas. Um episódio é detectado quando existe ao menos um alerta do modelo entre `início-h` e `início-1`. A métrica de antecedência usa o primeiro aviso dentro dessa janela. Há somente dois inícios no teste, portanto os valores são descritivos e possuem enorme incerteza.

| horizon | model_label | n_test_episodes | episodes_detected | episode_recall | median_maximum_lead_weeks | false_warning_weeks_per_year |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | Baseline sazonal | 2.000 | 2.000 | 1.000 | 4.000 | 48.164 |
| 4 | Baseline persistência | 2.000 | 2.000 | 1.000 | 4.000 | 48.164 |
| 4 | LSTM NumPy (BPTT) | 2.000 | 1.000 | 0.500 | 4.000 | 7.526 |
| 4 | Regressão logística | 2.000 | 1.000 | 0.500 | 4.000 | 10.034 |
| 4 | Random Forest | 2.000 | 1.000 | 0.500 | 4.000 | 20.570 |
| 4 | LSTM PyTorch | 2.000 | 1.000 | 0.500 | 4.000 | 33.614 |
| 8 | LSTM PyTorch | 2.000 | 2.000 | 1.000 | 8.000 | 30.604 |
| 8 | Baseline sazonal | 2.000 | 2.000 | 1.000 | 8.000 | 44.150 |
| 8 | Baseline persistência | 2.000 | 2.000 | 1.000 | 8.000 | 44.150 |
| 8 | Regressão logística | 2.000 | 1.000 | 0.500 | 8.000 | 10.536 |
| 8 | LSTM NumPy (BPTT) | 2.000 | 1.000 | 0.500 | 8.000 | 17.058 |
| 8 | Random Forest | 2.000 | 1.000 | 0.500 | 8.000 | 30.604 |
| 12 | LSTM PyTorch | 2.000 | 2.000 | 1.000 | 12.000 | 27.092 |
| 12 | Baseline sazonal | 2.000 | 2.000 | 1.000 | 12.000 | 40.137 |
| 12 | Baseline persistência | 2.000 | 2.000 | 1.000 | 12.000 | 40.137 |
| 12 | Regressão logística | 2.000 | 1.000 | 0.500 | 12.000 | 8.529 |
| 12 | Random Forest | 2.000 | 1.000 | 0.500 | 12.000 | 10.034 |
| 12 | LSTM NumPy (BPTT) | 2.000 | 1.000 | 0.500 | 12.000 | 15.051 |
| 16 | Regressão logística | 2.000 | 2.000 | 1.000 | 16.000 | 8.027 |
| 16 | Random Forest | 2.000 | 2.000 | 1.000 | 16.000 | 9.031 |
| 16 | LSTM NumPy (BPTT) | 2.000 | 2.000 | 1.000 | 16.000 | 21.573 |
| 16 | LSTM PyTorch | 2.000 | 2.000 | 1.000 | 16.000 | 22.075 |
| 16 | Baseline sazonal | 2.000 | 2.000 | 1.000 | 16.000 | 36.123 |
| 16 | Baseline persistência | 2.000 | 2.000 | 1.000 | 16.000 | 36.123 |

## 9. Regressão de incidência

| horizon | n | mae | rmse | r2 |
| --- | --- | --- | --- | --- |
| 4 | 104.000 | 90.553 | 121.171 | 0.184 |
| 8 | 104.000 | 84.849 | 111.029 | 0.315 |
| 12 | 104.000 | 105.284 | 141.929 | -0.119 |
| 16 | 104.000 | 118.052 | 159.149 | -0.408 |

A regressão é secundária. R² negativo significa que o modelo não supera uma referência constante no período final e deve ser reportado como resultado negativo, sem seleção retrospectiva do horizonte favorável.

## 10. Explicabilidade da LSTM PyTorch

Captum Integrated Gradients e Occlusion foram aplicados somente ao teste. O baseline zero no espaço padronizado corresponde à média do treino. As atribuições explicam a saída do modelo, não relações causais nem efeitos de intervenção.

| horizon | rank | feature | mean_absolute_attribution | mean_signed_attribution |
| --- | --- | --- | --- | --- |
| 4 | 1.000 | incidence_mean_4 | 0.011 | 0.011 |
| 4 | 2.000 | media_umidade_semana | 0.010 | -0.003 |
| 4 | 3.000 | log_incidence_lag_52 | 0.009 | -0.009 |
| 4 | 4.000 | incidence_ratio_upper_lag1 | 0.008 | 0.007 |
| 4 | 5.000 | ONI | 0.007 | 0.000 |
| 8 | 1.000 | incidence_mean_4 | 0.006 | 0.005 |
| 8 | 2.000 | media_umidade_semana | 0.005 | -0.002 |
| 8 | 3.000 | ONI | 0.004 | 0.001 |
| 8 | 4.000 | chuva_total_mm | 0.004 | -0.000 |
| 8 | 5.000 | log_incidence_lag_52 | 0.004 | -0.003 |
| 12 | 1.000 | log_incidence_lag_8 | 0.005 | -0.005 |
| 12 | 2.000 | media_umidade_semana | 0.004 | -0.001 |
| 12 | 3.000 | incidence_mean_4 | 0.004 | 0.004 |
| 12 | 4.000 | chuva_total_mm | 0.002 | 0.000 |
| 12 | 5.000 | incidence_std_12 | 0.002 | -0.001 |
| 16 | 1.000 | log_incidence_lag_8 | 0.005 | -0.005 |
| 16 | 2.000 | incidence_mean_4 | 0.003 | 0.003 |
| 16 | 3.000 | media_umidade_semana | 0.003 | -0.000 |
| 16 | 4.000 | incidence_std_12 | 0.002 | -0.002 |
| 16 | 5.000 | ONI | 0.002 | 0.001 |

## 11. Sensibilidade da definição

Foram avaliadas 24 especificações: cinco ou sete anos, raio ±1 ou ±2, limites média+1,96DP/P90/P95 e persistência de três ou quatro semanas. A concordância Jaccard com a principal variou de 0.485 a 1.000, mediana 0.569. A especificação principal produziu 63 semanas e 6 episódios.

Essa variação mostra que a incerteza do construto é material. O resultado principal deve ser acompanhado pela sensibilidade; não é aceitável escolher a definição depois de observar qual produz a melhor métrica preditiva.

## 12. O que foi modificado

| Componente | Versão anterior | Nova versão | Razão |
|---|---|---|---|
| Escala | contagem semanal | incidência por 100 mil | comparabilidade populacional |
| Canal | P75 causal | média log + 1,96DP, sete anos | alinhamento a orientação epidemiológica |
| Persistência | três semanas + média móvel | quatro semanas consecutivas | alinhamento ao plano nacional |
| Desfecho principal | surto estatístico | estado operacional de alerta | validade do construto |
| Desfecho secundário | qualquer semana positiva na janela | início de novo episódio | evita inflar o alvo por episódios longos |
| Avaliação | métricas semanais | semanais + episódios + antecedência | utilidade operacional |
| Sensibilidade | recomendada | 24 definições executadas | quantificar incerteza da definição |
| Regressão | número de casos | incidência | coerência de escala |
| Explicabilidade | Captum no LSTM | mantida com features de incidência | interpretação do modelo final |

## 13. Limitações e validade

### Validade do construto

O canal identifica um **alerta estatístico**. Sem dados de gravidade, hospitalização, óbito, sorotipo, cobertura diagnóstica e decisão oficial, não deve ser chamado de epidemia confirmada. A definição precisa de validação por epidemiologista e confronto com registros oficiais de surtos.

### Validade interna

O pipeline controla vazamento temporal conhecido, mas assume que clima da semana está disponível ao fim da semana e que índices externos têm a latência representada. Revisões tardias de casos e clima ainda não são modeladas.

### Validade externa

Há uma única série municipal. O teste 2024–2025 não substitui validação em outros municípios, validação prospectiva ou avaliação sob mudança de vigilância.

### Poder estatístico

Existem apenas seis episódios no total, dois no treino, dois na validação e dois no teste. Deep learning está em regime de amostra pequena; múltiplas sementes e incerteza entre episódios são necessárias antes de conclusões fortes.

## 14. Julgamento de defensabilidade

Esta versão é substancialmente mais defensável do que o notebook original para apresentar uma metodologia de pesquisa: o tempo está explícito, o canal é causal, o desfecho possui interpretação epidemiológica, o teste é preservado e há sensibilidade. Ela ainda não é prova suficiente para implantação clínica ou de vigilância. Para a tese, as pendências críticas são: confirmar o dicionário e as fontes; obter rótulos oficiais independentes; validar externamente; repetir sementes; e pré-registrar a especificação principal.

## 15. Reprodutibilidade

O notebook original permanece intacto. Esta especificação está em `src/dengue_research/epidemiology.py`, a execução em `scripts/run_epidemiological_study.py`, o notebook em `notebooks/Notebook_Definicao_Epidemiologica.ipynb` e os artefatos em `outputs/revisao_epidemiologica`.
