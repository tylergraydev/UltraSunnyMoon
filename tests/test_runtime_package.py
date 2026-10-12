"""Check package validation using a source-owned synthetic NCCH/ExeFS fixture."""
from pathlib import Path
import hashlib
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]/'tools'))
from verify_runtime_package import inspect


class PackageValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'fixture.cxi'
        self.code = bytes(range(128))
        self.data = bytearray(4096)
        self.data[0x100:0x104] = b'NCCH'
        struct.pack_into('<I', self.data, 0x104, 8)
        self.data[0x18f] = 4
        struct.pack_into('<I', self.data, 0x180, 0x400)
        self.data[0x160:0x180] = hashlib.sha256(self.data[0x200:0x600]).digest()
        struct.pack_into('<III', self.data, 0x1a0, 5, 2, 1)
        struct.pack_into('<III', self.data, 0x1b0, 7, 1, 1)
        struct.pack_into('<8sII', self.data, 0xa00, b'.code', 0, len(self.code))
        self.data[0xc00:0xc80] = self.code
        self.data[0xbe0:0xc00] = hashlib.sha256(self.code).digest()
        self.data[0x1c0:0x1e0] = hashlib.sha256(self.data[0xa00:0xc00]).digest()
        self.data[0x1e0:0x200] = hashlib.sha256(self.data[0xe00:0x1000]).digest()
        self.path.write_bytes(self.data)

    def test_valid_code_and_region_hashes(self):
        self.assertEqual(inspect(self.path, self.code)['entries'], ['.code'])

    def test_payload_corruption_is_rejected(self):
        self.data[0xc00] ^= 1
        self.path.write_bytes(self.data)
        with self.assertRaisesRegex(ValueError, 'entry hash'):
            inspect(self.path, self.code)

    def test_hash_header_corruption_is_rejected(self):
        self.data[0xbe0] ^= 1
        self.path.write_bytes(self.data)
        with self.assertRaisesRegex(ValueError, 'superblock hash'):
            inspect(self.path, self.code)

    def test_wrong_selected_code_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'selected image'):
            inspect(self.path, self.code[::-1])


if __name__ == '__main__':
    unittest.main()
