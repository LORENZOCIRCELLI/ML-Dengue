import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SPEC = importlib.util.spec_from_file_location(
    'scheduled_pipeline', ROOT / 'scripts/run_scheduled_pipeline.py',
)
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)


class ScheduledPipelineTests(unittest.TestCase):
    def test_full_pipeline_orders_stages_and_publishes_only_prepared_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / 'export'
            destination.mkdir()
            (destination / 'old.json').write_text('{"previous": true}')
            calls = []

            def execute(arguments, **kwargs):
                calls.append(Path(arguments[-1]).as_posix())
                self.assertTrue(kwargs['check'])

            def retrospective(directory):
                calls.append('retrospectiva')
                self.assertEqual(directory, root / 'v1/results')

            def exporter(source, output, registry):
                calls.append('exportacao')
                self.assertIsNone(registry)
                self.assertEqual(source, root / 'v1/results')
                output.mkdir(parents=True)
                (output / 'catalogo.json').write_text('{"new": true}')

            def module(path):
                if Path(path).name == 'retrospectiva.py':
                    return {'export_retrospectives': retrospective}
                return {'export_results': exporter}

            with patch.object(PIPELINE.subprocess, 'run', side_effect=execute), \
                 patch.object(PIPELINE.runpy, 'run_path', side_effect=module), \
                 patch.object(PIPELINE, 'validate_export', return_value=74):
                PIPELINE.run_pipeline(root)
            self.assertEqual(calls, [
                str(root / 'v1/estudo.py'),
                str(root / 'comparacao_ENSO/estudo.py'),
                'retrospectiva', 'exportacao',
            ])
            self.assertEqual(json.loads((destination / 'catalogo.json').read_text()), {'new': True})
            self.assertTrue((root / '.runtime/export_previous/old.json').exists())

    def test_training_failure_preserves_previous_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'export').mkdir()
            original = root / 'export/catalogo.json'
            original.write_text('{"previous": true}')
            with patch.object(PIPELINE.subprocess, 'run', side_effect=subprocess.CalledProcessError(3, 'training')), \
                 patch.object(PIPELINE.runpy, 'run_path') as loader:
                with self.assertRaises(subprocess.CalledProcessError):
                    PIPELINE.run_pipeline(root)
                loader.assert_not_called()
            self.assertEqual(json.loads(original.read_text()), {'previous': True})

    def test_publication_failure_restores_previous_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.runtime').mkdir()
            (root / 'export').mkdir()
            (root / 'export/catalogo.json').write_text('previous')
            prepared = root / '.runtime/new'
            prepared.mkdir()
            replace = os.replace

            def fail_new(source, destination):
                if source == prepared:
                    raise OSError('simulated failure')
                return replace(source, destination)

            with patch.object(PIPELINE.os, 'replace', side_effect=fail_new):
                with self.assertRaises(OSError):
                    PIPELINE.publish_local_export(root, prepared)
            self.assertEqual((root / 'export/catalogo.json').read_text(), 'previous')


class UploadScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='alphadengue-scheduler-')
        cls.root = Path(cls.temporary.name)
        (cls.root / 'scripts').mkdir()
        for relative in (
            'upload_to_s3.sh', 'Script_Run.sh',
            'scripts/pipeline_runtime.sh', 'scripts/validate_app_export.py',
        ):
            shutil.copy2(ROOT / relative, cls.root / relative)
        shutil.copytree(ROOT / 'export', cls.root / 'export')
        cls.aws = cls.root / 'fake_aws'
        cls.aws.write_text(
            '#!/usr/bin/env python3\n'
            'import json, os, sys\n'
            'with open(os.environ["AWS_TEST_LOG"], "a") as stream:\n'
            ' stream.write(json.dumps(sys.argv[1:])+"\\n")\n'
            'if os.environ.get("AWS_TEST_FAIL") == "1" and sys.argv[2] == "sync":\n'
            ' sys.exit(11)\n'
        )
        cls.aws.chmod(0o755)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_upload(self, fail=False):
        log = self.root / 'calls.jsonl'
        log.unlink(missing_ok=True)
        environment = {
            **os.environ,
            'PIPELINE_PYTHON': sys.executable,
            'AWS_CLI': str(self.aws),
            'AWS_TEST_LOG': str(log),
            'AWS_TEST_FAIL': '1' if fail else '0',
        }
        completed = subprocess.run(
            ['bash', str(self.root / 'upload_to_s3.sh')],
            cwd='/tmp', env=environment, capture_output=True, text=True,
        )
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return completed, calls

    def test_upload_only_export_json_and_catalog_last(self):
        completed, calls = self.run_upload()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][:3], ['s3', 'sync', str(self.root / 'export') + '/'])
        self.assertEqual(calls[1][:3], ['s3', 'cp', str(self.root / 'export/catalogo.json')])
        self.assertEqual(calls[0][3], 's3://dengue-model-results-mldengue/export/')
        self.assertIn('--no-follow-symlinks', calls[0])
        self.assertEqual(calls[0][calls[0].index('--include') + 1], '*.json')
        self.assertNotIn('--delete', calls[0])
        self.assertNotIn(str(self.root / 'outputs'), calls[0])

    def test_failed_sync_does_not_upload_catalog(self):
        completed, calls = self.run_upload(fail=True)
        self.assertEqual(completed.returncode, 11)
        self.assertEqual(len(calls), 1)

    def test_invalid_export_blocks_aws_calls(self):
        catalog = self.root / 'export/catalogo.json'
        original = catalog.read_bytes()
        try:
            catalog.write_text('{"schemaVersion": "invalid"}')
            completed, calls = self.run_upload()
        finally:
            catalog.write_bytes(original)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(calls, [])

    def test_shared_lock_blocks_upload(self):
        import fcntl
        runtime = self.root / '.runtime'
        runtime.mkdir(exist_ok=True)
        with (runtime / 'pipeline.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            completed, calls = self.run_upload()
        self.assertEqual(completed.returncode, 75)
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
