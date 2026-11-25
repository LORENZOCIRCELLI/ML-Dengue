# Comparação entre as duas definições de desfecho

## Leitura correta da comparação

As duas versões não diferem apenas em código: elas medem construtos distintos. A versão anterior usa contagens e um P75 causal com persistência de três semanas. A versão epidemiológica usa incidência por 100 mil, limite superior em escala logarítmica e quatro semanas consecutivas. Assim, diferenças de desempenho não devem ser interpretadas como uma competição direta entre modelos sobre o mesmo problema.

## Concordância dos rótulos semanais

- Semanas válidas comparadas: 630.
- Concordância bruta: 0.724.
- Jaccard entre semanas positivas: 0.266.
- Positivos na definição anterior: 237; positivos na nova definição: 63.

## Melhor PR-AUC por horizonte em cada definição

| definition | horizon | model_label | prevalence | pr_auc | precision | recall_sensitivity | false_alarms_per_year |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Incidência/canal oficial-alinhado | 4 | Baseline persistência | 0.183 | 0.462 | 0.183 | 1.000 | 42.645 |
| P75 causal anterior | 4 | Regressão logística | 0.644 | 0.962 | 0.980 | 0.731 | 0.502 |
| Incidência/canal oficial-alinhado | 8 | Baseline persistência | 0.183 | 0.289 | 0.183 | 1.000 | 42.645 |
| P75 causal anterior | 8 | LSTM PyTorch | 0.644 | 0.927 | 0.652 | 0.896 | 16.055 |
| Incidência/canal oficial-alinhado | 12 | Regressão logística | 0.183 | 0.254 | 0.062 | 0.105 | 15.051 |
| P75 causal anterior | 12 | LSTM PyTorch | 0.644 | 0.927 | 0.644 | 1.000 | 18.563 |
| Incidência/canal oficial-alinhado | 16 | Regressão logística | 0.183 | 0.277 | 0.167 | 0.316 | 15.051 |
| P75 causal anterior | 16 | LSTM PyTorch | 0.644 | 0.901 | 0.644 | 1.000 | 18.563 |

## Conclusão comparativa

A especificação epidemiológica é mais defensável como desfecho primário porque normaliza por população, separa estado de alerta de início de episódio e ancora os parâmetros em orientações sanitárias. A versão P75 permanece útil como análise de sensibilidade histórica. Métricas de uma versão não validam a outra, e a estabilidade da conclusão deve ser julgada pela concordância da ordenação dos modelos, pelas curvas fora da amostra e pelo desempenho por episódio.
