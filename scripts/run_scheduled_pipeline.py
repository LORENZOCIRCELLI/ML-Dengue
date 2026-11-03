from pathlib import Path
import os
import runpy
import shutil
import subprocess
import sys
import tempfile

from validate_app_export import validate_export


ROOT = Path(__file__).resolve().parents[1]


def publish_local_export(root, source):
    destination = root / 'export'
    previous = root / '.runtime/export_previous'
    if previous.exists():
        shutil.rmtree(previous)
    if destination.exists():
        os.replace(destination, previous)
    try:
        os.replace(source, destination)
    except BaseException:
        if previous.exists():
            os.replace(previous, destination)
        raise


def run_pipeline(root=ROOT):
    root = Path(root).resolve()
    runtime = root / '.runtime'
    runtime.mkdir(exist_ok=True)
    print('Etapa 1/4: treinamento e resultados completos da v1.', flush=True)
    subprocess.run(
        [sys.executable, '-u', str(root / 'v1/estudo.py')],
        cwd=root, check=True,
    )
    print('Etapa 2/4: comparação consolidada ONI/ENSO.', flush=True)
    subprocess.run(
        [sys.executable, '-u', str(root / 'comparacao_ENSO/estudo.py')],
        cwd=root, check=True,
    )
    print('Etapa 3/4: retrospectivas dos três modelos e quatro horizontes.', flush=True)
    retrospective = runpy.run_path(str(root / 'v1/retrospectiva.py'))
    retrospective['export_retrospectives'](root / 'v1/results')
    print('Etapa 4/4: preparação e validação dos JSONs do aplicativo.', flush=True)
    exporter = runpy.run_path(str(root / 'scripts/export_app_json.py'))
    with tempfile.TemporaryDirectory(prefix='export-', dir=runtime) as temporary:
        prepared = Path(temporary) / 'export'
        exporter['export_results'](root / 'v1/results', prepared, None)
        count = validate_export(prepared)
        publish_local_export(root, prepared)
    print(f'Pipeline concluído: {count} JSONs prontos em export.', flush=True)


if __name__ == '__main__':
    run_pipeline()
