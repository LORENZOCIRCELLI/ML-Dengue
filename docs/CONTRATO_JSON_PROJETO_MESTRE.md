# Contrato dos JSONs do Projeto Mestre

## Regra de compatibilidade

`app_dados_dengue.json` permanece inalterado. O Projeto Mestre acrescenta arquivos; não remove campos existentes.

## `app_previsoes.json`

Campos principais:

| Campo | Significado |
|---|---|
| `schemaVersion` | versão do formato |
| `generatedAt` | data e hora da geração em UTC |
| `horizonteSemanas` | 4, 8, 12 ou 16 |
| `modelo` | modelo responsável pela previsão atual |
| `versaoModelo` | versão rastreável do modelo |
| `previsaoAtual` | previsão emitida na última semana disponível |
| `previsoesAtuais` | previsão atual de todos os modelos comparados |
| `linhaTempoPrevisoes` | previsões retrospectivas do teste |
| `statusCientifico` | limites de uso do resultado |

`modeloSelecionado` é escolhido pela maior PR AUC na validação, sem consultar o teste. `nivelRisco` é uma categoria relativa ao limiar validado, não uma categoria clínica oficial.

## `app_explicabilidade_lstm.json`

Campos principais:

| Campo | Gráfico possível |
|---|---|
| `explicacaoAtual.importanciaVariaveis` | barras por variável |
| `explicacaoAtual.importanciaTemporal` | barras ou linha por semana anterior |
| `explicacaoAtual.mapaCalor` | mapa semana × variável |
| `explicacaoGlobalTeste.importanciaVariaveis` | importância média no teste |
| `explicacaoGlobalTeste.importanciaTemporal` | importância temporal média |

`direcao` pode assumir `aumentou`, `reduziu` ou `neutro`. Ela descreve o deslocamento do logit da LSTM em relação ao baseline.

## `metricas_projeto_mestre.json`

Contém métricas, limiares, partições e intervalos de incerteza do experimento completo daquele horizonte.

## Regras técnicas

- datas em ISO 8601;
- números não finitos são exportados como `null`;
- `NaN` e `Infinity` são proibidos;
- escrita atômica evita publicar arquivo parcialmente escrito;
- toda previsão contém data de emissão e data-alvo;
- modelo e explicação usam a mesma versão;
- arquivos de modelos não precisam ser públicos no S3.
