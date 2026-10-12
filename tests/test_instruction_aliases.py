"""Regression checks for equivalent assembler spellings encountered in modules."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
from verify_function import canonical


class InstructionAliasTests(unittest.TestCase):
    def test_shift_immediates_and_unsigned_condition_aliases(self):
        self.assertEqual(canonical('ldrlo','pc, [pc, r1, lsl #2]'),
                         canonical('ldrcc','pc, [pc,r1,lsl #0x2]'))

    def test_memory_zero_displacement_does_not_change_post_indexing(self):
        self.assertEqual(canonical('str','r0, [r2]'),canonical('str','r0, [r2,#0x0]'))
        self.assertNotEqual(canonical('str','r0, [r2],#4'),canonical('str','r0, [r2,#4]'))


if __name__ == '__main__':
    unittest.main()
