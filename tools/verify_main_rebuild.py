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
    replacement = plan.get('replacement')
    expected_image = bytearray(code)
    replacements = {}
    bss = plan.get('bss_replacement')
    if bss:
        from bss_selection import validate
        payload = validate((root/'build/startup_zero_helper.o').read_bytes(), bss, code, header)
        expected_image[0x24:0x48] = payload
        replacements['startup_zero_helper'] = (0x24, 36, bss)
    if replacement:
        from compile_helper import standalone_helper
        object_data = (root/'build/aeabi_vec_ctor.o').read_bytes()
        payload = standalone_helper(object_data)
        if len(payload) != 34 or hashlib.sha256(object_data).hexdigest() != replacement['object_sha256']:
            raise ValueError('Compiled replacement object differs from its receipt')
        if replacement['source_sha256'] != hashlib.sha256(Path('src/runtime/aeabi_vec_ctor.c').read_bytes()).hexdigest():
            raise ValueError('Compiled replacement source receipt differs')
        behavior = replacement['behavior']
        if behavior['code_sha256'] != code_hash or behavior['object_sha256'] != replacement['object_sha256'] or behavior['cases_passed'] != 8 or len(behavior['cases']) != 8 or behavior.get('cpu_model') != 'ARM11 MPCore' or not all(c['passed'] for c in behavior['cases']):
            raise ValueError('Compiled replacement behavior receipt differs')
        if replacement['policy'] == 'exact' and payload != code[0x50:0x72]:
            raise ValueError('Exact replacement differs from original')
        if replacement['policy'] not in ('exact', 'behavior-tested-nonmatching'):
            raise ValueError('Unsupported replacement policy')
        expected_image[0x50:0x72] = payload
        replacements['aeabi_vec_ctor'] = (0x50, 34, replacement)
    if plan['source_replacements'] != len(replacements):
        raise ValueError('Replacement count differs')
    expected, cursor = {}, 0
    for name, offset, flags in (('.text', 0x10, 6), ('.rodata', 0x20, 2), ('.data', 0x30, 3)):
        address, pages, logical = struct.unpack_from('<III', header, offset)
        size = pages*0x1000
        expected[name] = {'address': address, 'offset': cursor, 'size': size, 'logical_size': logical,
                          'flags': flags, 'bytes': bytes(expected_image[cursor:cursor+size])}
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
        selected = replacements.get(obj['name'])
        if selected and (obj['offset'], obj['size'], obj['section']) != (selected[0], selected[1], '.text'):
            raise ValueError('Replacement range differs')
        receipts.append({'name': obj['name'], 'offset': position, 'size': obj['size'],
                         'section': obj['section'], 'origin': 'compiled-source' if selected else 'original-split',
                         'sha256': selected[2]['object_sha256'] if selected else hashlib.sha256(path.read_bytes()).hexdigest()})
        position += obj['size']
    if position != len(code) or object_paths != set((root/'split/code.bin').glob('*.o')):
        raise ValueError('Split objects do not cover the full input exactly once')
    selected_names = [o['name']+'.o' for o in plan['objects']]
    response = (root/'out/code.bin.txt').read_text().splitlines()
    if [Path(line.strip('"')).name for line in response] != selected_names:
        raise ValueError('Linker response file object selection differs')
    helper_line = response[selected_names.index('aeabi_vec_ctor.o')].strip('"').replace('\\', '/')
    helper_directory = 'build' if replacement else 'split/code.bin'
    if not helper_line.endswith('/'+helper_directory+'/aeabi_vec_ctor.o'):
        raise ValueError('Compiled helper selection fell back to another object')
    map_text = (root/'out/code.bin_linked.map').read_text()
    loaded_names = [Path(p).name for p in re.findall(r'^LOAD (.*\.o)$', map_text, re.MULTILINE)]
    if loaded_names != selected_names:
        raise ValueError('Linker map object selection differs')
    for obj, line, load in zip(plan['objects'], response, re.findall(r'^LOAD (.*\.o)$', map_text, re.MULTILINE)):
        directory = 'build' if obj['name'] in replacements else 'split/code.bin'
        suffix = '/'+directory+'/'+obj['name']+'.o'
        if not all(p.strip('"').replace('\\', '/').endswith(suffix) for p in (line, load)):
            raise ValueError('Linker selected an unexpected object path')
    for name in replacements:
        if name+'.o' not in selected_names:
            raise ValueError('Selected replacement missing from layout')
    selected_helper_loads = [line.replace('\\', '/') for line in map_text.splitlines()
                            if line.startswith('LOAD ') and line.endswith('/aeabi_vec_ctor.o')]
    if len(selected_helper_loads) != 1 or not selected_helper_loads[0].endswith('/'+helper_directory+'/aeabi_vec_ctor.o'):
        raise ValueError('Linker map helper selection differs')
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
    if rebuilt != expected_image:
        raise ValueError('Reconstructed code.bin differs from selected image')
    return {'verification_passed': True, 'exact_match': rebuilt == code,
            'original_bytes_verified': len(code)-sum(r[1] for r in replacements.values()),
            'sha256': hashlib.sha256(rebuilt).hexdigest(), 'original_sha256': code_hash,
            'exheader_sha256': header_hash, 'split_objects_verified': len(object_paths),
            'initialized_sections_verified': 3, 'load_mappings_verified': 3,
            'selected_object_receipts': receipts,
            'source_replacements': len(replacements),
            'replacement_policies': {n: r[2]['policy'] for n, r in replacements.items()},
            'replacement_policy': ('behavior-tested-nonmatching' if any(r[2]['policy'] == 'behavior-tested-nonmatching' for r in replacements.values()) else 'exact') if replacements else None,
            'changed_bytes': sum(a != b for a, b in zip(code, rebuilt)),
            'bss_size': struct.unpack_from('<I', header, 0x3c)[0],
            'scope': 'Initialized image with explicit original/compiled object selection; behavior requires separate execution checks; game execution unverified.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('code')
    parser.add_argument('exheader')
    parser.add_argument('run_directory')
    args = parser.parse_args()
    print(json.dumps(verify(args.code, args.exheader, args.run_directory), indent=2))
