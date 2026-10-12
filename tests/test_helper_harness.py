"""Source-owned machine-code probes verify that ABI failures are detected."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]/'tools'))
from verify_helper_behavior import execute


class HelperHarnessTests(unittest.TestCase):
    def test_noop_preserves_null_constructor_contract(self):
        # Source-owned Thumb bx lr; no retail instruction bytes.
        result = execute(bytes.fromhex('7047'), count=3, stride=4, null_constructor=True)
        self.assertEqual(result['calls'], [])

    def test_missing_callbacks_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Callback order/count'):
            execute(bytes.fromhex('7047'), count=1, stride=4)

    def test_wrong_return_is_rejected(self):
        # movs r0, #0; bx lr
        with self.assertRaisesRegex(ValueError, 'returned array'):
            execute(bytes.fromhex('00207047'), count=0, stride=4)

    def test_callee_saved_register_corruption_is_rejected(self):
        # movs r4, #0; bx lr
        with self.assertRaisesRegex(ValueError, 'Callee-saved'):
            execute(bytes.fromhex('00247047'), count=0, stride=4)

    def test_unexpected_array_write_is_rejected(self):
        # str r0, [r0]; bx lr
        with self.assertRaisesRegex(ValueError, 'outside its stack'):
            execute(bytes.fromhex('00607047'), count=0, stride=4)


if __name__ == '__main__':
    unittest.main()
