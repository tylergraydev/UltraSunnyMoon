"""Verify module relocation changes against independently parsed raw records."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def verify(source, elf_path):
    original = Path(source).read_bytes()
    elf = Path(elf_path).read_bytes()
    relocated = elf[0x1000:]
    report = json.loads(Path(elf_path).with_suffix('.json').read_text())
    if hashlib.sha256(original).hexdigest() != report['source_sha256'] or hashlib.sha256(elf).hexdigest() != report['elf_sha256']:
        raise ValueError('Source/view digest differs')
    base = int(report['synthetic_base'],16)
    table, count = struct.unpack_from('<II', original, 0xC8)
    segments = [struct.unpack_from('<III',original,table+index*12) for index in range(count)]
    relocation_table, relocation_count = struct.unpack_from('<II',original,0x128)
    expected = bytearray(original)
    changed_words = 0
    for index in range(relocation_count):
        tag, kind, symbol_segment, addend = struct.unpack_from('<IBB2xI',original,relocation_table+index*12)
        offset, size, _ = segments[tag & 15]
        within = tag >> 4
        if within+4 > size:
            raise ValueError('Relocation leaves its segment')
        target = offset+within
        symbol = base+segments[symbol_segment][0]
        if kind == 0:
            continue
        if kind in (2,38):
            value = symbol+addend
        elif kind == 3:
            value = symbol+addend-(base+target)
        else:
            raise ValueError('Unsupported relocation type')
        struct.pack_into('<I',expected,target,value & 0xffffffff)
        changed_words += 1
    if bytes(expected) != relocated:
        raise ValueError('Payload differs from raw-record-derived relocation output')
    return {'source_sha256':hashlib.sha256(original).hexdigest(),'relocation_words_verified':changed_words,
            'module_bytes':len(original),'untouched_bytes_preserved':True,
            'scope':'synthetic local relocation only; runtime loader not verified'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('elf')
    args=parser.parse_args()
    print(json.dumps(verify(args.source,args.elf),indent=2))
