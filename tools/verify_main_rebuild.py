"""Verify main-image objects, section addresses, PT_LOADs and full raw bytes.

Reads ELF and exheader fields independently of the external pipeline.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from verify_rebuild import elf_sections


def verify(code_path, exheader_path, root):
    code, header = Path(code_path).read_bytes(), Path(exheader_path).read_bytes()
    code_hash = hashlib.sha256(code).hexdigest()
    header_hash = hashlib.sha256(header).hexdigest()
    if code_hash != 'b5388f7500d91be01499a99ca007c98212068608ed7c83c43952e1d5148e9e09' or header_hash != 'e4682ebab1bef10bdede38589b18c98f6976b1ebdc6a3b2540757aedcfe141e2':
        raise ValueError('Original input identity differs')
    root = Path(root)
    plan = json.loads((root/'layout.json').read_text())
    expected, cursor = {}, 0
    for name, offset, flags in (('.text', 0x10, 6), ('.rodata', 0x20, 2), ('.data', 0x30, 3)):
        address, pages, logical = struct.unpack_from('<III', header, offset)
        size = pages*0x1000
        expected[name] = {'address': address, 'offset': cursor, 'size': size, 'logical_size': logical,
                          'flags': flags, 'bytes': code[cursor:cursor+size]}
        cursor += size
    if cursor != len(code):
        raise ValueError('Input extent differs from page allocation')
    object_paths, position, receipts = set(), 0, []
    for obj in plan['objects']:
        if obj['offset'] != position or obj['size'] <= 0:
            raise ValueError('Object coverage has gaps, overlaps, or invalid sizes')
        segment = expected[obj['section']]
        if not segment['offset'] <= position < position+obj['size'] <= segment['offset']+segment['size']:
            raise ValueError('Object crosses an initialized region')
        path = root/'split/code.bin'/(obj['name']+'.o')
        if path in object_paths:
            raise ValueError('Object selected more than once')
        object_paths.add(path)
        sections = elf_sections(path.read_bytes())
        if set(sections) != {obj['section']} or sections[obj['section']]['bytes'] != code[position:position+obj['size']]:
            raise ValueError('Selected split object differs from original range')
        receipts.append({'name': obj['name'], 'offset': position, 'size': obj['size'],
                         'section': obj['section'], 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        position += obj['size']
    if position != len(code) or object_paths != set((root/'split/code.bin').glob('*.o')):
        raise ValueError('Split objects do not cover the full input exactly once')
    selected_names = [o['name']+'.o' for o in plan['objects']]
    response = (root/'out/code.bin.txt').read_text().splitlines()
    if [Path(line.strip('"')).name for line in response] != selected_names:
        raise ValueError('Linker response file object selection differs')
    map_text = (root/'out/code.bin_linked.map').read_text()
    loaded_names = [Path(p).name for p in re.findall(r'^LOAD (.*\.o)$', map_text, re.MULTILINE)]
    if loaded_names != selected_names:
        raise ValueError('Linker map object selection differs')
    elf = (root/'out/code.bin_linked').read_bytes()
    sections = elf_sections(elf)
    if set(sections) != set(expected):
        raise ValueError('Linked initialized sections differ')
    for name, want in expected.items():
        got = sections[name]
        if got['address'] != want['address'] or got['flags'] != want['flags'] or got['bytes'] != want['bytes']:
            raise ValueError(f'Linked {name} bytes, address or permissions differ')
    fields = struct.unpack_from('<16sHHIIIIIHHHHHH', elf)
    phoff, phsize, phcount = fields[5], fields[9], fields[10]
    if fields[1] != 2 or fields[4] != expected['.text']['address'] or phsize != 32 or phcount != 3 or phoff+phcount*phsize > len(elf):
        raise ValueError('Linked ELF entry or program headers differ')
    loads = [struct.unpack_from('<8I', elf, phoff+i*phsize) for i in range(phcount)]
    for load, want, flags in zip(loads, expected.values(), (5, 4, 6)):
        kind, offset, virtual, physical, file_size, memory_size, actual_flags, alignment = load
        if (kind, virtual, physical, file_size, memory_size, actual_flags) != (1, want['address'], want['address'], want['size'], want['size'], flags):
            raise ValueError('Linked PT_LOAD mapping differs')
        if offset+file_size > len(elf) or elf[offset:offset+file_size] != want['bytes']:
            raise ValueError('Linked PT_LOAD payload differs')
        if alignment <= 0 or alignment & (alignment-1) or virtual % alignment != offset % alignment:
            raise ValueError('Invalid PT_LOAD alignment')
    rebuilt = (root/'out/code.bin').read_bytes()
    if rebuilt != code:
        raise ValueError('Reconstructed code.bin differs from original')
    return {'exact_match': True, 'original_bytes_verified': len(code), 'sha256': code_hash,
            'exheader_sha256': header_hash, 'split_objects_verified': len(object_paths),
            'initialized_sections_verified': 3, 'load_mappings_verified': 3,
            'selected_object_receipts': receipts,
            'source_replacements': 0, 'bss_size': struct.unpack_from('<I', header, 0x3c)[0],
            'scope': 'Unchanged initialized image; original bytes retained; BSS and game execution not rebuilt.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('code')
    parser.add_argument('exheader')
    parser.add_argument('run_directory')
    args = parser.parse_args()
    print(json.dumps(verify(args.code, args.exheader, args.run_directory), indent=2))
