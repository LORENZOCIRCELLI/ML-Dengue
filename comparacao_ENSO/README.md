# Comparação consolidada de ONI/ENSO

Pergunta: acrescentar ONI/ENSO melhora a previsão de aumento de casos, além dos casos recentes, temperatura, umidade, chuva e sazonalidade local?

O experimento compara **sem ENSO**, **ONI contínuo** e **ENSO binário** para Random Forest, RNN e LSTM em 4, 8, 12 e 16 semanas. São 36 ensembles, cada um com cinco sementes. As 12 referências sem ENSO são recarregadas da v1 e suas previsões são reproduzidas antes da comparação; as outras 24 combinações são treinadas.

## Executar

Na raiz do projeto:

```bash
MPLCONFIGDIR=/tmp/enso-comparacao-mpl .venv/bin/python comparacao_ENSO/estudo.py
```

Também pode ser executado pelo notebook `comparacao_ENSO.ipynb`. O mesmo experimento está acessível na seção 7 do notebook principal `v1/v1.ipynb`.

## Protocolo fixo

- Mesmo dataset processado e mesmas amostras, datas e alvos da v1, verificados por combinação.
- Alvo: casos em t+h pelo menos 50% acima da média de t−4 a t−1.
- Mesmos cortes temporais e exclusão das fronteiras entre partições.
- Janelas de 12 semanas; casos e clima local com atraso de uma semana; ONI com atraso de quatro semanas, como nos experimentos anteriores.
- ONI contínuo mantém a anomalia; indicadores binários: El Niño se ONI ≥ +0,5, La Niña se ONI ≤ −0,5; neutro quando ambos são zero. Não são episódios oficiais com critério de persistência.
- Scaler ajustado somente nas janelas do treino; as seis entradas de base são numericamente idênticas às da v1 em todas as variantes.
- Sementes 42, 123, 2025, 7 e 99; média das cinco saídas; limiar fixo 0,5.
- RF: 25/50/100/200 árvores, profundidade 6, folha mínima 2, balanceamento de classes e regra `sqrt` para atributos; seleção pelo F1 de validação, primeiro em empate.
- RNN/LSTM: uma camada de 24 unidades, Adam 0,003, até 150 épocas, paciência 20, seleção pela menor BCE de validação. Somente a dimensão de entrada aumenta para 7 ou 8 variáveis.
- Nenhuma variante é escolhida pelo teste, e não há refit após a avaliação.

O protocolo é salvo antes do treinamento. Execuções idênticas concluídas podem ser reutilizadas; mudanças no código/protocolo invalidam a reutilização.

## Resultados

`results/comparacao` contém CSV e JSON de métricas por ensemble e semente, diferenças pareadas nos três splits, estabilidade entre sementes e intervalos exploratórios de F1 e PR-AUC no teste. Os gráficos PNG/SVG usam DejaVu Sans, azul para sem ENSO, laranja para ONI contínuo e verde para ENSO binário. Escores em 0–1; diferenças na mesma escala, sem conversão indevida para porcentagens.

Cada modelo/variante/horizonte preserva checkpoints, históricos, regras selecionadas, previsões semanais, métricas, curvas ROC e matriz de confusão. Não se recalcula SHAP/Captum nesta comparação de ganho incremental. O relatório está em `results/relatorio.md` e os dados consolidados em `results/comparacao/consolidado.json`.

F1 e PR-AUC são os indicadores principais. Os intervalos usam bootstrap móvel pareado de 1.000 reamostragens em blocos de `max(12, horizonte)` semanas. Não são intervalos simultâneos, testes de equivalência ou comprovação de benefício em novos anos. A análise é condicional aos modelos já ajustados. A variabilidade entre sementes é apresentada separadamente.

## Limites

O teste já foi examinado durante o desenvolvimento. Trata-se de uma comparação retrospectiva e exploratória em um município e uma divisão temporal. ONI vem da planilha histórica, sem versões originais e datas de publicação. O atraso de quatro semanas é uma hipótese e não garante disponibilidade em tempo real ou ausência de revisões futuras do índice. Ausência de ganho não significa ausência de efeito climático, e diferenças preditivas não demonstram causalidade.

Este experimento não altera `v1/results`, `export` ou os dados do aplicativo.

## Verificação

```bash
.venv/bin/python comparacao_ENSO/validar_resultados.py
```

Recarrega os checkpoints, reconstrói as entradas e o ajuste dos scalers, confere partições/alvos e seleção pela validação, reproduz previsões e recalcula métricas. Não retreina os modelos.

Referências: [NOAA/CPC — ONI](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v5/) e [Forecasting: Principles and Practice — bootstrap por blocos](https://otexts.com/fpp3/bootstrap.html).
