# Legacy — experimentos e resultados descontinuados

Este diretório reúne o material científico substituído pelo fluxo atual
`v1/` + `comparacao_ENSO/` e pelos estudos complementares ENSO mantidos na raiz. O critério de arquivamento é o uso no projeto atual,
e não apenas a data ou o commit em que o arquivo apareceu.

Os experimentos antigos foram desconsiderados pelo responsável do projeto por
problemas metodológicos. Estudos intermediários e exemplos também foram
arquivados por não integrarem o fluxo atual. O simples arquivamento de um exemplo
não representa uma nova avaliação de sua correção metodológica.

Não use estes resultados para fundamentar conclusões atuais, selecionar modelos
ou alimentar o aplicativo.

## Conteúdo

- `outputs/` e `reports/`: todos os resultados e relatórios dos estudos anteriores.
- `notebooks/`: notebooks antigos, revisões intermediárias e Projeto Mestre.
- `models/`: exemplos básicos de modelos; os três auxiliares ENSO foram restaurados na raiz.
- `src/dengue_research/`: implementação do Projeto Mestre e das revisões anteriores.
- `scripts/`, `tests/` e `docs/`: executores, geradores de notebooks, testes e
  documentação exclusivos desses estudos.
- `requirements-research.txt`: dependências dos estudos arquivados.
- `static/` e `charts.json`: protótipo e definições de gráficos já arquivados.

Os caminhos relativos originais foram preservados dentro de `legacy/` e o
conteúdo dos arquivos foi mantido. O arquivo `manifesto.json` registra origem,
destino, tamanho e SHA-256 de cada arquivo. Caches Python são apenas históricos;
não são necessários à recuperação do código-fonte.

### Inventário

| Origem | Arquivos |
|---|---:|
| `charts.json` | 1 |
| `docs` | 2 |
| `models` | 278 |
| `notebooks` | 32 |
| `outputs` | 743 |
| `reports` | 4 |
| `requirements-research.txt` | 1 |
| `scripts` | 12 |
| `src` | 20 |
| `static` | 2 |
| `tests` | 4 |

Os quatro `experimento_*` e seus três auxiliares ENSO foram restaurados fora de
`legacy/` por responderem à pergunta da tese. Seus resultados estão também
no [índice central](../results/README.md). O manifesto registra os caminhos
restaurados e seus hashes, separados dos arquivos que continuam arquivados.

## Execução histórica

Este material é um arquivo histórico, não um segundo pipeline ativo. Os caminhos
internos e as dependências não foram adaptados para execução nesta pasta. Os
estudos continuam contendo referências às localizações anteriores e ao dataset
compartilhado. Para reproduzir uma versão antiga, recupere o estado completo do
Git em outra pasta; não execute os notebooks antigos sobre os resultados atuais.

## Fluxo atual preservado

| Caminho na raiz | Função |
|---|---|
| `v1/` | Estudo atual e resultados que alimentam o aplicativo |
| `comparacao_ENSO/` | Comparação consolidada atual de ONI/ENSO |
| `export/` | JSONs consumidos pelo aplicativo |
| `data/` | Bases de dados compartilhadas |
| `scripts/` | Exportação, validação e pipeline agendado atual |
| `tests/` | Testes do exportador e do pipeline atual |

O aplicativo em `mobile/` e o site em `website/` não foram modificados nesta
reorganização.

## Recuperação pelo Git

O estado anterior a toda a reorganização está registrado na tag
`checkpoint/pre-legacy-2026-11-25`, no commit `4d68f41`.

Para consultar um arquivo no caminho anterior:

```bash
git show checkpoint/pre-legacy-2026-11-25:notebooks/Notebook_Atualizado.ipynb
```

Para recuperar o estado completo em outra pasta, mantendo o projeto atual:

```bash
git worktree add ../ML-Dengue-pre-legacy -b consulta/pre-legacy checkpoint/pre-legacy-2026-11-25
```

A reorganização precisa ser registrada em um novo commit para que o Git também
preserve os novos caminhos. Os commits e a tag anteriores continuam disponíveis.
