# Random Forest — ONI resumido na validação

Dois resumos predefinidos; nenhum outro atraso ou janela foi testado. Mesmos atributos de base, alvo, datas e cinco sementes.

| Entrada | F1 média ± DP | PR-AUC (AP) média ± DP |
|---|---:|---:|
| Sem ENSO | 0.716 ± 0.014 | 0.768 ± 0.011 |
| ONI recente | 0.607 ± 0.028 | 0.738 ± 0.020 |
| ONI — média de 12 semanas | 0.610 ± 0.036 | 0.732 ± 0.022 |

## Comparação pareada com a referência sem ENSO

- ONI recente, F1: diferença média -0.109; melhorou em 0 de 5 sementes.
- ONI recente, PR-AUC (Average Precision): diferença média -0.030; melhorou em 1 de 5 sementes.
- ONI — média de 12 semanas, F1: diferença média -0.106; melhorou em 0 de 5 sementes.
- ONI — média de 12 semanas, PR-AUC (Average Precision): diferença média -0.036; melhorou em 1 de 5 sementes.

Os resultados são exploratórios no período de validação já examinado. As cinco sementes medem variação de treinamento, não generalização temporal; DP não é intervalo de confiança. O teste não foi reavaliado. Ausência de ganho nestas configurações não prova ausência de associação entre ENSO e dengue.
