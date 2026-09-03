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

## CORS do S3 para Expo Web

Apps Android/iOS podem ler os objetos públicos diretamente. Navegadores exigem que o bucket autorize a origem do app. Em **S3 → bucket → Permissions → Cross-origin resource sharing (CORS)**, use o conteúdo de `s3-cors.json`. Como esses JSONs já são públicos, o arquivo permite leitura `GET/HEAD` de qualquer origem; restrinja `AllowedOrigins` ao domínio do app se preferir.

## Verificação

```bash
npm run typecheck
npm run build:web
```

Depois de substituir uma versão anterior do projeto, limpe o cache do Metro antes de testar:

```bash
npx expo start --clear
```
