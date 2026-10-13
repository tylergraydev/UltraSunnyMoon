"""Regression checks for CRO named-import resolution on synthetic, non-retail modules."""
import importlib.util
from pathlib import Path
import struct
import unittest

module_spec = importlib.util.spec_from_file_location("resolve_cro_imports", Path(__file__).parents[1] / "tools/resolve_cro_imports.py")
resolver = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(resolver)


def strings_table(strings):
    """Return (blob, offsets) with each string NUL-terminated."""
    blob, offsets = b"", []
    for text in strings:
        offsets.append(len(blob))
        blob += text.encode() + b"\0"
    return blob, offsets


def build_crs(exports):
    """A static-style module: absolute segment addresses and named exports."""
    header_size = 0x138
    segments = [(0x100000, 0x1000, 0), (0x200000, 0x100, 2)]
    table_at = header_size
    exports_at = table_at + 12*len(segments)
    names, offsets = strings_table([name for name, _, _ in exports])
    strings_at = exports_at + 8*len(exports)
    size = strings_at + len(names)
    data = bytearray(size)
    data[0x80:0x84] = b"CRO0"
    struct.pack_into("<II", data, 0x90, size, 0)
    struct.pack_into("<II", data, 0xC8, table_at, len(segments))
    struct.pack_into("<II", data, 0xD0, exports_at, len(exports))
    for index, (addr, seg_size, kind) in enumerate(segments):
        struct.pack_into("<III", data, table_at+index*12, addr, seg_size, kind)
    for index, (name, segment, offset) in enumerate(exports):
        struct.pack_into("<II", data, exports_at+index*8, strings_at+offsets[index], (offset << 4) | segment)
    data[strings_at:] = names
    return bytes(data)


def build_cro(imports, relocations, text_size=0x40, data_size=0x10):
    """A CRO with one text and one data segment and a relocation table of the given records.

    imports: list of (name, first record index). relocations: list of
    (segment, offset, type, is_batch_end, addend) tuples.
    """
    header_size = 0x138
    segment_table = header_size
    relocation_table = segment_table + 12*2
    named_table = relocation_table + 12*len(relocations)
    string_blob, string_offsets = strings_table([name for name, _ in imports])
    strings_at = named_table + 8*len(imports)
    text_at = strings_at + len(string_blob)
    text_at = (text_at + 3) & ~3
    data_at = text_at + text_size
    size = data_at + data_size
    data = bytearray(size)
    data[0x80:0x84] = b"CRO0"
    struct.pack_into("<II", data, 0x90, size, 0)
    struct.pack_into("<II", data, 0xC8, segment_table, 2)
    struct.pack_into("<II", data, 0xF8, relocation_table, len(relocations))
    struct.pack_into("<II", data, 0x100, named_table, len(imports))
    struct.pack_into("<II", data, 0x118, strings_at, len(string_blob))
    struct.pack_into("<III", data, segment_table, text_at, text_size, 0)
    struct.pack_into("<III", data, segment_table+12, data_at, data_size, 2)
    for index, (segment, offset, kind, end, addend) in enumerate(relocations):
        tag = (offset << 4) | segment
        struct.pack_into("<IBBBBI", data, relocation_table+index*12, tag, kind, end, 0, 0, addend)
    for index, (name, first) in enumerate(imports):
        struct.pack_into("<II", data, named_table+index*8, strings_at+string_offsets[index],
                         relocation_table+first*12)
    data[strings_at:strings_at+len(string_blob)] = string_blob
    return bytes(data)


CRS = build_crs([
    ("plain_function", 0, 0x20),
    ("thumb_function", 0, 0x51),
    ("state_object", 1, 0x8),
])


