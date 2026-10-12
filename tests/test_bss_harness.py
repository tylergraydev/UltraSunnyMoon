"""Source-owned probes check failures in the isolated startup-clearer harness."""
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]/'tools'))
from verify_bss_behavior import execute, BSS_START, BSS_END


class BssHarnessTests(unittest.TestCase):
    def test_noop_cannot_pass_even_when_memory_is_already_zero(self):
        # Source-owned ARM bx lr.
        with self.assertRaisesRegex(ValueError, 'every BSS word'):
            execute(struct.pack('<I', 0xe12fff1e), pattern=0)

    def test_callee_saved_corruption_is_rejected(self):
        # mov r4, #0; bx lr
        with self.assertRaisesRegex(ValueError, 'Callee-saved'):
            execute(struct.pack('<II', 0xe3a04000, 0xe12fff1e))

    def test_wrong_store_value_is_rejected(self):
        # ldr r0, [pc, #8]; mov r1, #1; str r1, [r0]; bx lr; address
        with self.assertRaisesRegex(ValueError, 'Store order'):
            execute(struct.pack('<5I', 0xe59f0008, 0xe3a01001, 0xe5801000,
                                0xe12fff1e, BSS_START))

    def test_byte_store_is_rejected(self):
        # ldr r0, [pc, #8]; mov r1, #0; strb r1, [r0]; bx lr; address
        with self.assertRaisesRegex(ValueError, 'width'):
            execute(struct.pack('<5I', 0xe59f0008, 0xe3a01000, 0xe5c01000,
                                0xe12fff1e, BSS_START))

    def test_write_at_exclusive_end_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Store order'):
            execute(struct.pack('<5I', 0xe59f0008, 0xe3a01000, 0xe5801000,
                                0xe12fff1e, BSS_END))


if __name__ == '__main__':
    unittest.main()
