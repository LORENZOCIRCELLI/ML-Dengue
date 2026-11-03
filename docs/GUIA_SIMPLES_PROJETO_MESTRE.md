# Guia simples do Projeto Mestre

## O objetivo em uma frase

Descobrir se clima, El Niño e La Niña ajudam a antecipar alertas de dengue em Ribeirão Preto com 4, 8, 12 e 16 semanas de antecedência.

## O que acontece quando o projeto é executado

1. O arquivo semanal é carregado.
2. Datas repetidas, semanas ausentes e valores inválidos são procurados.
3. Os casos são divididos pela população para produzir incidência por 100 mil habitantes.
4. Um canal endêmico é calculado usando somente anos anteriores.
5. Semanas de rotina, mobilização e alerta são identificadas.
6. Casos anteriores, sazonalidade, clima local e índices globais são preparados.
7. Modelos com e sem clima são comparados.
8. As previsões de 4, 8, 12 e 16 semanas são avaliadas.
9. A LSTM é explicada com Captum.
10. Os resultados são exportados para JSON.

## O que significa “causal” no código

Quando o código usa a palavra `causal`, ele quer dizer apenas que o futuro não foi usado para calcular o passado. Não significa que o projeto provou que o clima causou dengue.

## Qual é a definição principal de alerta

A definição principal usa incidência e canal endêmico. Um alerta exige quatro semanas consecutivas acima do limite superior do canal.

Essa é uma definição construída para a pesquisa. Até ser comparada com registros oficiais, ela deve ser chamada de “alerta epidemiológico pelo canal endêmico”, e não de epidemia oficialmente confirmada.

## Por que o P75 continua existindo

O P75 é mantido no Projeto 1 como comparação. Ele permite verificar se as conclusões mudam quando “surto” é definido de outra maneira.

## Como o projeto mede o valor do clima

Os mesmos modelos são executados com cinco conjuntos de informação:

| Conjunto | Informações utilizadas |
|---|---|
| `seasonal_only` | época do ano e tendência |
| `epidemiology_only` | época do ano e histórico da dengue |
| `climate_only` | época do ano e clima |
| `full_without_enso` | dengue e clima, sem ONI |
| `full` | dengue, clima local, ONI e outros índices |

Se o conjunto completo superar de forma consistente o conjunto epidemiológico, existe evidência de ganho preditivo do clima. Se não superar, o resultado deve ser mantido.

## Como El Niño e La Niña entram

ONI entra no modelo como número contínuo. Para gráficos, o projeto usa uma classificação operacional:

- ONI a partir de `+0,5`: El Niño;
- ONI até `-0,5`: La Niña;
- demais valores: neutro.

Essa categoria é descritiva e não substitui a classificação oficial de episódios. ONI entra com quatro semanas de atraso por prudência até que sua latência real seja documentada.

## Por que clima local entra atrasado

Temperatura, chuva e umidade da própria semana podem ainda não estar completas quando a previsão é emitida. O Projeto Mestre usa pelo menos uma semana de atraso.

## Modelos utilizados

- referência sazonal;
- referência de persistência;
- regressão logística;
- Random Forest;
- LSTM NumPy, como comparação didática;
- LSTM PyTorch, como rede recorrente principal.

O projeto não pressupõe que a LSTM será melhor.

## O que o Captum explica

O Captum mostra quais entradas deslocaram a previsão da LSTM em relação a uma referência média. Ele pode mostrar importância de variáveis e de semanas anteriores.

Ele não prova que uma variável causou o alerta.

## O que é exportado para o aplicativo

Em cada pasta de horizonte, o projeto cria:

```text
dados/app_previsoes.json
dados/app_explicabilidade_lstm.json
metricas/metricas_projeto_mestre.json
figuras/captum_importancia_variaveis.png
figuras/captum_importancia_temporal.png
```

O arquivo existente `app_dados_dengue.json` não é modificado.

## Como executar

No diretório principal do projeto:

```bash
MPLCONFIGDIR=/tmp/matplotlib-master \
PYTHONPATH=src \
./.venv/bin/python scripts/run_master_study.py
```

Para verificar rapidamente a integração:

```bash
MPLCONFIGDIR=/tmp/matplotlib-master \
PYTHONPATH=src \
./.venv/bin/python scripts/run_master_study.py --quick
```

Para executar os testes:

```bash
MPLCONFIGDIR=/tmp/matplotlib-master \
PYTHONPATH=src \
./.venv/bin/python -m unittest discover -s tests -v
```

## Onde ficam os resultados científicos

```text
outputs/projeto_mestre/
```

## Onde ficam os arquivos consumíveis pelo aplicativo

```text
outputs/horizontes/04_semanas/
outputs/horizontes/08_semanas/
outputs/horizontes/12_semanas/
outputs/horizontes/16_semanas/
```

## O que pode ser afirmado

- houve ou não associação entre determinadas informações climáticas e alertas futuros;
- acrescentar clima melhorou ou não a previsão;
- o ganho variou ou não entre horizontes;
- a LSTM utilizou determinadas entradas para calcular suas previsões;
- os resultados foram observados em Ribeirão Preto no período estudado.

## O que não pode ser afirmado

- El Niño causou sozinho um surto;
- Captum identificou causas epidemiológicas;
- o sistema funciona em qualquer município;
- o aplicativo valida cientificamente o modelo;
- os resultados atuais autorizam uso em decisões de saúde pública.

## Pendências que não devem ser escondidas

1. Confirmar formalmente a origem da coluna `dem`.
2. Documentar a fonte e a latência de cada variável climática.
3. Comparar o alerta construído com registros oficiais.
4. Reservar um período futuro ou outro município para validação independente.
5. Manter previsões futuras arquivadas antes de conhecer os resultados.

