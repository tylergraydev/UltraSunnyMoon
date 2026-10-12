"""Split/link the pinned Ultra Sun base main image without source replacements.

Run in WSL. Generated retail objects and binaries stay under analysis/private.
"""
import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace

from module_view import load_reader, PIPELINE_REVISION
from rebuild_module import digest

CODE_SHA256 = 'b5388f7500d91be01499a99ca007c98212068608ed7c83c43952e1d5148e9e09'
EXHEADER_SHA256 = 'e4682ebab1bef10bdede38589b18c98f6976b1ebdc6a3b2540757aedcfe141e2'


def layout(code, exheader):
    if digest(code) != CODE_SHA256 or digest(exheader) != EXHEADER_SHA256:
        raise ValueError('Inputs differ from the pinned base code/exheader')
    segments, cursor = [], 0
    for name, header_offset in (('.text', 0x10), ('.rodata', 0x20), ('.data', 0x30)):
        address, pages, logical = struct.unpack_from('<III', exheader, header_offset)
        size = pages*0x1000
        segments.append({'section': name, 'address': address, 'offset': cursor,
                         'logical_size': logical, 'size': size})
        cursor += size
    if cursor != len(code) or any(s['logical_size'] > s['size'] for s in segments):
        raise ValueError('Invalid page allocation')
    if any(a['address']+a['size'] != b['address'] for a, b in zip(segments, segments[1:])):
        raise ValueError('This baseline requires contiguous initialized virtual regions')
    text = segments[0]
    ranges = [('original_startup_prefix', 0, 0x24, '$d'),
              ('startup_zero_helper', 0x24, 0x1c, '$a'),
              ('original_startup_literals', 0x40, 0x10, '$d'),
              ('aeabi_vec_ctor', 0x50, 0x22, '$t'),
              ('original_text_before_arm_sample', 0x72, 0x45b4-0x72, '$d'),
              ('startup_arm_sample', 0x45b4, 0x4c, '$a'),
              ('original_text_remainder', 0x4600, text['logical_size']-0x4600, '$d'),
              ('original_text_padding', text['logical_size'], text['size']-text['logical_size'], '$d')]
    objects = [{'name': n, 'offset': off, 'size': size, 'mode': mode, 'section': '.text'}
               for n, off, size, mode in ranges if size]
    for segment in segments[1:]:
        for suffix, offset, size in [('contents', segment['offset'], segment['logical_size']),
                                     ('padding', segment['offset']+segment['logical_size'],
                                      segment['size']-segment['logical_size'])]:
            if size:
                objects.append({'name': 'original_'+segment['section'][1:]+'_'+suffix,
                                'offset': offset, 'size': size, 'mode': '$d', 'section': segment['section']})
    return {'segments': segments, 'objects': objects,
            'bss_size': struct.unpack_from('<I', exheader, 0x3c)[0], 'source_replacements': 0}


def worker(root, reader):
    _, BinaryReader = load_reader(reader)
    from ctrtype import CTRBinary, ExHeader
    from util import Symbol
    from split import split_by_symbols
    import pipeline
    code = (root/'orig/code.bin').read_bytes()
    header = (root/'orig/exheader.bin').read_bytes()
    plan = layout(code, header)
    binary = CTRBinary('code.bin', code, ExHeader.from_reader(BinaryReader('exheader.bin', header)))
    symbols = [Symbol(o['offset'], o['name'], o['mode'], o['size'], o['section']) for o in plan['objects']]
    split_dir = root/'split/code.bin'
    split_dir.mkdir(parents=True)
    info = SimpleNamespace(args={'progress_reports': False})
    targets = split_by_symbols(binary, split_dir, symbols, info)
    pipeline.LD_FLAGS = ['--entry=0x100000', '-T', str(root/'linker.ld')]
    linked = pipeline.link_all('code.bin', [p for _, p in targets], root/'out', str(root/'tools/ld'), info)
    pipeline.recreate_binary('code.bin', root/'out', str(root/'tools/objcopy'), linked, binary)


def run(code_path, exheader_path, destination, reader):
    load_reader(reader)
    code, header = Path(code_path).read_bytes(), Path(exheader_path).read_bytes()
    plan = layout(code, header)
    root = Path(destination).resolve()
    root.relative_to((Path.cwd()/'analysis/private').resolve())
    root.mkdir(parents=True, exist_ok=False)
    for name in ('orig', 'tools', 'out'):
        (root/name).mkdir()
    (root/'orig/code.bin').write_bytes(code)
    (root/'orig/exheader.bin').write_bytes(header)
    (root/'layout.json').write_text(json.dumps(plan, indent=2)+'\n')
    versions = {}
    for name in ('ld', 'objcopy'):
        executable = shutil.which('arm-none-eabi-'+name)
        if not executable:
            raise ValueError('Install binutils-arm-none-eabi in WSL')
        (root/'tools'/name).symlink_to(executable)
        versions[name] = {'path': executable, 'sha256': digest(Path(executable).read_bytes()),
                         'version': subprocess.check_output([executable, '--version'], text=True).splitlines()[0]}
    script = ['OUTPUT_FORMAT("elf32-littlearm")', 'OUTPUT_ARCH(arm)',
              'PHDRS { text PT_LOAD FLAGS(5); ro PT_LOAD FLAGS(4); data PT_LOAD FLAGS(6); }', 'SECTIONS {']
    for segment, phdr in zip(plan['segments'], ('text', 'ro', 'data')):
        section, address, size = segment['section'], segment['address'], segment['size']
        script.extend([f'{section} 0x{address:x} : {{ *({section}) }} :{phdr}',
                       f'ASSERT(SIZEOF({section}) == 0x{size:x}, "{section} extent changed")'])
    script.append('}')
    (root/'linker.ld').write_text('\n'.join(script)+'\n')
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', str(root), str(Path(reader).resolve())]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (root/'pipeline.log').write_text(result.stdout)
    report = {'pipeline_revision': PIPELINE_REVISION, 'command': command, 'toolchain': versions,
              'code_sha256': digest(code), 'exheader_sha256': digest(header),
              'pipeline_exit_code': result.returncode, 'source_replacements': 0}
    (root/'build.json').write_text(json.dumps(report, indent=2)+'\n')
    if result.returncode:
        raise SystemExit('Rebuild failed; inspect private pipeline.log')
    from verify_main_rebuild import verify
    proof = verify(code_path, exheader_path, root)
    (root/'verification.json').write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps({k: v for k, v in proof.items() if k != 'selected_object_receipts'}, indent=2))


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--worker':
        worker(Path(sys.argv[2]), Path(sys.argv[3]))
        raise SystemExit(0)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('code')
    parser.add_argument('exheader')
    parser.add_argument('destination')
    parser.add_argument('--reader', default='.local/pipeline-reference')
    args = parser.parse_args()
    run(args.code, args.exheader, args.destination, args.reader)
