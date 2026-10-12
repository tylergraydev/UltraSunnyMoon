"""Source-owned selection regressions; no retail bytes or generated objects."""
import copy
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import bss_selection
import rebuild_main
from rebuild_module import digest


class BssSelectionTests(unittest.TestCase):
    def fixture(self):
        code, header, obj, payload = bytes(0x100), b'header', b'source-owned-object', b'X'*36
        source = digest(Path('src/runtime/clear_bss.c').read_bytes())
        identities = {'source_sha256': source, 'code_sha256': digest(code), 'exheader_sha256': digest(header)}
        compilation = dict(identities, entry='0x100024', mode='arm',
                           original_with_literals_sha256=digest(code[0x24:0x48]),
                           compiler={'sha256': 'compiler', 'backend_sha256': 'backend'},
                           profiles=[{'object': 'Os.o', 'object_sha256': digest(obj),
                                      'text_sha256': digest(payload), 'compiled_size': 36, 'command': ['compile']}])
        cases = [{'pattern': 165}, {'pattern': 255}, {'pattern': 0}, {'pattern': None, 'thumb_return': True}]
        behavior = dict(identities, object_sha256=digest(obj), entry='0x100024', mode='arm',
                        bss_start='0x6a3d48', bss_end_exclusive='0x6d3f04',
                        bounds_verified_against_exheader=True, cases_passed=4, cpu_model='ARM11 MPCore',
                        harness_sha256=digest(Path('tools/verify_bss_behavior.py').read_bytes()),
                        cases=[{'case': c, 'passed': True, 'result': {
                            'word_writes': 49263, 'cleared_bytes': 197052,
                            'thumb_return': c.get('thumb_return', False), 'canaries_preserved': True,
                            'callee_saved_preserved': True, 'stack_unchanged': True}} for c in cases])
        receipt = {'object_name': 'Os.o', 'object_sha256': digest(obj),
                   'compilation': compilation, 'behavior': behavior, 'policy': 'behavior-tested-nonmatching'}
        self.seal(receipt)
        return code, header, obj, payload, receipt

    def seal(self, receipt):
        for name in ('compilation', 'behavior'):
            receipt[name+'_sha256'] = digest(json.dumps(receipt[name], sort_keys=True).encode())

    def test_valid_receipt_and_arm_object_gate(self):
        code, header, obj, payload, receipt = self.fixture()
        with patch.object(bss_selection, 'standalone_helper', return_value=payload) as gate:
            self.assertEqual(bss_selection.validate(obj, receipt, code, header), payload)
            gate.assert_called_once_with(obj, 'ultrasun_clear_bss', thumb=False)

    def test_modified_receipts_rejected(self):
        code, header, obj, payload, receipt = self.fixture()
        for name in ('behavior', 'compilation'):
            candidate = copy.deepcopy(receipt)
            candidate[name]['source_sha256'] = 'wrong'
            with self.subTest(name=name), patch.object(bss_selection, 'standalone_helper', return_value=payload):
                with self.assertRaises(ValueError):
                    bss_selection.validate(obj, candidate, code, header)

    def test_wrong_identity_coverage_and_policy_rejected(self):
        code, header, obj, payload, receipt = self.fixture()
        for change in (
                lambda r: r['behavior'].update(object_sha256='wrong'),
                lambda r: r['compilation'].update(exheader_sha256='wrong'),
                lambda r: r['behavior']['cases'].pop(),
                lambda r: r['behavior']['cases'][0]['result'].update(word_writes=0),
                lambda r: r.update(policy='exact')):
            candidate = copy.deepcopy(receipt)
            change(candidate)
            self.seal(candidate)
            with patch.object(bss_selection, 'standalone_helper', return_value=payload):
                with self.assertRaises(ValueError):
                    bss_selection.validate(obj, candidate, code, header)

    def test_split_policy_preserves_later_literals(self):
        code = bytes(0x7000)
        header = bytearray(0x40)
        for offset, address, pages, logical in ((0x10, 0x100000, 5, 0x4900),
                                               (0x20, 0x105000, 1, 16), (0x30, 0x106000, 1, 16)):
            struct.pack_into('<III', header, offset, address, pages, logical)
        with patch.object(rebuild_main, 'CODE_SHA256', digest(code)), patch.object(rebuild_main, 'EXHEADER_SHA256', digest(header)):
            for bss in (False, True):
                plan = rebuild_main.layout(code, header, bss=bss)
                zero, literals = plan['objects'][1:3]
                self.assertEqual(zero['offset'], 0x24)
                self.assertEqual(zero['size'], 36 if bss else 28)
                self.assertEqual(literals['offset']+literals['size'], 0x50)
                self.assertEqual(literals['offset'], 0x48 if bss else 0x40)
                cursor = 0
                for obj in plan['objects']:
                    self.assertEqual(obj['offset'], cursor)
                    cursor += obj['size']
                self.assertEqual(cursor, len(code))


if __name__ == '__main__':
    unittest.main()
