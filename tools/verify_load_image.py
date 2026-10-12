"""Independently check REA's file-backed main-image ELF mappings.

REA reports ELF observations, not an ELF-specific verified attestation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from verify_analysis import read_json


def verify(code_path, elf_path, evidence_path):
    code, elf = Path(code_path).read_bytes(), Path(elf_path).read_bytes()
    evidence = read_json(evidence_path)
    if hashlib.sha256(elf).hexdigest() != evidence['subject']['digest']['sha256'] or elf[0x1000:] != code:
        raise ValueError('Evidence target or original payload differs')
    if elf[:7] != b'\x7fELF\x01\x01\x01':
        raise ValueError('Expected little-endian ELF32')
    header = struct.unpack_from('<16sHHIIIIIHHHHHH', elf)
    phoff, phsize, phcount = header[5], header[9], header[10]
    expected = []
    for index in range(phcount):
        kind, offset, address, _, size, _, _, _ = struct.unpack_from('<IIIIIIII', elf, phoff + index*phsize)
        if kind == 1 and size:
            expected.append((offset, address, size))
    observed = [mapping for mapping in evidence['raw_result']['mappings']
                if mapping['loaded'] and mapping['address_space'] == 'ram' and mapping['source_file_index'] == 0]
    if len(observed) != len(expected):
        raise ValueError('File-backed mapping count differs')
    total = 0
    for offset, address, size in expected:
        matches = [mapping for mapping in observed if int(mapping['start'], 16) == address]
        if len(matches) != 1:
            raise ValueError('Expected one mapping at each segment start')
        mapping = matches[0]
        if mapping['file_offset'] != offset or mapping['length'] != size or int(mapping['end'], 16) != address+size-1:
            raise ValueError('Mapping address, offset, or extent differs')
        if hashlib.sha256(elf[offset:offset+size]).hexdigest() != mapping['sha256']:
            raise ValueError('Measured bytes differ from the original file')
        total += size
    if total != len(code):
        raise ValueError('Mappings do not cover the complete original code payload')
    return {'evidence_id': evidence['evidence_id'], 'original_segments_verified': len(expected),
            'original_bytes_verified': total, 'target_digest_verified': True,
            'scope': 'initialized ELF mappings; not a retail loader or runtime proof'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('code')
    parser.add_argument('elf')
    parser.add_argument('evidence')
    args = parser.parse_args()
    print(json.dumps(verify(args.code, args.elf, args.evidence), indent=2))
