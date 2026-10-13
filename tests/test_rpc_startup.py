"""Source-owned startup readback evidence; no game bytes or assets."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]/'tools'))
from compare_runtime_rpc import verify_startup


class StartupEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.code = bytes(range(128))
        self.startup = self.code[0x24:0x50]
        (self.root/'loaded-startup.bin').write_bytes(self.startup)
        self.proof = {'startup_address': '0x100024', 'startup_size': 44,
                      'loaded_startup_verified': True,
                      'loaded_startup_sha256': hashlib.sha256(self.startup).hexdigest()}

    def test_valid_body_literals_and_preserved_words(self):
        result = verify_startup(self.root, self.proof, self.code)
        self.assertEqual(result['bss_sha256'], hashlib.sha256(self.startup[:36]).hexdigest())
        self.assertEqual(result['preserved_literals_sha256'], hashlib.sha256(self.startup[36:]).hexdigest())

    def test_original_body_substitution_is_rejected(self):
        altered = bytes(36)+self.startup[36:]
        (self.root/'loaded-startup.bin').write_bytes(altered)
        self.proof['loaded_startup_sha256'] = hashlib.sha256(altered).hexdigest()
        with self.assertRaises(ValueError):
            verify_startup(self.root, self.proof, self.code)

    def test_preserved_literal_change_is_rejected(self):
        altered = self.startup[:36]+bytes(8)
        (self.root/'loaded-startup.bin').write_bytes(altered)
        with self.assertRaises(ValueError):
            verify_startup(self.root, self.proof, self.code)

    def test_wrong_address_or_extent_is_rejected(self):
        for field, value in (('startup_address', '0x100028'), ('startup_size', 36)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_startup(self.root, dict(self.proof, **{field: value}), self.code)


if __name__ == '__main__':
    unittest.main()
