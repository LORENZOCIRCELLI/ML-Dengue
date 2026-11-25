# Machine Learning para Predição de Surtos de Arboviroses

Repositório do projeto de doutorado de **Prof. Me. Fernando Perez**, dedicado à
aplicação de Machine Learning e Ciência de Dados à análise da dengue em Ribeirão
Preto. O aplicativo AlphaDengue permite consultar as previsões e os resultados.

## Estudo atual

O estudo em [`v1/`](./v1/README.md) compara Random Forest, RNN e LSTM nos horizontes
de **4, 8, 12 e 16 semanas**. O alvo é o aumento de pelo menos 50% dos casos da
semana-alvo em relação à média das quatro semanas anteriores à emissão. Esse
critério de crescimento não representa confirmação epidemiológica de surto.

Cada modelo combina cinco sementes fixas. As partições são cronológicas, com
remoção de amostras nas fronteiras. O desempenho é retrospectivo e exploratório;
o teste histórico já foi examinado durante o desenvolvimento.

A comparação em [`comparacao_ENSO/`](./comparacao_ENSO/README.md) avalia o valor
incremental de ONI contínuo e ENSO binário nas mesmas arquiteturas e horizontes.
Seus resultados permanecem separados dos JSONs do aplicativo.

Os estudos intermediários `experimento_sem_ONI/`, `experimento_com_ONI/`,
`experimento_ONI_continuo/` e `experimento_ONI_resumido/` complementam a resposta
à pergunta da tese e permanecem fora de `legacy/`.

**Para consultar os resultados, comece pelo [índice central em results/](./results/README.md).**

## Organização atual

| Caminho | Conteúdo |
|---|---|
| [`v1/`](./v1/README.md) | Estudo atual, notebook, modelos e resultados |
| [`comparacao_ENSO/`](./comparacao_ENSO/README.md) | Comparação consolidada ONI/ENSO |
| [`results/`](./results/README.md) | Cópias organizadas dos resultados principais e complementares |
| `experimento_*/` | Estudos complementares de representação e estabilidade de ENSO |
| `models/` | Código auxiliar dos estudos ENSO intermediários |
| `data/` | Dataset bruto e processado compartilhado |
| `export/` | Catálogo e JSONs publicados para o aplicativo |
| [`mobile/`](./mobile/README.md) | Aplicativo AlphaDengue em React Native/Expo |
| `website/` | Site em React/Vite |
| `scripts/` | Pipeline atual, exportador e validador de JSONs |
| `tests/` | Testes do exportador e do pipeline atual |
| `docs/` | Documentação geral e execução na AWS |
| [`legacy/`](./legacy/README.md) | Experimentos, código e resultados descontinuados |

## Execução

Com as dependências de `v1/requirements.txt` instaladas no ambiente Python:

```bash
.venv/bin/python v1/estudo.py
.venv/bin/python comparacao_ENSO/estudo.py
.venv/bin/python scripts/export_app_json.py
```

A exportação copia os JSONs de `v1/results/` para `export/` e atualiza o índice de
imports locais do aplicativo. Ela não treina modelos.

O pipeline completo, incluindo as retrospectivas, pode ser executado com
`./Script_Run.sh`. A publicação é uma
etapa separada, com `./upload_to_s3.sh`. Configuração, logs, bloqueio de concorrência
e agendamento estão em [`docs/AWS_AGENDAMENTO.md`](./docs/AWS_AGENDAMENTO.md).
O pipeline usa o dataset local; não atualiza a base em serviços externos.

## Verificação

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_app_export.py export
```

Para as verificações científicas, após a execução dos estudos:

```bash
.venv/bin/python v1/validar_resultados.py
.venv/bin/python comparacao_ENSO/validar_resultados.py
```

Os comandos do aplicativo estão em [`mobile/README.md`](./mobile/README.md).

Para atualizar e verificar as cópias de consulta:

```bash
python3 scripts/collect_results.py
python3 scripts/collect_results.py --check
```

## Experimentos descontinuados

Todo o material científico substituído pelo fluxo atual foi reunido em
[`legacy/`](./legacy/README.md), incluindo `outputs/`, `reports/`, notebooks,
modelos de exemplo, Projeto Mestre e seus
scripts e testes. Os conteúdos foram preservados com inventário e hashes em
[`legacy/manifesto.json`](./legacy/manifesto.json).

Os resultados antigos desconsiderados por problemas metodológicos não devem
orientar as conclusões atuais nem os dados exibidos pelo aplicativo.

O estado anterior à reorganização pode ser recuperado pela tag
`checkpoint/pre-legacy-2026-11-25` (commit `4d68f41`). O procedimento está no
[guia do arquivo histórico](./legacy/README.md).

## Equipe

- **Pesquisador:** Prof. Me. Fernando Perez.
- **Orientador:** Prof. Dr. Rene Beleboni.
- **Instituição:** Universidade de Ribeirão Preto.

## Licença

Este repositório centraliza a produção científica do projeto de doutorado.
Consulte os autores antes de reutilizar dados ou materiais protegidos por direitos
autorais.
