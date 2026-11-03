import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('export_app_json', ROOT / 'scripts/export_app_json.py')
EXPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORTER)


class AppExportTests(unittest.TestCase):
    def test_complete_export_preserves_bytes_and_is_repeatable(self):
        source = ROOT / 'v1/results'
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'export'
            registry = Path(directory) / 'mobile/src/generated/results.ts'
            count = EXPORTER.export_results(source, destination, registry)
            catalog_source = json.loads((source / 'catalogo.json').read_text())
            expected = 62 + sum('retrospectiva' in entry for entry in catalog_source['resultados'])
            self.assertEqual(count, expected)
            exported = {str(path.relative_to(destination)): path.read_bytes() for path in destination.rglob('*.json')}
            self.assertEqual(len(exported), expected)
            for relative, content in exported.items():
                self.assertEqual(content, (source / relative).read_bytes(), relative)
            catalog = json.loads((destination / 'catalogo.json').read_text())
            for entry in catalog['resultados']:
                for field in EXPORTER.RESOURCE_FIELDS:
                    self.assertTrue((destination / entry[field]).is_file())
            previous_registry = registry.read_bytes()
            EXPORTER.export_results(source, destination, registry)
            self.assertEqual(previous_registry, registry.read_bytes())
            self.assertNotIn('v1/results', registry.read_text())

    def test_invalid_source_does_not_publish_partial_export(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            source.mkdir()
            (source / 'catalogo.json').write_text('{"resultados": []}')
            destination = Path(directory) / 'export'
            with self.assertRaises(ValueError):
                EXPORTER.export_results(source, destination, None)
            self.assertFalse(destination.exists())

    def test_rejects_paths_outside_export(self):
        for value in ('../outside.json', '/outside.json', 'x/../../outside.json', 'https://example.test/file.json', 'x\\outside.json'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    EXPORTER.resource_path(value)

    def test_source_cannot_be_overwritten(self):
        source = ROOT / 'v1/results'
        with self.assertRaises(ValueError):
            EXPORTER.export_results(source, source, None)


if __name__ == '__main__':
    unittest.main()