class ResolveTests(unittest.TestCase):
    def resolve(self, cro):
        exports = resolver.crs_exports(resolver.parse(CRS))
        module = resolver.parse(cro)
        return resolver.resolve(module, resolver.parse(CRS), exports)

    def test_single_record_import_is_resolved_to_absolute_address(self):
        cro = build_cro([("plain_function", 0)], [(0, 0x4, 2, 1, 8)])
        text_at = struct.unpack_from("<I", cro, 0x138)[0]
        imports, uncovered = self.resolve(cro)
        entry = imports[0]
        self.assertEqual(uncovered, 0)
        self.assertEqual(entry["status"], "resolved")
        self.assertEqual(entry["symbol_address"], 0x100020)
        self.assertFalse(entry["thumb"])
        relocation = entry["relocations"][0]
        self.assertEqual(relocation["patch_file_offset"], text_at+0x4)
        self.assertEqual(relocation["expected_word"], 0x100020+8)

    def test_thumb_bit_is_kept_for_text_exports(self):
        cro = build_cro([("thumb_function", 0)], [(0, 0x0, 2, 1, 0)])
        imports, _ = self.resolve(cro)
        self.assertTrue(imports[0]["thumb"])
        self.assertEqual(imports[0]["relocations"][0]["expected_word"], 0x100051)

    def test_multi_record_batch_runs_until_batch_end(self):
        cro = build_cro([("state_object", 0)], [(0, 0x0, 2, 0, 0), (1, 0x4, 2, 1, 4)])
        imports, uncovered = self.resolve(cro)
        self.assertEqual(uncovered, 0)
        self.assertEqual([r["segment"] for r in imports[0]["relocations"]], [0, 1])
        self.assertEqual(imports[0]["relocations"][1]["expected_word"], 0x200008+4)

    def test_unexported_name_is_reported_unresolved(self):
        cro = build_cro([("missing_symbol", 0)], [(0, 0x0, 2, 1, 0)])
        imports, _ = self.resolve(cro)
        self.assertEqual(imports[0]["status"], "unresolved")
        self.assertNotIn("expected_word", imports[0]["relocations"][0])

    def test_records_outside_named_batches_are_counted(self):
        cro = build_cro([("plain_function", 0)], [(0, 0x0, 2, 1, 0), (0, 0x4, 2, 1, 0)])
        _, uncovered = self.resolve(cro)
        self.assertEqual(uncovered, 1)

    def test_unsupported_relocation_type_is_rejected(self):
        cro = build_cro([("plain_function", 0)], [(0, 0x0, 3, 1, 0)])
        with self.assertRaises(resolver.ModuleFormatError):
            self.resolve(cro)

    def test_patch_outside_its_segment_is_rejected(self):
        cro = build_cro([("plain_function", 0)], [(0, 0x40, 2, 1, 0)])
        with self.assertRaises(resolver.ModuleFormatError):
            self.resolve(cro)

    def test_batch_running_past_table_is_rejected(self):
        cro = build_cro([("plain_function", 0)], [(0, 0x0, 2, 0, 0)])
        with self.assertRaises(resolver.ModuleFormatError):
            self.resolve(cro)

    def test_duplicate_static_export_is_rejected(self):
        duplicate = build_crs([("same", 0, 0x0), ("same", 0, 0x4)])
        with self.assertRaises(resolver.ModuleFormatError):
            resolver.crs_exports(resolver.parse(duplicate))

    def test_export_offset_outside_static_segment_is_rejected(self):
        bad = build_crs([("beyond", 1, 0x200)])
        exports = resolver.crs_exports(resolver.parse(bad))
        with self.assertRaises(resolver.ModuleFormatError):
            resolver.symbol_address(resolver.parse(bad), *exports["beyond"])

    def test_wrong_magic_is_rejected(self):
        cro = bytearray(build_cro([("plain_function", 0)], [(0, 0x0, 2, 1, 0)]))
        cro[0x80:0x84] = b"CRS0"
        with self.assertRaises(resolver.ModuleFormatError):
            resolver.parse(bytes(cro))


if __name__ == "__main__":
    unittest.main()
