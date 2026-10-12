"""Structural regression checks on synthetic, non-retail inputs."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

module_spec = importlib.util.spec_from_file_location("wrap_code", Path(__file__).parents[1] / "tools/wrap_code.py")
wrapper = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(wrapper)


class ElfMappingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.code = self.root / "code.bin"
        self.exheader = self.root / "exheader.bin"
        self.output = self.root / "analysis.elf"
        self.bytes = bytes(range(256)) * 48
        self.code.write_bytes(self.bytes)
        header = bytearray(0x40)
        for offset, address in ((0x10, 0x100000), (0x20, 0x200000), (0x30, 0x300000)):
            struct.pack_into("<III", header, offset, address, 1, 0xF00)
        struct.pack_into("<I", header, 0x3C, 0x1234)
        self.header = header
        self.exheader.write_bytes(header)

    def test_mapped_segments_preserve_every_input_byte_with_address_gaps(self):
        report = wrapper.build(self.code, self.exheader, self.output)
        elf = self.output.read_bytes()
        self.assertEqual(elf[0x1000:], self.bytes)
        for index, address in enumerate((0x100000, 0x200000, 0x300000)):
            segment = struct.unpack_from("<IIIIIIII", elf, 52 + index*32)
            self.assertEqual(segment[2], address)
            self.assertEqual(elf[segment[1]:segment[1]+segment[4]], self.bytes[index*0x1000:(index+1)*0x1000])
        self.assertTrue(report["source_bytes_preserved"])
        self.assertEqual(self.code.read_bytes(), self.bytes)

    def test_rejects_compressed_and_truncated_inputs_without_output(self):
        self.header[0xD] = 1
        self.exheader.write_bytes(self.header)
        with self.assertRaises(ValueError):
            wrapper.build(self.code, self.exheader, self.output)
        self.assertFalse(self.output.exists())
        self.header[0xD] = 0
        self.exheader.write_bytes(self.header)
        self.code.write_bytes(self.bytes[:-1])
        with self.assertRaises(ValueError):
            wrapper.build(self.code, self.exheader, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_overlapping_memory_segments(self):
        struct.pack_into("<III", self.header, 0x20, 0x100000, 1, 0xF00)
        self.exheader.write_bytes(self.header)
        with self.assertRaises(ValueError):
            wrapper.build(self.code, self.exheader, self.output)

    def test_bounded_text_does_not_claim_unmapped_code_coverage(self):
        report = wrapper.build(self.code, self.exheader, self.output, text_limit=0x48)
        segment = struct.unpack_from("<IIIIIIII", self.output.read_bytes(), 52)
        self.assertEqual(segment[4:6], (0x48, 0x48))
        self.assertEqual(report["text_limit"], 0x48)
        self.assertIn("bounded", report["coverage"])
        self.assertEqual(self.code.read_bytes(), self.bytes)


if __name__ == "__main__":
    unittest.main()
