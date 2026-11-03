#!/usr/bin/env python3
"""Gera o notebook de pesquisa a partir do pipeline versionável em Python."""

from pathlib import Path
import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks/Notebook_Metodologicamente_Revisado.ipynb"


def markdown(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


cells = [
    markdown("""
# Previsão temporal de surtos de dengue — versão metodologicamente revisada

Este notebook acompanha o estudo de doutorado sobre previsão de surtos de dengue em Ribeirão Preto. Cada previsão usa informações disponíveis até a semana de emissão e avalia horizontes de 4, 8, 12 e 16 semanas.

O código analítico foi organizado em `src/dengue_research` para permitir revisão, reutilização e controle de versão. O notebook documenta e executa o pipeline sem duplicar blocos por horizonte.
"""),
    markdown("""
## Protocolo pré-especificado

- Análise principal: surto exatamente em `t+h`.
- Análise complementar: pelo menos uma semana de surto entre `t+1` e `t+h`.
- Treino: datas-alvo até 2021-12-26.
- Validação: 2022–2023.
- Teste final: 2024–2025.
- Casos entram com atraso mínimo de uma semana.
- Métrica principal: PR-AUC; operação orientada a recall mínimo de 0,80 na validação.
- O teste não escolhe features, hiperparâmetros, épocas ou limiares.
"""),
    code("""
from pathlib import Path
import sys
import pandas as pd
from IPython.display import display, Image

PROJECT_ROOT = Path.cwd().resolve().parent if Path.cwd().name == 'notebooks' else Path.cwd().resolve()
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from dengue_research.pipeline import StudyConfig, load_weekly_data, audit_data, causal_endemic_channel
from dengue_research.reporting import load_results, metrics_frame, split_frame

config = StudyConfig(
    data_path=PROJECT_ROOT / 'data/dataset/processado/base_modelagem_dengue_dataset.xlsx',
    output_dir=PROJECT_ROOT / 'outputs/revisao_metodologica',
)
config
"""),
    markdown("""
## Auditoria dos dados

A célula seguinte verifica continuidade semanal, duplicatas, valores ausentes, intervalo temporal e compatibilidade das variáveis espaciais com o alvo municipal.
"""),
    code("""
df = load_weekly_data(config)
pd.Series(audit_data(df, config), name='valor').to_frame()
"""),
    markdown("""
## Canal endêmico causal

O limite de cada semana usa somente anos anteriores. Isso simula a informação disponível naquele momento e evita que 2024–2025 altere os rótulos do período de desenvolvimento.
"""),
    code("""
endemic = causal_endemic_channel(df, config)
display(endemic[['endemic_threshold', 'outbreak']].dropna().head())
print('Semanas rotuladas:', endemic['outbreak'].notna().sum())
print('Semanas de surto:', int(endemic['outbreak'].fillna(0).sum()))
"""),
    markdown("""
## Execução completa

A execução treina baselines, regressão logística, Random Forest, LSTM NumPy com BPTT completo e LSTM PyTorch. Também calcula intervalos por bootstrap, regressão de casos e explicações Captum. Para reproduzir todos os resultados, execute no terminal do projeto:

```bash
MPLCONFIGDIR=/tmp/mpl-dengue .venv/bin/python scripts/run_revised_study.py
```
"""),
    code("""
results_path = config.output_dir / 'resultados_completos.json'
if not results_path.exists():
    raise FileNotFoundError('Execute scripts/run_revised_study.py antes desta seção.')
results = load_results(results_path)
metrics = metrics_frame(results)
splits = split_frame(results)
"""),
    markdown("## Partições temporais e prevalência"),
    code("""
display(splits)
display(Image(filename=str(config.output_dir / 'figuras/prevalencia_particoes.png')))
"""),
    markdown("## Resultados da previsão exata"),
    code("""
exact_test = metrics.query("target_kind == 'exact' and split == 'test'")
display(exact_test[['horizon','model_label','pr_auc','roc_auc','precision','recall_sensitivity','f2','false_alarms_per_year']]
        .sort_values(['horizon','pr_auc'], ascending=[True,False]))
display(Image(filename=str(config.output_dir / 'figuras/comparacao_exact.png')))
"""),
    markdown("## Análise complementar em janela"),
    code("""
window_test = metrics.query("target_kind == 'window' and split == 'test'")
display(window_test[['horizon','model_label','prevalence','pr_auc','recall_sensitivity','false_alarms_per_year']]
        .sort_values(['horizon','pr_auc'], ascending=[True,False]))
display(Image(filename=str(config.output_dir / 'figuras/comparacao_window.png')))
"""),
    markdown("""
## Explicabilidade do LSTM PyTorch

Integrated Gradients e Occlusion são calculados somente no teste. O vetor zero no espaço padronizado representa a média do treino. As atribuições explicam a saída do modelo; não estabelecem causalidade epidemiológica.
"""),
    code("""
for horizon in config.horizons:
    path = config.output_dir / 'exact' / f'{horizon:02d}_semanas' / 'captum/integrated_gradients_features.csv'
    print()
    print(f'Horizonte {horizon} semanas')
    display(pd.read_csv(path).head(10))
"""),
    markdown("""
## Relatório e rastreabilidade

O relatório integral está em `reports/relatorio_revisao_metodologica.md`. Ele registra a formulação, as correções, as métricas, a explicabilidade, as limitações e as ameaças à validade. O notebook original permanece inalterado.
"""),
]

notebook = nbf.v4.new_notebook(cells=cells)
notebook["metadata"]["kernelspec"] = {
    "display_name": "Python 3 (ML-Dengue)",
    "language": "python",
    "name": "python3",
}
notebook["metadata"]["language_info"] = {"name": "python", "version": "3.12"}
nbf.write(notebook, OUTPUT)
print(OUTPUT)
