# AlphaDengue — execução agendada no EC2

## Fluxo

`Script_Run.sh` executa, nesta ordem:

1. Treinamento completo da v1: RF, RNN e LSTM, quatro horizontes, cinco sementes, avaliação, gráficos, explicabilidade e previsões.
2. Comparação ONI/ENSO nas três representações e quatro horizontes. Combinações concluídas com código, dados e protocolo idênticos podem ser reutilizadas pelo experimento.
3. Exportação das retrospectivas de teste dos três modelos e quatro horizontes.
4. Geração dos JSONs do aplicativo em uma pasta temporária, validação e substituição da pasta `export` somente após sucesso.

As funções analíticas são as mesmas usadas pelos notebooks. A rotina chama os scripts Python diretamente, sem Jupyter, kernel interativo ou alteração das saídas dos notebooks.

Os resultados científicos completos ficam no EC2, em `v1/results` e `comparacao_ENSO/results`. Somente a pasta `export` é usada por `upload_to_s3.sh`. Modelos, imagens, notebooks, logs, CSVs e resultados da comparação ENSO não são enviados.

## Preparação no EC2

O repositório, o dataset processado e as dependências de `v1/requirements.txt` precisam estar presentes na instância. O pipeline usa a base em `data/dataset/processado/base_modelagem_dengue_dataset.xlsx`; ele não busca nem atualiza essa base em serviços externos.

Os scripts detectam `venv/bin/python` e depois `.venv/bin/python`. Para escolher explicitamente o ambiente, configure `PIPELINE_PYTHON` com o caminho absoluto do executável. A AWS CLI deve estar instalada e ter credenciais/permissões para o bucket, preferencialmente por uma IAM role associada ao EC2. Os scripts não armazenam chaves.

Ambos os scripts podem ser chamados de qualquer diretório e têm permissão de execução. Dependem de Bash e `flock`, normalmente fornecido pelo pacote `util-linux` no Linux.

## Execução

```bash
/home/admin/ml-dengue/Script_Run.sh
/home/admin/ml-dengue/upload_to_s3.sh
```

O destino padrão é `s3://dengue-model-results-mldengue/export/`, na região `us-east-1`. É possível configurar `S3_DEST`, `AWS_REGION` e `AWS_CLI` no ambiente. `AWS_CLI` aceita o caminho absoluto do executável, útil quando o cron não carrega o PATH do terminal.

Para pré-visualizar as operações da AWS CLI:

```bash
/home/admin/ml-dengue/upload_to_s3.sh --dry-run
```

O modo dry-run não transfere arquivos, mas a AWS CLI ainda pode consultar o bucket e precisar de credenciais. Os testes automatizados do projeto substituem a AWS CLI por um executável simulado, sem acessar a AWS.

## Cron

Exemplo semanal, aos domingos às 03:00 no fuso configurado na instância. Ajuste o horário e o caminho ao seu EC2:

```cron
SHELL=/bin/bash
PIPELINE_PYTHON=/home/admin/ml-dengue/venv/bin/python
AWS_REGION=us-east-1
S3_DEST=s3://dengue-model-results-mldengue/export/
0 3 * * 0 /home/admin/ml-dengue/Script_Run.sh && /home/admin/ml-dengue/upload_to_s3.sh
```

O `&&` impede o envio quando o treinamento ou a exportação falham. Não é necessário ativar o venv manualmente ou entrar na pasta do projeto. Nenhuma tarefa é instalada automaticamente por esta adaptação.

## Logs e concorrência

Os logs ficam em `.runtime/logs`, separados por execução. O código de erro é preservado. Os dois scripts usam o mesmo bloqueio `.runtime/pipeline.lock`; uma execução concorrente termina com código 75. Assim, treinamento e upload não operam simultaneamente sobre a exportação.

A cópia anterior de `export` fica em `.runtime/export_previous` após uma publicação local bem-sucedida, sendo substituída na publicação seguinte. Se uma etapa anterior falhar, a exportação em uso permanece intacta.

O upload valida os JSONs antes de chamar a AWS, sincroniza os arquivos individuais e só depois envia `catalogo.json`. Não usa `--delete`, não muda ACLs e não altera o prefixo antigo `outputs/`. Publicar o catálogo por último não torna a atualização de múltiplos objetos uma transação atômica no S3.

## Configuração do aplicativo após a publicação

Configure `EXPO_PUBLIC_RESULTS_BASE_URL` com a URL HTTP da pasta que contém o novo `catalogo.json`. Exemplo para o bucket atual, se seus objetos forem acessíveis ao aplicativo:

```env
EXPO_PUBLIC_RESULTS_BASE_URL=https://dengue-model-results-mldengue.s3.us-east-1.amazonaws.com/export
```

A configuração de acesso do bucket/API e CORS será tratada na etapa de infraestrutura. Os scripts não tornam objetos públicos nem criam uma API.

Referências: [AWS CLI — s3 sync](https://docs.aws.amazon.com/cli/latest/reference/s3/sync.html) e [AWS CLI — s3 cp](https://docs.aws.amazon.com/cli/latest/reference/s3/cp.html).
