# Machine Learning para Predição de Surtos de Arboviroses

Repositório oficial do projeto de doutorado de **Prof. Me. Fernando Perez**, dedicado à aplicação de técnicas de Machine Learning, Inteligência Artificial e Ciência de Dados para análise epidemiológica da dengue.

Além dos modelos preditivos, o projeto possui um aplicativo para facilitar a visualização pelos gestores da saúde e deploy do código em nuvem.

O objetivo deste repositório é centralizar toda a produção científica, técnica e acadêmica desenvolvida ao longo da pesquisa, facilitando o acesso a documentos, códigos, experimentos, conjuntos de dados e resultados obtidos durante o doutorado.

## Projeto Mestre do doutorado

O estudo principal investiga se variáveis climáticas locais e indicadores de El Niño e La Niña acrescentam capacidade de antecipar alertas de dengue em Ribeirão Preto nos horizontes de 4, 8, 12 e 16 semanas.

Artefatos principais:

* `notebooks/Notebook_Mestre_Clima_Dengue.ipynb`: explicação completa e acessível;
* `scripts/run_master_study.py`: execução reproduzível;
* `src/dengue_research/master.py`: orquestração da análise;
* `src/dengue_research/climate.py`: atributos, ENSO e associações climáticas;
* `src/dengue_research/app_exports.py`: JSONs validados para o aplicativo;
* `docs/GUIA_SIMPLES_PROJETO_MESTRE.md`: guia de leitura sem exigir conhecimento técnico;
* `docs/CONTRATO_JSON_PROJETO_MESTRE.md`: campos exportados para o aplicativo.

Execução completa:

```bash
MPLCONFIGDIR=/tmp/matplotlib-master PYTHONPATH=src ./.venv/bin/python scripts/run_master_study.py
```

Teste técnico rápido:

```bash
MPLCONFIGDIR=/tmp/matplotlib-master PYTHONPATH=src ./.venv/bin/python scripts/run_master_study.py --quick
```

---

## Resumo do Projeto

A dengue é uma das principais doenças infeocontagiosas presentes em regiões tropicais e subtropicais, impactando milhões de pessoas todos os anos.

Este projeto investiga a utilização de técnicas modernas de Machine Learning para:

* Predição de surtos epidemiológicos;
* Análise temporal e espacial de casos;
* Identificação de padrões em dados de saúde pública;
* Apoio à tomada de decisão por órgãos de saúde;
* Desenvolvimento de modelos preditivos e sistemas inteligentes.

Além disso utiliza tecnologias modernas como React Native para construção de um aplicativo moderno e AWS para deploy, para que gestores da saúde possam ter acesso rápido e multiplataforma aos resultados dos modelos preditivos.

---

## Estrutura do Repositório

```text
ML-Dengue-Global-Repository/
│
├── docs/                  # Documentação geral
├── datasets/              # Bases de dados
├── notebooks/             # Análises exploratórias
├── models/                # Modelos treinados
├── src/                   # Código-fonte principal
├── experiments/           # Experimentos realizados
├── website/               # Site oficial do projeto
├── mobile/                # Código-fonte do aplicativo
├── scripts/               # Scripts para Nuvem
└── README.md
```

---

## Navegação Rápida

### Documentação

* [Documentação Geral](./docs/)
* [Metodologia](./docs/methodology.md)
* [Cronograma](./docs/timeline.md)

### Produção Científica

* [Relatórios Técnicos](./reports/)

### Dados

* [Datasets](./datasets/)
* [Descrição das Bases](./datasets/README.md)

### Desenvolvimento

* [Código-Fonte](./src/)
* [Experimentos](./experiments/)
* [Modelos](./models/)
* [App Mobile](./mobile/)
* [Scripts](./scripts/)

### Site do Projeto

* <a href="http://buscatextual.cnpq.br/buscatextual/visualizacv.do?id=K4778105T4">Website</a>

---

## Tecnologias Utilizadas no Projeto

### Tratamento de Dados e Machine Learning
* Python
* Jupyter Notebook
* Scikit-Learn
* Pandas
* NumPy
* Matplotlib

### App Mobile

* Typescript
* React

### Deploy em Nuvem e Versionamento

* Git & GitHub
* AWS

---

## Website

O site foi desenvolvido usando React e TailwindCSS

---

## Equipe

### Pesquisador

Prof. Me. Fernando Perez

### Orientador

Prof. Dr. Rene Beleboni

### Instituição

Universidade de Ribeirão Preto

---

## Licença

Este repositório é destinado ao armazenamento e organização da produção científica do projeto de doutorado. Consulte os autores antes de reutilizar dados ou materiais protegidos por direitos autorais.
