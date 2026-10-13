"""Resolve CRO named imports against static.crs using independently parsed raw records.

Each named import points at a relocation batch in the CRO's import relocation table.
Batches run until an entry with is_batch_end set. Symbols are looked up by exact name
in the named export table of static.crs, the module that carries main-image exports.
Only absolute relocations are supported. Indexed/anonymous imports share the relocation
table; their records are counted as outside named batches and not verified here. Names
not exported by static.crs are reported, not guessed. Nothing is patched in place.

Layout follows Azahar's ldr_ro CRO helper (GPLv2+ reference, read for semantics only):
  header: magic 0x80, cro_size 0x90, bss 0x94, segments 0xC8, named exports 0xD0,
          import modules 0xF0, import relocations 0xF8, named imports 0x100,
          indexed imports 0x108, anon imports 0x110, import strings 0x118, internal 0x128
  relocation record (12 bytes): u32 segment tag, u8 type, u8 is_batch_end,
          u8 is_batch_resolved, pad, u32 addend
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ABSOLUTE_TYPES = {2, 38}
FILE_BACKED = {0: 'TEXT', 1: 'RODATA', 2: 'DATA'}
RECORD = 12


class ModuleFormatError(ValueError):
    pass


def cstring(data, offset, limit):
    if not limit <= len(data) or not offset < limit:
        raise ModuleFormatError('string offset outside its table')
    end = data.find(b'\0', offset, limit)
    if end < 0:
        raise ModuleFormatError('unterminated string')
    return data[offset:end].decode('utf-8')


def parse(data):
    if len(data) < 0x138 or data[0x80:0x84] != b'CRO0':
        raise ModuleFormatError('not a CRO0 module')
    cro_size, bss_size = struct.unpack_from('<II', data, 0x90)
    if cro_size != len(data):
        raise ModuleFormatError('declared size differs from file size')
    table = lambda at: struct.unpack_from('<II', data, at)
    segments = []
    seg_off, seg_count = table(0xC8)
    for index in range(seg_count):
        addr, size, kind = struct.unpack_from('<III', data, seg_off+index*12)
        segments.append({'index': index, 'addr': addr, 'size': size, 'type': kind})
    return {'data': data, 'size': cro_size, 'bss': bss_size, 'segments': segments,
            'named_exports': table(0xD0), 'import_modules': table(0xF0),
            'import_relocations': table(0xF8), 'named_imports': table(0x100),
            'indexed_imports': table(0x108), 'anon_imports': table(0x110),
            'import_strings': table(0x118), 'internal_relocs': table(0x128)}


def record_table(module, key, size):
    offset, count = module[key]
    if offset+count*size > module['size']:
        raise ModuleFormatError(f'{key} leaves the module')
    return offset, count


def crs_exports(crs):
    """Map exported name to (segment index, segment-relative offset); duplicates are fatal."""
    data = crs['data']
    offset, count = record_table(crs, 'named_exports', 8)
    exports = {}
    for index in range(count):
        name_off, encoded = struct.unpack_from('<II', data, offset+index*8)
        name = cstring(data, name_off, len(data))
        if name in exports:
            raise ModuleFormatError('duplicate static export name')
        exports[name] = (encoded & 0xF, encoded >> 4)
    return exports


def symbol_address(crs, segment_index, offset):
    if segment_index >= len(crs['segments']):
        raise ModuleFormatError('export segment index out of range')
    segment = crs['segments'][segment_index]
    if offset >= segment['size']:
        raise ModuleFormatError('export offset outside its segment')
    return segment['addr']+offset


def batches(module):
    """Split the import relocation table into named-import batches, checking coverage."""
    data = module['data']
    rel_off, rel_count = record_table(module, 'import_relocations', RECORD)
    named_off, named_count = record_table(module, 'named_imports', 8)
    result, covered = [], set()
    for index in range(named_count):
        name_off, batch_off = struct.unpack_from('<II', data, named_off+index*8)
        if not (rel_off <= batch_off < rel_off+rel_count*RECORD) or (batch_off-rel_off) % RECORD:
            raise ModuleFormatError('batch offset is not a relocation record')
        name = cstring(data, name_off, len(data))
        records = []
        position = batch_off
        while True:
            if position >= rel_off+rel_count*RECORD:
                raise ModuleFormatError('batch runs past the relocation table')
            slot = (position-rel_off)//RECORD
            if slot in covered:
                raise ModuleFormatError('relocation record belongs to two batches')
            covered.add(slot)
            tag, kind, end, resolved, _, addend = struct.unpack_from('<IBBBBI', data, position)
            records.append({'tag': tag, 'segment': tag & 0xF, 'offset': tag >> 4, 'type': kind,
                            'addend': addend, 'is_batch_resolved': resolved})
            if end:
                break
            position += RECORD
        result.append({'name': name, 'name_offset': name_off, 'batch_offset': batch_off,
                       'relocations': records})
    return result, rel_count-len(covered)


def resolve(module, crs, exports):
    """Attach static.crs targets and expected words; fail on unsupported relocation types."""
    names = []
    patch_slots = set()
    named, uncovered = batches(module)
    for batch in named:
        status = 'resolved' if batch['name'] in exports else 'unresolved'
        entry = {'name': batch['name'], 'name_offset': batch['name_offset'],
                 'batch_offset': batch['batch_offset'], 'status': status, 'relocations': []}
        if status == 'resolved':
            segment_index, offset = exports[batch['name']]
            address = symbol_address(crs, segment_index, offset)
            entry |= {'static_segment': segment_index, 'static_offset': offset,
                      'symbol_address': address, 'thumb': bool(address & 1) and crs['segments'][segment_index]['type'] == 0}
        for rel in batch['relocations']:
            if rel['type'] not in ABSOLUTE_TYPES:
                raise ModuleFormatError(f'unsupported import relocation type {rel["type"]}')
            if rel['segment'] not in FILE_BACKED or rel['segment'] >= len(module['segments']):
                raise ModuleFormatError('import patch lies outside a file-backed segment')
            segment = module['segments'][rel['segment']]
            if rel['offset']+4 > segment['size']:
                raise ModuleFormatError('import patch leaves its segment')
            file_offset = segment['addr']+rel['offset']
            if file_offset+4 > module['size']:
                raise ModuleFormatError('import patch leaves the module file')
            if file_offset in patch_slots:
                raise ModuleFormatError('two imports patch the same word')
            patch_slots.add(file_offset)
            original = struct.unpack_from('<I', module['data'], file_offset)[0]
            item = dict(rel, patch_file_offset=file_offset, original_word=original)
            if status == 'resolved':
                item['expected_word'] = (address+rel['addend']) & 0xFFFFFFFF
            entry['relocations'].append(item)
        names.append(entry)
    return names, uncovered


def check_module(path, crs, exports):
    raw = Path(path).read_bytes()
    module = parse(raw)
    imports, uncovered = resolve(module, crs, exports)
    kinds = {}
    for entry in imports:
        for rel in entry['relocations']:
            kinds[rel['type']] = kinds.get(rel['type'], 0)+1
    return {'name': Path(path).name, 'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw),
            'bss_size': module['bss'], 'named_imports': len(imports),
            'batches_multi_record': sum(1 for e in imports if len(e['relocations']) > 1),
            'import_relocations': module['import_relocations'][1],
            'relocations_outside_named_batches': uncovered,
            'resolved': sum(1 for e in imports if e['status'] == 'resolved'),
            'unresolved_names': sorted(e['name'] for e in imports if e['status'] == 'unresolved'),
            'relocation_types': {str(k): v for k, v in sorted(kinds.items())},
            'module_imports': module['import_modules'][1],
            'indexed_imports': module['indexed_imports'][1], 'anon_imports': module['anon_imports'][1],
            'imports': imports}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('crs')
    parser.add_argument('output')
    parser.add_argument('modules', nargs='+')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.relative_to((Path.cwd()/'analysis'/'private').resolve())
    output.mkdir(parents=True, exist_ok=False)
    crs_raw = Path(args.crs).read_bytes()
    crs = parse(crs_raw)
    exports = crs_exports(crs)
    reports = [check_module(path, crs, exports) for path in args.modules]
    summary = {'static_crs_sha256': hashlib.sha256(crs_raw).hexdigest(), 'static_named_exports': len(exports),
               'modules': [{k: v for k, v in r.items() if k != 'imports'} for r in reports]}
    (output/'resolution.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    for report in reports:
        (output/(report['name']+'.imports.json')).write_text(json.dumps(report['imports'], indent=2), encoding='utf-8')
    print(json.dumps({'modules': len(reports), 'output': str(output/'resolution.json')}))


if __name__ == '__main__':
    sys.exit(main())
