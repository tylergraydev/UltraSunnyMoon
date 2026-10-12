"""Check Evidence envelope compatibility without retail inputs or dependencies."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

# read_json itself requires no Capstone; load just the module using the project's
# analysis virtual environment, which supplies the verifier dependency.
spec = importlib.util.spec_from_file_location('verify_analysis', Path(__file__).parents[1] / 'tools/verify_analysis.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EvidenceInputTests(unittest.TestCase):
    def test_cli_utf16_and_mcp_text_have_the_same_evidence(self):
        evidence = {'evidence_id': 'source-owned-fixture', 'raw_result': {'value': {}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'evidence.json'
            path.write_text(json.dumps(evidence), encoding='utf-16')
            self.assertEqual(module.read_json(path), evidence)
            path.write_text(json.dumps({'content': [{'type': 'text', 'text': json.dumps(evidence)}]}), encoding='utf-8')
            self.assertEqual(module.read_json(path), evidence)

    def test_multiple_text_blocks_are_not_silently_treated_as_complete_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'evidence.json'
            path.write_text(json.dumps({'content': [{'type': 'text', 'text': '{}'}, {'type': 'text', 'text': '{}'}]}))
            with self.assertRaises(ValueError):
                module.read_json(path)


if __name__ == '__main__':
    unittest.main()
