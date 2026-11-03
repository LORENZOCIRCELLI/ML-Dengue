prepare_runtime() {
    local task_name="$1"
    local candidate

    export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"
    RUNTIME_DIR="$PROJECT_DIR/.runtime"
    mkdir -p "$RUNTIME_DIR/logs"
    LOG_FILE="$RUNTIME_DIR/logs/${task_name}-$(date '+%Y%m%d-%H%M%S')-$$.log"
    exec > >(tee -a "$LOG_FILE") 2>&1

    trap 'status=$?; printf "[%s] Falha na linha %s; código %s. Log: %s\n" "$(date -Is)" "$LINENO" "$status" "$LOG_FILE" >&2; exit "$status"' ERR

    command -v flock > /dev/null
    exec 9> "$RUNTIME_DIR/pipeline.lock"
    if ! flock -n 9; then
        printf '[%s] Outra execução de treinamento ou upload está ativa.\n' "$(date -Is)" >&2
        exit 75
    fi

    PIPELINE_PYTHON="${PIPELINE_PYTHON:-}"
    if [[ -z "$PIPELINE_PYTHON" ]]; then
        for candidate in "$PROJECT_DIR/venv/bin/python" "$PROJECT_DIR/.venv/bin/python"; do
            if [[ -x "$candidate" ]]; then
                PIPELINE_PYTHON="$candidate"
                break
            fi
        done
    fi
    if [[ -z "$PIPELINE_PYTHON" || ! -x "$PIPELINE_PYTHON" ]]; then
        printf 'Ambiente Python não encontrado. Configure PIPELINE_PYTHON ou crie venv/.venv.\n' >&2
        exit 1
    fi

    export PYTHONUNBUFFERED=1
    export MPLBACKEND=Agg
    export MPLCONFIGDIR="${MPLCONFIGDIR:-$RUNTIME_DIR/matplotlib}"
    export AWS_PAGER=""
    export AWS_CLI_AUTO_PROMPT=off
    mkdir -p "$MPLCONFIGDIR"
    cd -- "$PROJECT_DIR"
}
