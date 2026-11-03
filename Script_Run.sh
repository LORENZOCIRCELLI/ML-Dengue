#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$PROJECT_DIR/scripts/pipeline_runtime.sh"

prepare_runtime "treinamento"

printf '[%s] Iniciando pipeline completo com %s.\n' "$(date -Is)" "$PIPELINE_PYTHON"
"$PIPELINE_PYTHON" -u "$PROJECT_DIR/scripts/run_scheduled_pipeline.py"
printf '[%s] Pipeline concluído; JSONs disponíveis em %s/export.\n' "$(date -Is)" "$PROJECT_DIR"
