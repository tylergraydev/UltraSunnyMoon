"""Independently verify the unchanged AnaiTest split/link/CRO rebuild."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def elf_sections(data):
    if data[:7] != b'\x7fELF\x01\x01\x01' or len(data) < 52:
        raise ValueError('Expected ELF32 little-endian image')
    fields = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    if fields[2] != 40:
        raise ValueError('Expected ARM ELF')
    offset, entry_size, count, string_index = fields[6], fields[11], fields[12], fields[13]
    if entry_size != 40 or string_index >= count or offset+count*40 > len(data):
        raise ValueError('Invalid ELF section table')
    sections = [struct.unpack_from('<10I', data, offset+i*40) for i in range(count)]
    names_section = sections[string_index]
    names = data[names_section[4]:names_section[4]+names_section[5]]
    selected = {}
    for section in sections:
        name = names[section[0]:].split(b'\0', 1)[0]
        if name in (b'.text', b'.rodata', b'.data'):
            start, size = section[4:6]
            if section[1] != 1 or start+size > len(data) or name.decode() in selected:
                raise ValueError('Invalid or duplicated initialized section')
            selected[name.decode()] = {'address': section[3], 'flags': section[2],
                                       'bytes': data[start:start+size]}
    return selected


def elf_text(data):
    selected = elf_sections(data)
    if '.text' not in selected or any(s['bytes'] for n, s in selected.items() if n != '.text'):
        raise ValueError('Expected .text without additional initialized payloads')
    return selected['.text']['bytes']


def verify(module, root):
    original = Path(module).read_bytes()
    root = Path(root)
    name = Path(module).name
    rebuilt = (root / 'out' / name).read_bytes()
    if rebuilt != original:
        raise ValueError('Reconstructed CRO differs from original')
    text_off, text_size = struct.unpack_from('<II', original, 0xb0)
    data_off, data_size = struct.unpack_from('<II', original, 0xb8)
    module_off = struct.unpack_from('<I', original, 0xc0)[0]
    expected = original[text_off:text_off+text_size]+original[data_off:data_off+data_size]
    parts = [('control_head', 0, 0x14), ('switch_table', 0x14, 0x14),
             ('control_tail', 0x28, 0x60), ('literal_pool', 0x88, 0x24),
             ('text_padding', 0xac, text_size-0xac), ('original_data', text_size, data_size)]
    for label, offset, size in parts:
        if elf_text((root / 'split' / name / (label+'.o')).read_bytes()) != expected[offset:offset+size]:
            raise ValueError(f'Split object differs: {label}')
    linked = elf_text((root / 'out' / (name+'_linked')).read_bytes())
    if linked != expected or (root / 'out' / 'linked-payload.bin').read_bytes() != expected:
        raise ValueError('Linked ELF/raw payload differs from original')
    bounds = [(0x80, text_off), (text_off, module_off), (module_off, data_off),
              (data_off, data_off+data_size)]
    for index, (start, end) in enumerate(bounds):
        if not 0x80 <= start <= end <= len(rebuilt):
            raise ValueError('Invalid CRO hash region')
        if hashlib.sha256(rebuilt[start:end]).digest() != rebuilt[index*32:index*32+32]:
            raise ValueError(f'CRO hash mismatch: {index}')
    return {'exact_match': True, 'size': len(rebuilt), 'split_objects_verified': len(parts),
            'linked_payload_size': len(linked), 'cro_hash_regions_verified': 4,
            'sha256': hashlib.sha256(rebuilt).hexdigest(), 'source_replacements': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module')
    parser.add_argument('run_directory')
    args = parser.parse_args()
    print(json.dumps(verify(args.module, args.run_directory), indent=2))
