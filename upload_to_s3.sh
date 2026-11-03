#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$PROJECT_DIR/scripts/pipeline_runtime.sh"

prepare_runtime "upload"

LOCAL_DIR="$PROJECT_DIR/export"
S3_DEST="${S3_DEST:-s3://dengue-model-results-mldengue/export}"
S3_DEST="${S3_DEST%/}/"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_CLI="${AWS_CLI:-aws}"
DRY_RUN=()

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--dry-run" ) ]]; then
    printf 'Uso: %s [--dry-run]\n' "$0" >&2
    exit 2
fi
if [[ $# -eq 1 ]]; then
    DRY_RUN=(--dryrun)
fi
if [[ "$S3_DEST" != s3://*/* || "$S3_DEST" == 's3:///' ]]; then
    printf 'Destino S3 inválido: %s\n' "$S3_DEST" >&2
    exit 2
fi

command -v "$AWS_CLI" > /dev/null
"$PIPELINE_PYTHON" "$PROJECT_DIR/scripts/validate_app_export.py" "$LOCAL_DIR"

printf '[%s] Enviando somente JSONs de %s para %s.\n' "$(date -Is)" "$LOCAL_DIR" "$S3_DEST"

"$AWS_CLI" s3 sync "$LOCAL_DIR/" "$S3_DEST" \
    --region "$AWS_REGION" \
    --exclude '*' \
    --include '*.json' \
    --exclude 'catalogo.json' \
    --no-follow-symlinks \
    --content-type application/json \
    --cache-control no-cache \
    --no-progress \
    --only-show-errors \
    "${DRY_RUN[@]}"

"$AWS_CLI" s3 cp "$LOCAL_DIR/catalogo.json" "${S3_DEST}catalogo.json" \
    --region "$AWS_REGION" \
    --no-follow-symlinks \
    --content-type application/json \
    --cache-control no-cache \
    --no-progress \
    --only-show-errors \
    "${DRY_RUN[@]}"

printf '[%s] Envio concluído.\n' "$(date -Is)"
