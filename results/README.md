# Resultados da tese — índice de consulta

## Pergunta de pesquisa

Acrescentar informações de ENSO melhora o desempenho dos modelos para antecipar
aumento dos casos de dengue, além do histórico de casos e do clima local?
Comparam-se ausência de ENSO, indicadores binários de El Niño/La Niña e ONI
contínuo (o valor decimal da anomalia). O estudo mede contribuição preditiva,
não demonstra causalidade biológica.

## Por onde começar

1. [Interpretação da comparação consolidada](comparacao_ENSO/INTERPRETACAO.md).
2. [Relatório consolidado](comparacao_ENSO/relatorio.md).
3. [Métricas dos ensembles em CSV](comparacao_ENSO/comparacao/metricas_ensemble.csv).
4. [Diferenças pareadas entre representações](comparacao_ENSO/comparacao/diferencas_ensemble.csv).
5. [Intervalos exploratórios no teste](comparacao_ENSO/comparacao/intervalos_pareados_teste.csv).
6. [Figuras da comparação](comparacao_ENSO/comparacao/figuras/).

A comparação consolidada é a análise mais abrangente: três representações de
ENSO, três arquiteturas (Random Forest, RNN e LSTM), quatro horizontes (4, 8, 12 e
16 semanas) e cinco sementes. Seu protocolo está em
[protocolo.json](comparacao_ENSO/protocolo.json). O registro de verificação já
existente foi copiado para [verificacao.json](comparacao_ENSO/verificacao.json);
a organização desta pasta não representa uma nova execução científica.

## Organização

| Pasta | Conteúdo | Papel na tese |
|---|---|---|
| `comparacao_ENSO/` | Comparação consolidada nos quatro horizontes | Análise principal do ganho incremental de ENSO |
| `v1/` | RF, RNN e LSTM sem ENSO nos quatro horizontes | Referências e resultados que alimentam o aplicativo |
| `intermediarios/experimento_sem_ONI/` | Referência sem ENSO em quatro semanas | Desenvolvimento e estabilidade |
| `intermediarios/experimento_com_ONI/` | Indicadores binários em quatro semanas | Comparação complementar de representações |
| `intermediarios/experimento_ONI_continuo/` | ONI contínuo e comparação das três representações | Análise complementar na validação |
| `intermediarios/experimento_ONI_resumido/` | RF com ONI recente ou média de 12 semanas | Sensibilidade à representação do ONI |

Cada pasta é uma cópia integral da pasta de resultados correspondente, incluindo
relatórios, tabelas, figuras, previsões, explicabilidade e modelos salvos, quando
existentes. Dentro de `v1/` e `comparacao_ENSO/`, os resultados específicos são
organizados por horizonte. O [relatório da v1](v1/relatorio_tecnico.md) e sua
[tabela de métricas](v1/comparacao/metricas_todos_modelos.csv) resumem as referências.

## Intermediários que devem permanecer fora de legacy

Esses estudos respondem à pergunta da tese e foram restaurados na raiz, com os
notebooks e os três scripts auxiliares em `models/`. Sua presença anterior em
`legacy/` resultou de um critério de arquivamento amplo demais.

As quatro análises intermediárias compartilham as mesmas 604 amostras de
treino/validação, datas, alvos e partições, conferidas a partir dos CSVs existentes.
Isso verifica comparabilidade desses elementos; não substitui uma auditoria
completa ou validação prospectiva.

Para a comparação mais recente dos intermediários, consulte:

- [Três representações: discussão](intermediarios/experimento_ONI_continuo/estabilidade_perda/comparacao_interpretacao.md).
- [Três representações: métricas](intermediarios/experimento_ONI_continuo/estabilidade_perda/comparacao_tres_representacoes.csv).
- [Sem ENSO versus binário](intermediarios/experimento_com_ONI/estabilidade_perda/comparacao_interpretacao.md).
- [ONI resumido: relatório](intermediarios/experimento_ONI_resumido/relatorio.md).

Nos intermediários, `estabilidade_perda/` usa seleção das redes pela perda BCE;
`estabilidade/` preserva a rodada anterior com seleção pelo F1. Os resultados
originais de uma semente também foram mantidos por rastreabilidade. Não trate
essas rodadas como repetições independentes nem misture seus indicadores.

A média do F1 de cinco sementes dos intermediários é diferente do F1 calculado
sobre a média das saídas de cinco modelos na comparação consolidada. Mesmo com
amostras compartilhadas, essas métricas não são intercambiáveis.

## Leitura dos resultados

A interpretação consolidada relata ganho de ENSO heterogêneo entre arquiteturas,
horizontes e períodos, sem vantagem uniforme. Os intermediários são exploratórios
na validação já usada para desenvolvimento, e o teste consolidado também já foi
examinado. Cinco sementes medem variabilidade de treinamento; não representam
cinco períodos independentes. As categorias binárias são operacionais e não
confirmam episódios oficiais de ENSO. A latência de quatro semanas do ONI é uma
hipótese, sem garantia de disponibilidade histórica em tempo real.

## Atualização e integridade

Esta pasta contém **cópias de consulta**. Os estudos continuam escrevendo nos
caminhos originais; o aplicativo continua consumindo `export/`.
Após gerar novos resultados, atualize as cópias explicitamente:

```bash
python3 scripts/collect_results.py
python3 scripts/collect_results.py --check
```

A atualização não treina modelos. `manifesto.json` registra origem, cópia, tamanho,
SHA-256 e instante da cópia. A verificação detecta mudanças nas origens, diferenças
nas cópias e arquivos extras. O coletor não apaga arquivos; se uma origem remover
um arquivo, a verificação apontará a cópia excedente para revisão.

Os caminhos citados dentro dos relatórios originais preservados referem-se às
pastas dos respectivos estudos. Use os links deste índice para navegar nas cópias.
