#!/bin/bash

set -e

# Diretório onde este script está localizado
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VENV="$PROJECT_DIR/venv"
NOTEBOOK_DIR="$PROJECT_DIR/notebooks"
NOTEBOOK="Notebook_Atualizado.ipynb"

echo "======================================"
echo "Executando notebook"
echo "======================================"

# Verifica se o ambiente virtual existe
if [ ! -d "$VENV" ]; then
    echo "Erro: venv não encontrado em:"
    echo "$VENV"
    exit 1
fi

# Ativa o ambiente virtual
source "$VENV/bin/activate"

# Entra na pasta dos notebooks
cd "$NOTEBOOK_DIR"

echo "Python:"
which python

echo "Executando: $NOTEBOOK"

jupyter nbconvert \
    --to notebook \
    --execute "$NOTEBOOK" \
    --inplace \
    --ExecutePreprocessor.timeout=-1

echo "======================================"
echo "Notebook executado com sucesso."
echo "======================================"

deactivate
