#!/usr/bin/env python3
"""Constrói o notebook auditável da especificação epidemiológica."""

from pathlib import Path
import nbformat as nbf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "notebooks/Notebook_Definicao_Epidemiologica.ipynb"


def markdown(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


cells = [
    markdown(
        """
# Previsão de alertas de dengue — definição epidemiológica

Esta é uma **segunda especificação**, mantida separada de `Notebook_Metodologicamente_Revisado.ipynb` e do notebook original. O objetivo é prever, com 4, 8, 12 e 16 semanas de antecedência:

1. o estado operacional de alerta exatamente em `t+h`;
2. o início de um novo episódio em qualquer semana de `t+1` a `t+h`.

O termo *alerta* é usado de forma deliberada. Um cruzamento do canal endêmico não equivale, sozinho, a uma declaração oficial de epidemia.
"""
    ),
    markdown(
        """
## Especificação pré-definida

- incidência = casos / população × 100.000;
- canal causal com somente anos anteriores;
- sete anos históricos, semanas epidemiológicas ±2 e mínimo de três anos;
- transformação `log1p`, centro geométrico e limite `média + 1,96 DP`;
- mobilização: acima da mediana e abaixo do limite por quatro semanas consecutivas;
- alerta: acima do limite superior por quatro semanas consecutivas;
- treino por data-alvo até 2021, validação 2022–2023 e teste 2024–2025.

Referências metodológicas: [Plano Nacional 2025](https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/guias-e-manuais/2025/plano-de-contingencia-nacional-para-dengue-chikungunya-e-zika.pdf/@@download/file) e [diretrizes da OMS](https://tdr.who.int/docs/librariesprovider10/meeting-reports/dengue-diagnosis-pdf.pdf?download=true&sfvrsn=ef5ec264_0).
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
OUTPUT_DIR = PROJECT_ROOT / 'outputs/revisao_epidemiologica'
REEXECUTE = False  # altere conscientemente para True para treinar tudo novamente

if REEXECUTE or not (OUTPUT_DIR / 'resultados_completos.json').exists():
    subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts/run_epidemiological_study.py')], cwd=PROJECT_ROOT, check=True)

results = json.loads((OUTPUT_DIR / 'resultados_completos.json').read_text(encoding='utf-8'))
metrics = pd.read_csv(OUTPUT_DIR / 'metricas_consolidadas.csv')
splits = pd.read_csv(OUTPUT_DIR / 'particoes_temporais.csv')
episodes = pd.read_csv(OUTPUT_DIR / 'episodios_alerta.csv')
event_metrics = pd.read_csv(OUTPUT_DIR / 'metricas_episodios.csv')
sensitivity = pd.read_csv(OUTPUT_DIR / 'sensibilidade_definicao.csv')
print('Projeto:', PROJECT_ROOT)
print('Execução carregada:', OUTPUT_DIR)
"""
    ),
    markdown(
        """
## 1. Auditoria do dado e do denominador

`dem` é operacionalizado como população residente porque é positivo, não possui ausências e tem magnitude populacional. A documentação presente no repositório, porém, não contém dicionário de variáveis. A fonte, o ano de referência e a mudança de 711.825 para 702.739 precisam ser confirmados antes da tese.
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
## 2. Canal endêmico e episódios

As colunas `ano` e `semana_epidemiologica` do banco são usadas diretamente. Isso evita o deslocamento que ocorreria ao aplicar a semana ISO ao domingo que inicia cada semana epidemiológica.
"""
    ),
    code(
        """
display(episodes)
display(Image(filename=str(OUTPUT_DIR / 'figuras/canal_endemico_completo.png')))
display(Image(filename=str(OUTPUT_DIR / 'figuras/canal_endemico_teste_2024_2025.png')))
"""
    ),
    markdown(
        """
## 3. Partições temporais

A partição é feita pela **data-alvo**, não pela data de emissão. Isso impede que uma previsão emitida no fim do treino tenha desfecho localizado na validação ou no teste. Transformações são ajustadas somente no treino; validação escolhe hiperparâmetros, early stopping e limiar; teste é usado uma vez.
"""
    ),
    code(
        """
display(splits[splits.target_kind.eq('exact')][['horizon','split','n','positive','prevalence','first_target_date','last_target_date']])
"""
    ),
    markdown(
        """
## 4. Modelos e resultado semanal

São comparados baseline sazonal, baseline de persistência, regressão logística, Random Forest, LSTM NumPy com BPTT completo e LSTM PyTorch. PR-AUC é a métrica principal de discriminação; o limiar é escolhido na validação visando recall ≥0,80 e maior precisão. Recall, especificidade, Brier e alarmes falsos descrevem o comportamento operacional.
"""
    ),
    code(
        """
exact_test = metrics[(metrics.target_kind == 'exact') & (metrics.split == 'test')]
columns = ['horizon','model_label','prevalence','pr_auc','roc_auc','precision','recall_sensitivity','specificity','f2','brier','false_alarms_per_year']
display(exact_test[columns].sort_values(['horizon','pr_auc'], ascending=[True,False]).round(3))
display(Image(filename=str(OUTPUT_DIR / 'figuras/comparacao_exact.png')))
"""
    ),
    markdown(
        """
### Interpretação central

O desempenho elevado da definição P75 anterior não se reproduz com o alerta epidemiológico mais estrito. No teste, a prevalência é cerca de 18%, o LSTM PyTorch apresenta PR-AUC inferior à prevalência em todos os horizontes e modelos simples são mais competitivos. Os baselines que obtêm recall 1 classificam praticamente todas as semanas como positivas no limiar selecionado e, portanto, não são operacionalmente úteis.

Esse resultado negativo não deve ser ocultado nem “corrigido” escolhendo uma nova definição após observar o teste. Ele indica forte dependência do construto e amostra insuficiente para sustentar a LSTM como modelo principal.
"""
    ),
    markdown(
        """
## 5. Início de episódios e antecedência

Um episódio é detectado se houver ao menos um aviso entre `início-h` e `início-1`. Como existem somente dois inícios no teste, recall de episódio assume apenas 0, 0,5 ou 1; alarmes falsos e validação prospectiva são indispensáveis para interpretação.
"""
    ),
    code(
        """
display(event_metrics[['horizon','model_label','n_test_episodes','episodes_detected','episode_recall','median_maximum_lead_weeks','false_warning_weeks_per_year']].sort_values(['horizon','episode_recall','false_warning_weeks_per_year'], ascending=[True,False,True]).round(3))
"""
    ),
    markdown(
        """
## 6. Sensibilidade do desfecho

Vinte e quatro especificações variam janela histórica, raio de semanas, limite superior e persistência. Essa análise mede incerteza da definição, mas não autoriza escolher retrospectivamente o rótulo que maximiza o desempenho.
"""
    ),
    code(
        """
display(sensitivity.sort_values('jaccard_vs_primary').round(3))
display(Image(filename=str(OUTPUT_DIR / 'figuras/sensibilidade_definicao.png')))
"""
    ),
    markdown(
        """
## 7. Captum no LSTM PyTorch

Integrated Gradients e Occlusion usam apenas amostras de teste. O baseline zero no espaço padronizado corresponde à média do treino. As atribuições explicam logits do modelo e não causalidade epidemiológica.
"""
    ),
    code(
        """
for horizon in (4,8,12,16):
    path = OUTPUT_DIR / f'exact/{horizon:02d}_semanas/captum/integrated_gradients_features.csv'
    top = pd.read_csv(path).head(8)
    display(Markdown(f'### Horizonte: {horizon} semanas'))
    display(top.round(5))
    display(Image(filename=str(OUTPUT_DIR / f'exact/{horizon:02d}_semanas/captum/integrated_gradients_heatmap.png')))
"""
    ),
    markdown(
        """
## 8. Comparação com a versão anterior

A comparação é descritiva porque os rótulos representam construtos diferentes. Concordância alta entre semanas negativas pode coexistir com baixa concordância entre semanas positivas; por isso, Jaccard e prevalência são apresentados junto às métricas.
"""
    ),
    code(
        """
comparison_path = PROJECT_ROOT / 'reports/comparacao_definicoes.md'
display(Markdown(comparison_path.read_text(encoding='utf-8')))
"""
    ),
    markdown(
        """
## 9. Limitações decisivas

- seis episódios totais e apenas dois em cada partição principal;
- ausência de rótulo oficial independente de surto/epidemia;
- `dem` sem proveniência formal confirmada;
- uma única série municipal;
- latência de notificação e revisão de dados ainda não modeladas;
- clima e índices externos dependem da disponibilidade real na data de emissão;
- resultados de uma semente não quantificam instabilidade da LSTM.

O pipeline é adequado para uma análise de doutorado transparente, mas os resultados atuais **não sustentam implantação operacional** nem superioridade da LSTM. O próximo passo científico é validar o desfecho com vigilância epidemiológica, documentar as fontes, repetir sementes e realizar validação geográfica ou prospectiva.
"""
    ),
    markdown(
        """
## 10. Artefatos reproduzíveis

- execução: `scripts/run_epidemiological_study.py`;
- definição e avaliação: `src/dengue_research/epidemiology.py`;
- relatórios: `src/dengue_research/epidemiological_reporting.py`;
- resultados completos: `outputs/revisao_epidemiologica`;
- relatório detalhado: `reports/relatorio_definicao_epidemiologica.md`.
"""
    ),
]

nb = nbf.v4.new_notebook(cells=cells)
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3"},
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUTPUT)
print(OUTPUT)
