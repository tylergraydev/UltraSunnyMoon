"""Prepare original/rebuilt decrypted CXIs for local emulator comparison.

Only the pinned base NCSD partition is supported. Retail inputs stay unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from verify_main_rebuild import verify as verify_main

BASE_SHA256 = '3bb3b4eb0d17f18875d8b847c871dc97a172beeda03ce99e59e62a78ed5c1a53'


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(8*1024*1024):
            digest.update(block)
    return digest.hexdigest()


def build(base_path, main_run, destination):
    base = Path(base_path)
    if file_hash(base) != BASE_SHA256:
        raise ValueError('Base container differs from the pinned local input')
    run = Path(main_run)
    main_proof = verify_main(run/'orig/code.bin', run/'orig/exheader.bin', run)
    code = (run/'out/code.bin').read_bytes()
    with base.open('rb') as source:
        ncsd = source.read(0x200)
        if ncsd[0x100:0x104] != b'NCSD':
            raise ValueError('Expected NCSD base')
        partition, partition_size = (n*0x200 for n in struct.unpack_from('<II', ncsd, 0x120))
        source.seek(partition)
        header = bytearray(source.read(0x200))
        if header[0x100:0x104] != b'NCCH' or not header[0x18f]&4 or header[0x18e] != 0:
            raise ValueError('Expected decrypted NCCH with 512-byte units')
        size = struct.unpack_from('<I', header, 0x104)[0]*0x200
        if size != partition_size or partition+size > base.stat().st_size:
            raise ValueError('NCCH extent differs from NCSD allocation')
        source.seek(partition+0x200)
        exheader = source.read(0x800)
        if exheader != (run/'orig/exheader.bin').read_bytes() or exheader[0xd]&1:
            raise ValueError('Original exheader differs or code is compressed')
        exefs_offset, exefs_size, hash_size = (n*0x200 for n in struct.unpack_from('<III', header, 0x1a0))
        if exefs_offset+exefs_size > size or hash_size != 0x200:
            raise ValueError('Unexpected ExeFS extent/hash region')
        source.seek(partition+exefs_offset)
        exefs = bytearray(source.read(0x200))
        matches = []
        for index in range(10):
            name, offset, length = struct.unpack_from('<8sII', exefs, index*16)
            if name.rstrip(b'\0') == b'.code':
                matches.append((index, offset, length))
        if len(matches) != 1:
            raise ValueError('Expected exactly one .code entry')
        index, code_offset, code_size = matches[0]
        code_position = exefs_offset+0x200+code_offset
        if code_size != len(code) or code_position+code_size > exefs_offset+exefs_size:
            raise ValueError('Rebuilt code does not fit original ExeFS entry')
        source.seek(partition+code_position)
        if source.read(code_size) != (run/'orig/code.bin').read_bytes():
            raise ValueError('Container .code differs from verified original')
        exefs[0x1e0-index*32:0x200-index*32] = hashlib.sha256(code).digest()
        header[0x1c0:0x1e0] = hashlib.sha256(exefs).digest()
        root = Path(destination).resolve()
        root.relative_to((Path.cwd()/'analysis/private').resolve())
        root.mkdir(parents=True, exist_ok=False)
        source.seek(partition)
        original_hash, rebuilt_hash = hashlib.sha256(), hashlib.sha256()
        with (root/'original.cxi').open('xb') as original, (root/'rebuilt.cxi').open('xb') as rebuilt:
            remaining, position = size, 0
            patches = [(0, bytes(header)), (exefs_offset, bytes(exefs)), (code_position, code)]
            while remaining:
                block = source.read(min(8*1024*1024, remaining))
                if not block:
                    raise ValueError('Truncated original partition')
                original.write(block)
                original_hash.update(block)
                altered = bytearray(block)
                for offset, payload in patches:
                    start, end = max(position, offset), min(position+len(block), offset+len(payload))
                    if end > start:
                        altered[start-position:end-position] = payload[start-offset:end-offset]
                rebuilt.write(altered)
                rebuilt_hash.update(altered)
                position += len(block)
                remaining -= len(block)
    report = {'base_sha256': BASE_SHA256, 'partition_offset': partition, 'size': size,
              'original_cxi_sha256': original_hash.hexdigest(), 'rebuilt_cxi_sha256': rebuilt_hash.hexdigest(),
              'main_image_sha256': main_proof['sha256'], 'replacement_policy': main_proof['replacement_policy'],
              'main_run': str(run.resolve()), 'exefs_offset': exefs_offset, 'code_offset': code_position,
              'scope': 'Decrypted emulator CXIs; retail RSA signature retained, not regenerated; hardware validity unclaimed'}
    (root/'package.json').write_text(json.dumps(report, indent=2)+'\n')
    from verify_runtime_package import verify
    proof = verify(root, run, base)
    (root/'verification.json').write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base')
    parser.add_argument('main_run')
    parser.add_argument('destination')
    args = parser.parse_args()
    build(args.base, args.main_run, args.destination)
