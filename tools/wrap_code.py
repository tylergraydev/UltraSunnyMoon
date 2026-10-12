"""Wrap decompressed 3DS ExeFS code in an analysis-only ELF32 ARM image.

Retail bytes remain external. This is not a runnable game or a matching build.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def build(code_path, exheader_path, output_path, text_limit=None):
    code = Path(code_path).read_bytes()
    exheader = Path(exheader_path).read_bytes()
    if len(exheader) < 0x40:
        raise ValueError("Exheader is too short")
    if exheader[0xD] & 1:
        raise ValueError("Compressed code is unsupported; decompress before wrapping")
    descriptions = [struct.unpack_from("<III", exheader, offset)
                    for offset in (0x10, 0x20, 0x30)]
    bss_size = struct.unpack_from("<I", exheader, 0x3C)[0]
    if len(code) != sum(pages * 0x1000 for _, pages, _ in descriptions):
        raise ValueError("Code size does not equal the exheader page allocation")
    for address, pages, size in descriptions:
        if address % 0x1000 or size > pages * 0x1000:
            raise ValueError("Invalid segment allocation")
    for previous, following in zip(descriptions, descriptions[1:]):
        if previous[0] + previous[1] * 0x1000 > following[0]:
            raise ValueError("Overlapping segments")
    if text_limit is not None and (text_limit <= 0 or text_limit % 4 or text_limit > descriptions[0][2]):
        raise ValueError("Text limit must be aligned, positive, and within the text segment")
    ident = b"\x7fELF" + bytes([1, 1, 1, 0]) + bytes(8)
    # ET_EXEC, EM_ARM, EABI5. Segment allocation comes directly from exheader.
    header = struct.pack("<16sHHIIIIIHHHHHH", ident, 2, 40, 1,
                         descriptions[0][0], 52, 0, 0x05000000,
                         52, 32, 3, 0, 0, 0)
    headers = []
    segments = []
    cursor = 0
    for index, ((address, pages, size), flags) in enumerate(zip(descriptions, (5, 4, 6))):
        allocated = pages * 0x1000
        memory_size = allocated + (bss_size if index == 2 else 0)
        mapped_size = allocated
        if index == 0 and text_limit is not None:
            mapped_size = memory_size = text_limit
        headers.append(struct.pack("<IIIIIIII", 1, 0x1000 + cursor, address,
                                   address, mapped_size, memory_size, flags, 0x1000))
        segments.append({"name": ("text", "ro", "data")[index],
                         "address": hex(address), "code_offset": hex(cursor),
                         "logical_size": size, "file_size": mapped_size,
                         "memory_size": memory_size, "flags": flags})
        cursor += allocated
    output = header + b"".join(headers)
    output += bytes(0x1000 - len(output)) + code
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(output)
    # Verify that every mapped byte is the original byte at its declared address.
    for segment in segments:
        offset = int(segment["code_offset"], 16)
        size = segment["file_size"]
        if output[0x1000 + offset:0x1000 + offset + size] != code[offset:offset + size]:
            raise ValueError("ELF mapping verification failed")
    return {"kind": "analysis-only-elf", "text_limit": text_limit,
            "coverage": "full initialized image" if text_limit is None else "bounded text view; other text is not mapped",
            "code_sha256": hashlib.sha256(code).hexdigest(),
            "exheader_sha256": hashlib.sha256(exheader).hexdigest(),
            "elf_sha256": hashlib.sha256(output).hexdigest(),
            "entry": hex(descriptions[0][0]), "bss_size": bss_size,
            "segments": segments, "source_bytes_preserved": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code")
    parser.add_argument("exheader")
    parser.add_argument("output")
    parser.add_argument("--text-limit", type=lambda value: int(value, 0), help="Bound text mapping for focused analysis; does not claim whole-image coverage")
    args = parser.parse_args()
    print(json.dumps(build(args.code, args.exheader, args.output, args.text_limit), indent=2))
