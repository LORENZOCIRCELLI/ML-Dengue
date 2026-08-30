# Dengue Outbreak App

Aplicativo Expo/React Native para dados epidemiológicos, métricas de modelos e notícias brasileiras sobre arboviroses.

## Executar

```bash
npm install
cp .env.example .env
# Preencha EXPO_PUBLIC_GNEWS_API_KEY com uma chave de https://gnews.io/
npm start
```

Os dados dos horizontes de 4, 8, 12 e 16 semanas são lidos diretamente dos oito arquivos JSON públicos no S3. A aba **Tendências** apresenta a série real e a aba **Notícias** consulta a GNews em português, limitada ao Brasil e filtrada por arboviroses.

Não faça commit da chave. Como variáveis `EXPO_PUBLIC_*` ficam acessíveis no aplicativo compilado, use um endpoint intermediário no backend em produção para proteger a cota.

## Verificação

```bash
npm run typecheck
npm run build:web
```
