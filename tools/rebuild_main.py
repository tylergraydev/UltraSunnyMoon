"""Split/link the pinned Ultra Sun base main image with explicit source selection.

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


def layout(code, exheader, bss=False):
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
              ('startup_zero_helper', 0x24, 0x24 if bss else 0x1c, '$a'),
              ('original_startup_literals', 0x48 if bss else 0x40, 8 if bss else 0x10, '$d'),
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
    saved_plan = json.loads((root/'layout.json').read_text())
    plan = layout(code, header, bss='bss_replacement' in saved_plan)
    binary = CTRBinary('code.bin', code, ExHeader.from_reader(BinaryReader('exheader.bin', header)))
    symbols = [Symbol(o['offset'], o['name'], o['mode'], o['size'], o['section']) for o in plan['objects']]
    split_dir = root/'split/code.bin'
    split_dir.mkdir(parents=True)
    info = SimpleNamespace(args={'progress_reports': False})
    targets = split_by_symbols(binary, split_dir, symbols, info)
    if 'replacement' in saved_plan:
        targets = [(offset, root/'build/aeabi_vec_ctor.o' if path.stem == 'aeabi_vec_ctor' else path)
                   for offset, path in targets]
    if 'bss_replacement' in saved_plan:
        targets = [(offset, root/'build/startup_zero_helper.o' if path.stem == 'startup_zero_helper' else path)
                   for offset, path in targets]
    pipeline.LD_FLAGS = ['--entry=0x100000', '-T', str(root/'linker.ld')]
    linked = pipeline.link_all('code.bin', [p for _, p in targets], root/'out', str(root/'tools/ld'), info)
    pipeline.recreate_binary('code.bin', root/'out', str(root/'tools/objcopy'), linked, binary)


def run(code_path, exheader_path, destination, reader, helper_object=None, allow_nonmatching=False, bss_object=None):
    load_reader(reader)
    code, header = Path(code_path).read_bytes(), Path(exheader_path).read_bytes()
    plan = layout(code, header, bss=bool(bss_object))
    replacement = None
    if allow_nonmatching and not (helper_object or bss_object):
        raise ValueError('Nonmatching permission requires a compiled object')
    if bss_object:
        from bss_selection import select
        bss_object = Path(bss_object).resolve()
        plan['bss_replacement'] = select(bss_object, code, header, allow_nonmatching)
        plan['source_replacements'] += 1
    if helper_object:
        from compile_helper import standalone_helper, require_exact
        helper_object = Path(helper_object).resolve()
        payload = standalone_helper(helper_object.read_bytes())
        if len(payload) != 34:
            raise ValueError('Replacement must occupy exactly the original 34-byte slot')
        if not allow_nonmatching:
            require_exact(helper_object, code_path)
        comparison = json.loads((helper_object.parent/'comparison.json').read_text())
        matches = [p for p in comparison['profiles'] if p['object'] == helper_object.name]
        if len(matches) != 1 or matches[0]['object_sha256'] != digest(helper_object.read_bytes()):
            raise ValueError('Compilation receipt does not bind the selected helper')
        if comparison['source_sha256'] != digest(Path('src/runtime/aeabi_vec_ctor.c').read_bytes()) or comparison['code_sha256'] != CODE_SHA256:
            raise ValueError('Compilation receipt source or target differs')
        behavior = json.loads((helper_object.parent/'behavior.json').read_text())
        if behavior['object_sha256'] != digest(helper_object.read_bytes()) or behavior['code_sha256'] != CODE_SHA256 or behavior['cases_passed'] != 8 or len(behavior['cases']) != 8 or behavior['cpu_model'] != 'ARM11 MPCore' or not all(c['passed'] for c in behavior['cases']):
            raise ValueError('Behavior receipt does not bind the selected helper')
        replacement = {'object_sha256': digest(helper_object.read_bytes()),
                       'source_sha256': comparison['source_sha256'], 'compiler': comparison['compiler'],
                       'command': matches[0]['command'], 'behavior': behavior,
                       'policy': 'behavior-tested-nonmatching' if payload != code[0x50:0x72] else 'exact'}
        plan['replacement'] = replacement
        plan['source_replacements'] += 1
    root = Path(destination).resolve()
    root.relative_to((Path.cwd()/'analysis/private').resolve())
    root.mkdir(parents=True, exist_ok=False)
    for name in ('orig', 'tools', 'out'):
        (root/name).mkdir()
    if replacement or bss_object:
        (root/'build').mkdir()
    if bss_object:
        shutil.copyfile(bss_object, root/'build/startup_zero_helper.o')
    if replacement:
        shutil.copyfile(helper_object, root/'build/aeabi_vec_ctor.o')
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
              'pipeline_exit_code': result.returncode, 'source_replacements': plan['source_replacements']}
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
    parser.add_argument('--helper-object', help='Select the compiled helper with bound compilation/behavior receipts')
    parser.add_argument('--bss-object', help='Select the compiled BSS clearer including its literals')
    parser.add_argument('--allow-nonmatching', action='store_true', help='Explicitly permit behavior-tested nonmatching objects')
    args = parser.parse_args()
    run(args.code, args.exheader, args.destination, args.reader, args.helper_object, args.allow_nonmatching, args.bss_object)
