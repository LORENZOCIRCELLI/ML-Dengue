# Código auxiliar dos experimentos ENSO

Estes scripts participam das análises intermediárias pertinentes à tese e
permanecem fora de `legacy/`:

- `avaliar_estabilidade.py`: sementes fixas e comparação sem ENSO versus binário;
- `comparar_representacoes_enso.py`: ONI contínuo e comparação de três representações;
- `avaliar_oni_resumido.py`: Random Forest com ONI recente e ONI médio.

Os notebooks e dependências estão nas quatro pastas `experimento_*` da raiz.
Os resultados para consulta estão em [`../results/`](../results/README.md).
Essas análises complementam a comparação consolidada em `comparacao_ENSO/`;
não são executadas automaticamente pelo pipeline operacional.

Os exemplos didáticos com Breast Cancer Wisconsin, seus resultados e o exportador
de exemplos permanecem em [`../legacy/models/`](../legacy/models/README.md).
