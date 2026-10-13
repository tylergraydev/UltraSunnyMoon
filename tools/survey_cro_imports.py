"""Survey CRO import tables in a decrypted base RomFS using the pinned pipeline reader.

Extracts every .cro/.crs root module into a new private run directory, parses its
header with the pinned reader, and summarizes import tables without editing bytes.
Relocation meaning is not applied here; see verify_cro_imports.py for resolution.
Retail bytes and the generated report stay under analysis/private/.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from module_view import load_reader
from pyctr.fileio import SubsectionIO
from pyctr.type.romfs import RomFSReader
import struct


def extract_roots(image, destination):
    """Read every root code module from a decrypted CCI without dumping other assets."""
    modules = {}
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
        with RomFSReader(SubsectionIO(source, ncch_offset+offset*0x200, size*0x200), case_insensitive=False) as romfs:
            for name in romfs.get_info_from_path('/').contents:
                if not name.endswith(('.cro', '.crs')):
                    continue
                with romfs.open('/'+name) as module_file:
                    data = module_file.read()
                if Path(name).name != name:
                    raise ValueError('Module name is not a basename')
                (destination/name).write_bytes(data)
                modules[name] = data
    return modules


def summarize(name, data, CRO, BinaryReader):
    cro = CRO.from_reader(BinaryReader(name, data))
    imports = []
    for entry in cro.import_module_table.obj:
        imports.append({'module': entry.name.obj,
                        'indexed_off': entry.indexed.off, 'indexed_count': entry.indexed.size,
                        'anon_off': entry.anon.off, 'anon_count': entry.anon.size})
    return {'name': name, 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data),
            'declared_size': cro.cro_size, 'bss_size': cro.bss_size,
            'named_exports': len(cro.named_export_table.obj),
            'import_modules': imports,
            'named_imports': len(cro.named_import_table.obj),
            'indexed_imports': len(cro.indexed_import_table.obj),
            'anon_imports': len(cro.anon_import_table.obj),
            'import_relocations': len(cro.import_relocations.obj),
            'internal_relocations': len(cro.internal_relocs.obj)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('run_directory')
    parser.add_argument('--reader', default='.local/pipeline-reference')
    args = parser.parse_args()
    CRO, BinaryReader = load_reader(args.reader)
    root = Path(args.run_directory).resolve()
    root.relative_to((Path.cwd()/'analysis'/'private').resolve())
    root.mkdir(parents=True, exist_ok=False)
    modules_dir = root/'modules'
    modules_dir.mkdir()
    modules = extract_roots(args.image, modules_dir)
    summaries = [summarize(name, data, CRO, BinaryReader) for name, data in sorted(modules.items())
                 if name.endswith('.cro')]
    report = {'reader': 'pipeline 621bbce909ad2f9c551563c7443ed80c0123fe77 ctrtype.CRO',
              'static_crs_sha256': hashlib.sha256(modules['static.crs']).hexdigest(),
              'cro_count': len(summaries),
              'modules_with_named_imports': [s['name'] for s in summaries if s['named_imports']],
              'modules_with_indexed_or_anon_imports': [s['name'] for s in summaries
                                                       if s['indexed_imports'] or s['anon_imports']],
              'summaries': summaries}
    (root/'survey.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'cro_count': report['cro_count'],
                      'with_named_imports': len(report['modules_with_named_imports']),
                      'with_indexed_or_anon': len(report['modules_with_indexed_or_anon_imports']),
                      'survey': str(root/'survey.json')}))


if __name__ == '__main__':
    sys.exit(main())
