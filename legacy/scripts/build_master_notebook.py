#!/usr/bin/env python3
"""Constrói o notebook explicativo do Projeto Mestre."""

from pathlib import Path
import nbformat as nbf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "notebooks/Notebook_Mestre_Clima_Dengue.ipynb"


def markdown(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


cells = [
    markdown(
        """
# Projeto Mestre — clima, ENSO e previsão de alertas de dengue

## O que este projeto procura descobrir

O objetivo principal é verificar se informações climáticas locais e indicadores de El Niño e La Niña ajudam a antecipar alertas de dengue em Ribeirão Preto com **4, 8, 12 e 16 semanas** de antecedência.

O notebook separa três perguntas:

1. clima e dengue aparecem relacionados nos dados históricos?
2. acrescentar clima melhora previsões feitas somente com casos anteriores e época do ano?
3. quais informações a LSTM utilizou para produzir cada previsão?

As análises medem associação e contribuição preditiva. Elas não demonstram que uma variável climática, isoladamente, causou um surto.
"""
    ),
    markdown(
        """
## Decisões principais tomadas antes da análise final

- definição principal: alerta pelo canal endêmico causal em incidência por 100 mil habitantes;
- análise de sensibilidade: P75 causal preservado no Projeto 1;
- clima local disponível com atraso mínimo de uma semana;
- ONI e demais índices globais disponíveis com atraso conservador de quatro semanas;
- treino por data-alvo até 2021, validação em 2022–2023 e avaliação retrospectiva em 2024–2025;
- PR AUC como medida principal de discriminação, sempre apresentada junto à prevalência;
- comparação obrigatória entre sazonalidade, epidemiologia, clima, modelo sem ENSO e modelo completo;
- resultados negativos são preservados;
- Captum explica o comportamento da LSTM, não causalidade epidemiológica.
"""
    ),
    code(
        """
from pathlib import Path
import json
import subprocess
import sys
import pandas as pd
from IPython.display import display, Image, Markdown

cwd = Path.cwd().resolve()
PROJECT_ROOT = cwd if (cwd / 'src/dengue_research').exists() else cwd.parent
OUTPUT_DIR = PROJECT_ROOT / 'outputs/projeto_mestre'
REEXECUTE = False  # True treina todos os modelos novamente; pode demorar.

if REEXECUTE or not (OUTPUT_DIR / 'resultados_completos.json').exists():
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / 'scripts/run_master_study.py')],
        cwd=PROJECT_ROOT,
        check=True,
    )

results = json.loads((OUTPUT_DIR / 'resultados_completos.json').read_text(encoding='utf-8'))
associations = pd.read_csv(OUTPUT_DIR / 'associacoes_climaticas.csv')
enso = pd.read_csv(OUTPUT_DIR / 'resumo_enso.csv')
ablation = pd.read_csv(OUTPUT_DIR / 'comparacao_com_sem_clima.csv')
stability = pd.read_csv(OUTPUT_DIR / 'estabilidade_lstm_sementes.csv')
episodes = pd.read_csv(OUTPUT_DIR / 'episodios_alerta.csv')
print('Projeto:', PROJECT_ROOT)
print('Resultados:', OUTPUT_DIR)
"""
    ),
    markdown(
        """
## 1. Qualidade e origem dos dados

Esta seção verifica datas, ausências, duplicações e valores impossíveis. O denominador `dem` é usado provisoriamente como população residente, mas sua fonte e a alteração observada em 2023 ainda precisam de confirmação documental. Isso é uma pendência científica explícita, não uma informação escondida.
"""
    ),
    code(
        """
display(pd.Series(results['data_audit'], name='valor').to_frame())
display(pd.Series(results['population_audit'], name='valor').to_frame())
"""
    ),
    markdown(
        """
## 2. O que é considerado alerta

O canal endêmico compara a incidência semanal com o histórico da mesma época em anos anteriores. Somente semanas anteriores são utilizadas. Um alerta exige quatro semanas consecutivas acima do limite superior.

O termo correto é **alerta epidemiológico construído pelo canal**. Ele não equivale sozinho a uma declaração oficial de epidemia.
"""
    ),
    code("display(episodes)"),
    markdown(
        """
## 3. Como El Niño e La Niña são representados

A coluna ONI é utilizada como informação contínua nos modelos. Para gráficos descritivos, valores a partir de `+0,5` são chamados de El Niño, valores até `-0,5` de La Niña e os demais de neutros. Essa classificação é operacional e precisa ser confrontada com a fonte oficial antes da redação final.

Nos modelos, ONI aparece com pelo menos quatro semanas de atraso. Assim, uma previsão não utiliza um índice que ainda não estaria disponível na data de emissão.
"""
    ),
    code("display(enso.round(3))"),
    markdown(
        """
## 4. Relações climáticas observadas

As correlações abaixo usam blocos de oito semanas para representar a dependência entre semanas próximas. Elas ajudam a descrever a relação temporal, mas não provam causa e efeito.
"""
    ),
    code(
        """
display(
    associations.sort_values('spearman', key=lambda s: s.abs(), ascending=False)
    .head(30)
    .round(3)
)
"""
    ),
    markdown(
        """
## 5. A comparação central da tese

São comparados cinco conjuntos de informação:

- `seasonal_only`: somente época do ano e tendência;
- `epidemiology_only`: sazonalidade e histórico da dengue;
- `climate_only`: sazonalidade e variáveis climáticas;
- `full_without_enso`: casos e clima, mas sem ONI;
- `full`: casos, clima local, ONI e outros índices.

O clima será considerado preditivamente útil apenas se melhorar resultados fora do treino de forma consistente. Um resultado inferior também deve ser mantido e discutido.
"""
    ),
    code(
        """
columns = ['horizon_weeks','feature_set','model','prevalence','pr_auc','brier','precision','recall_sensitivity','false_alarms_per_year']
display(ablation[columns].sort_values(['horizon_weeks','model','pr_auc'], ascending=[True,True,False]).round(3))
"""
    ),
    markdown(
        """
## 6. Modelos completos

O projeto mantém referências simples, regressão logística, Random Forest, LSTM NumPy e LSTM PyTorch. A tese não pressupõe que a rede neural será superior. O modelo mais complexo só é favorecido se houver evidência fora do treino.
"""
    ),
    code(
        """
rows = []
for horizon, experiment in results['experiments']['exact'].items():
    for model, values in experiment['metrics'].items():
        rows.append({'horizonte': int(horizon), 'modelo': model, **values['test']})
metrics = pd.DataFrame(rows)
display(metrics[['horizonte','modelo','prevalence','pr_auc','roc_auc','precision','recall_sensitivity','specificity','brier','false_alarms_per_year']].round(3))
"""
    ),
    markdown(
        """
## 7. Estabilidade da LSTM

A LSTM é treinada com diferentes sementes, isto é, diferentes pontos de partida controlados. A média, a dispersão e as falhas são mais importantes do que uma única execução favorável.
"""
    ),
    code("display(stability.round(3))"),
    markdown(
        """
## 8. Explicabilidade com Captum

Integrated Gradients é calculado nas amostras de teste. Occlusion funciona como confirmação parcial. O baseline zero representa a média do treino depois da padronização.

Uma atribuição positiva significa que a entrada aumentou o logit em relação ao baseline. Isso não significa que a variável causou o alerta.
"""
    ),
    code(
        """
for horizon in (4, 8, 12, 16):
    base = OUTPUT_DIR / f'exact/{horizon:02d}_semanas/captum'
    display(Markdown(f'### {horizon} semanas'))
    display(pd.read_csv(base / 'integrated_gradients_features.csv').head(12).round(5))
    display(Image(filename=str(base / 'integrated_gradients_heatmap.png')))
"""
    ),
    markdown(
        """
## 9. Arquivos para o aplicativo

O arquivo legado `app_dados_dengue.json` não é modificado. Cada horizonte recebe:

- `dados/app_previsoes.json`;
- `dados/app_explicabilidade_lstm.json`;
- `metricas/metricas_projeto_mestre.json`;
- figuras auxiliares do Captum.

Todos os JSONs usam datas padronizadas, substituem valores não finitos por `null` e registram versão do modelo, data-alvo, limiar e aviso científico.
"""
    ),
    code(
        """
for horizon in (4, 8, 12, 16):
    path = PROJECT_ROOT / f'outputs/horizontes/{horizon:02d}_semanas/dados/app_previsoes.json'
    payload = json.loads(path.read_text(encoding='utf-8'))
    display(Markdown(f'### {horizon} semanas'))
    display(pd.Series(payload['previsaoAtual'], name='valor').to_frame())
"""
    ),
    markdown(
        """
## 10. Como interpretar o resultado final

O projeto pode concluir que clima e ENSO ajudam, ajudam apenas em certos horizontes ou não acrescentam desempenho ao histórico de casos. As três respostas são cientificamente válidas.

O aplicativo demonstra que os resultados podem ser produzidos e comunicados automaticamente. Ele não transforma uma associação em causalidade nem torna o sistema pronto para decisões de saúde pública.
"""
    ),
    markdown(
        """
## 11. Limitações que devem permanecer na tese

- uma única série municipal;
- poucos episódios independentes;
- ausência atual de validação com alertas oficiais;
- denominador populacional ainda sem fonte formal confirmada;
- disponibilidade real e revisões dos dados precisam ser documentadas;
- 2024–2025 já foi examinado e é avaliação retrospectiva, não teste intocado;
- previsões futuras ou outro município são necessários para validação independente;
- Captum explica o modelo, não mecanismos biológicos.
"""
    ),
    markdown(
        """
## 12. Como executar

Execução completa:

```bash
PYTHONPATH=src ./.venv/bin/python scripts/run_master_study.py
```

Verificação técnica rápida:

```bash
PYTHONPATH=src ./.venv/bin/python scripts/run_master_study.py --quick
```

Testes:

```bash
PYTHONPATH=src ./.venv/bin/python -m unittest discover -s tests -v
```
"""
    ),
]

notebook = nbf.v4.new_notebook(cells=cells)
notebook["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3"},
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(notebook, OUTPUT)
print(OUTPUT)
