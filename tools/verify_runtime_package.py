"""Independently verify packaged CXI code, hashes and retained original regions."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from contextlib import ExitStack


def inspect(path, expected_code):
    with Path(path).open('rb') as stream:
        header = stream.read(512)
        if header[256:260] != b'NCCH' or not header[399]&4 or header[398] != 0:
            raise ValueError('Unexpected CXI format/encryption')
        size = int.from_bytes(header[260:264], 'little')*512
        if size != Path(path).stat().st_size:
            raise ValueError('CXI length differs from header')
        stream.seek(512)
        exheader = stream.read(2048)
        exheader_size = int.from_bytes(header[384:388], 'little')
        if hashlib.sha256(exheader[:exheader_size]).digest() != header[352:384] or exheader[13]&1:
            raise ValueError('Exheader hash or compression flag differs')
        exefs_offset = int.from_bytes(header[416:420], 'little')*512
        exefs_size = int.from_bytes(header[420:424], 'little')*512
        hash_size = int.from_bytes(header[424:428], 'little')*512
        if hash_size != 512 or exefs_offset+exefs_size > size:
            raise ValueError('Invalid ExeFS bounds')
        stream.seek(exefs_offset)
        table = stream.read(512)
        if hashlib.sha256(table).digest() != header[448:480]:
            raise ValueError('ExeFS superblock hash differs')
        entries, positions = {}, []
        for index in range(10):
            raw_name, offset, length = struct.unpack_from('<8sII', table, index*16)
            if not raw_name.strip(b'\0'):
                continue
            name = raw_name.rstrip(b'\0').decode('ascii')
            if name in entries or offset%512 or offset+length+512 > exefs_size:
                raise ValueError('Invalid ExeFS entry')
            position = exefs_offset+512+offset
            stream.seek(position)
            data = stream.read(length)
            if hashlib.sha256(data).digest() != table[480-index*32:512-index*32]:
                raise ValueError('ExeFS entry hash differs: '+name)
            entries[name] = (position, length)
            positions.append((position, position+length))
            if name == '.code' and data != expected_code:
                raise ValueError('Packaged code differs from selected image')
            if name == '.code':
                code_hash_offset = exefs_offset+480-index*32
        if '.code' not in entries or any(a[1] > b[0] for a, b in zip(sorted(positions), sorted(positions)[1:])):
            raise ValueError('Missing code or overlapping ExeFS entries')
        romfs_offset = int.from_bytes(header[432:436], 'little')*512
        romfs_size = int.from_bytes(header[436:440], 'little')*512
        romfs_hash_size = int.from_bytes(header[440:444], 'little')*512
        if romfs_offset+romfs_size > size or romfs_hash_size > romfs_size:
            raise ValueError('Invalid RomFS region')
        stream.seek(romfs_offset)
        if hashlib.sha256(stream.read(romfs_hash_size)).digest() != header[480:512]:
            raise ValueError('RomFS superblock hash differs')
    return {'size': size, 'code_offset': entries['.code'][0], 'code_size': entries['.code'][1],
            'code_hash_offset': code_hash_offset,
            'exefs_offset': exefs_offset, 'entries': list(entries)}


def verify(root, main_run, base_path=None):
    root, run = Path(root), Path(main_run)
    code = (run/'out/code.bin').read_bytes()
    original_code = (run/'orig/code.bin').read_bytes()
    original = inspect(root/'original.cxi', original_code)
    rebuilt = inspect(root/'rebuilt.cxi', code)
    if original != rebuilt:
        raise ValueError('Package layouts differ')
    allowed = [(448, 480), (original['code_hash_offset'], original['code_hash_offset']+32),
               (original['code_offset'], original['code_offset']+len(code))]
    report = json.loads((root/'package.json').read_text())
    digests, differences, position = [hashlib.sha256(), hashlib.sha256()], 0, 0
    with ExitStack() as stack:
        first = stack.enter_context((root/'original.cxi').open('rb'))
        second = stack.enter_context((root/'rebuilt.cxi').open('rb'))
        base = stack.enter_context(Path(base_path).open('rb')) if base_path else None
        if base:
            base_hash = hashlib.sha256()
            while chunk := base.read(8*1024*1024):
                base_hash.update(chunk)
            if base_hash.hexdigest() != '3bb3b4eb0d17f18875d8b847c871dc97a172beeda03ce99e59e62a78ed5c1a53':
                raise ValueError('Source base identity differs')
            base.seek(0x120)
            partition, extent = (n*512 for n in struct.unpack('<II', base.read(8)))
            if partition != report['partition_offset'] or extent != original['size']:
                raise ValueError('Original source partition extent differs')
            base.seek(partition)
        while old := first.read(8*1024*1024):
            if base and base.read(len(old)) != old:
                raise ValueError('Original CXI differs from the pinned source partition')
            new = second.read(len(old))
            if len(new) != len(old):
                raise ValueError('Package length differs')
            for digest, data in zip(digests, (old, new)):
                digest.update(data)
            if old != new:
                for index, (a, b) in enumerate(zip(old, new)):
                    if a != b:
                        if not any(start <= position+index < end for start, end in allowed):
                            raise ValueError('Package changed outside code and required hashes')
                        differences += 1
            position += len(old)
    if [d.hexdigest() for d in digests] != [report['original_cxi_sha256'], report['rebuilt_cxi_sha256']]:
        raise ValueError('Package digests differ from creation receipts')
    return {'verification_passed': True, 'size': position, 'changed_bytes': differences,
            'original_cxi_sha256': digests[0].hexdigest(), 'rebuilt_cxi_sha256': digests[1].hexdigest(),
            'packaged_code_sha256': hashlib.sha256(code).hexdigest(), 'exefs_entries_verified': rebuilt['entries'],
            'original_source_partition_verified': bool(base_path),
            'original_other_regions_preserved': True, 'runtime_execution_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package_directory')
    parser.add_argument('main_run')
    parser.add_argument('--base', help='Also compare the original CXI with the pinned NCSD source partition')
    args = parser.parse_args()
    print(json.dumps(verify(args.package_directory, args.main_run, args.base), indent=2))
