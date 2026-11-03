# AlphaDengue

Aplicativo Expo/React Native para consultar os resultados de Random Forest, RNN e LSTM nos horizontes de 4, 8, 12 e 16 semanas.

## Exportar os resultados

Na raiz do projeto:

```bash
python3 scripts/export_app_json.py
```

O script copia 74 JSONs de `v1/results` para `export`, preservando seus conteúdos e caminhos. Inclui o catálogo, a série histórica e, para cada modelo/horizonte, previsão, métricas, explicabilidade, conclusão, resultado completo e retrospectiva. Não treina modelos nem altera os resultados.

O mesmo comando atualiza `src/generated/results.ts`, o índice de imports da cópia local. O aplicativo importa os arquivos de `export`; não importa arquivos de `v1/results` ou dos experimentos antigos. O resultado completo fica disponível para publicação, mas não é carregado junto com os arquivos individuais para evitar duplicar dados na memória.

## Executar com os JSONs locais

```bash
cd mobile
npm install
cp .env.example .env
npm run export:data
npm start
```

Deixe `EXPO_PUBLIC_RESULTS_BASE_URL` vazio para usar a pasta `export` na compilação. Depois de atualizar os JSONs, reinicie o Expo com `npx expo start --clear` se o cache não refletir os arquivos novos.

## Consumir uma API ou S3

Publique o conteúdo de `export` preservando a estrutura de pastas. Configure a URL que contém `catalogo.json`:

```env
EXPO_PUBLIC_RESULTS_BASE_URL=https://seu-endpoint/export
```

A aplicação solicita `catalogo.json` e resolve os caminhos relativos indicados no próprio catálogo. Se o conteúdo de `export` for publicado na raiz de um bucket ou domínio, use essa raiz como URL-base. A URL-base é configuração pública, sem credenciais.

Uma API pode servir os mesmos caminhos e retornar os mesmos JSONs. Não é necessário converter o formato para o schema antigo do aplicativo. Ao alterar a variável, reinicie o Expo ou gere uma nova compilação. Quando a fonte remota estiver configurada, erros de rede ou de formato são exibidos; não há substituição silenciosa por mocks ou dados locais.

No Expo Web, configure CORS no S3/API para permitir a origem do aplicativo. O arquivo `s3-cors.json` contém um exemplo para objetos públicos. Esta entrega prepara os arquivos e o cliente; não publica nada na AWS.

No EC2, é possível exportar somente os arquivos de dados, sem gerar o índice do aplicativo:

```bash
python3 scripts/export_app_json.py --no-registry
```

Depois, envie o conteúdo de `export/` para o prefixo escolhido no S3. O catálogo e suas subpastas devem permanecer juntos.

## Conteúdo exibido

- Painel: casos observados da série exportada, referência do critério e previsões dos três modelos no menor horizonte disponível.
- Previsões: resposta sim/não, semana-alvo, critério, acerto histórico e tamanho da avaliação, avisos, conclusão integral e explicabilidade SHAP ou Saliency/Integrated Gradients.
- Modelos: métricas de teste, resumos de treino/validação/teste, baseline sempre negativo, matrizes de confusão e curvas ROC.
- Notícias: serviço GNews existente, independente dos resultados dos modelos.

O escore não calibrado não é apresentado como probabilidade de surto. A taxa de acerto histórico não é apresentada como probabilidade de uma previsão individual estar correta. A classificação indica aumento de pelo menos 50%, conforme o critério contido em cada previsão.

As telas auxiliares de Tendências e Retrospectiva, fora da navegação atual, permanecem com a integração anterior. A retrospectiva binária já está exportada em `retrospectiva.json` por modelo/horizonte; sua tela ainda precisa ser adaptada, pois o contrato anterior esperava estimativas de quantidade de casos.

## Verificar

```bash
npm run typecheck
npm test
npm run format:check
npm run build:web
```

Na raiz, o teste do exportador pode ser executado com:

```bash
python3 -m unittest discover -s tests -p test_app_export.py
```

## Identidade visual

Os tokens visuais estão em `src/theme/colors.ts`, a estrutura de página em `src/theme/layout.ts` e o cabeçalho em `src/components/ScreenHeader.tsx`. Use `npm run format` para manter a formatação.
