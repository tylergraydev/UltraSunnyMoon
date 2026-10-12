"""Inventory code modules and selectively extract them from a decrypted CCI.

Requires pyctr==0.7.6. No boot ROM keys are needed for already decrypted RomFS.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from pyctr.fileio import SubsectionIO
from pyctr.type.romfs import RomFSReader


def inventory(image, selected):
    destination = Path('extracted/base/modules')
    destination.mkdir(parents=True, exist_ok=True)
    with Path(image).open('rb') as source:
        header = source.read(0x200)
        if header[0x100:0x104] != b'NCSD':
            raise ValueError('Expected a CCI/NCSD image')
        ncch_offset, ncch_units = struct.unpack_from('<II', header, 0x120)
        ncch_offset, ncch_size = ncch_offset*0x200, ncch_units*0x200
        source.seek(ncch_offset)
        ncch = source.read(0x200)
        if ncch[0x100:0x104] != b'NCCH' or not ncch[0x18f] & 4:
            raise ValueError('Only already decrypted application NCCH is supported')
        offset, size = struct.unpack_from('<II', ncch, 0x1b0)
        if (offset+size)*0x200 > ncch_size or ncch_offset+ncch_size > Path(image).stat().st_size:
            raise ValueError('RomFS region leaves the container')
        with RomFSReader(SubsectionIO(source, ncch_offset+offset*0x200, size*0x200), case_insensitive=False) as romfs:
            modules = []
            for name in romfs.get_info_from_path('/').contents:
                if not name.endswith(('.cro', '.crs')):
                    continue
                with romfs.open('/'+name) as module_file:
                    data = module_file.read()
                modules.append({'name': name, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                'magic': data[0x80:0x84].decode('ascii')})
                if name in selected:
                    if Path(name).name != name:
                        raise ValueError('Module name is not a basename')
                    (destination/name).write_bytes(data)
            missing = set(selected)-{item['name'] for item in modules}
            if missing:
                raise ValueError(f'Selected modules not found: {sorted(missing)}')
    return {'reader': 'pyctr 0.7.6', 'modules': sorted(modules, key=lambda item:item['name']),
            'extracted': sorted(selected), 'scope': 'root code modules only; no unrelated assets extracted'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('--extract', nargs='+', default=['static.crs', 'AnaiTest.cro'])
    args = parser.parse_args()
    report = inventory(args.image, args.extract)
    output = Path('analysis/private/module-inventory.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'modules':len(report['modules']), 'extracted':report['extracted'], 'report':str(output)}))
