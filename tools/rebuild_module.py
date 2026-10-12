"""Split/link an untouched CRO with the pinned external pipeline (run in WSL).

All generated objects, symbols, logs and retail bytes remain in analysis/private.
This imports no decompiled source and does not identify the retail compiler.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

from module_view import load_reader, PIPELINE_REVISION


def digest(data):
    return hashlib.sha256(data).hexdigest()


def worker(root, reader):
    """Reuse pipeline operations with a portable text-only linker script."""
    CRO, BinaryReader = load_reader(reader)
    from ctrtype import CTRBinary
    from util import Symbol
    from split import split_by_symbols
    import pipeline
    import csv
    source = next((root / 'orig').glob('*.cro'))
    cro = CRO.from_reader(BinaryReader(source.name, source.read_bytes()))
    binary = CTRBinary(source.name, cro)
    rows = csv.DictReader((root / 'symbols' / (source.name+'.csv')).read_text().splitlines())
    symbols = [Symbol(int(r['Location'], 16)-binary.base_addr, r['Name'], r['Mode'],
                      int(r['Size'], 16), r['Segment']) for r in rows]
    info = SimpleNamespace(args={'progress_reports': False})
    split_dir = root / 'split' / source.name
    split_dir.mkdir(parents=True)
    targets = split_by_symbols(binary, split_dir, symbols, info)
    # No relocation generation or source replacements: original file-relative
    # instruction/literal words are intentionally preserved by this baseline.
    pipeline.LD_FLAGS = ['--entry=0', '-T', str(root / 'linker.ld')]
    linked = pipeline.link_all(source.name, [p for _, p in targets], root / 'out',
                               str(root / 'tools' / 'ld'), info)
    payload = root / 'out' / 'linked-payload.bin'
    subprocess.run([str(root / 'tools' / 'objcopy'), str(linked), '-O', 'binary', str(payload)], check=True)
    if payload.read_bytes() != binary.data:
        raise ValueError('Linked text/data differ from original concatenated payload')
    pipeline.recreate_binary(source.name, root / 'out', str(root / 'tools' / 'objcopy'), linked, binary)


def run(module, destination, reader):
    CRO, BinaryReader = load_reader(reader)
    source = Path(module).resolve()
    original = source.read_bytes()
    if source.name != 'AnaiTest.cro' or digest(original) != 'b996787f2bf5ab6182cbd0470ea1801d5bf0ee7e15e96b49c5b53a785dc66034':
        raise ValueError('This pilot is restricted to the verified base AnaiTest.cro')
    cro = CRO.from_reader(BinaryReader(source.name, original))
    root = Path(destination).resolve()
    root.relative_to((Path.cwd() / 'analysis' / 'private').resolve())
    root.mkdir(parents=True, exist_ok=False)
    for directory in ('orig', 'src', 'symbols', 'tools', 'out'):
        (root / directory).mkdir()
    shutil.copyfile(source, root / 'orig' / source.name)
    versions = {}
    for name in ('ld', 'objcopy'):
        executable = shutil.which('arm-none-eabi-' + name)
        if not executable:
            raise ValueError('Install binutils-arm-none-eabi in WSL')
        (root / 'tools' / name).symlink_to(executable)
        versions[name] = {'path': executable, 'sha256': digest(Path(executable).read_bytes()),
                          'version': subprocess.check_output([executable, '--version'], text=True).splitlines()[0]}
    # Pipeline positions are relative to text + data concatenation, not runtime
    # addresses. Separate the verified instruction ranges from the jump table.
    ranges = [('control_head', 0, 0x14, '$a'), ('switch_table', 0x14, 0x14, '$d'),
              ('control_tail', 0x28, 0x60, '$a'), ('literal_pool', 0x88, 0x24, '$d'),
              ('text_padding', 0xac, len(cro.text.obj)-0xac, '$d'),
              ('original_data', len(cro.text.obj), len(cro.data.obj), '$d')]
    rows = ['Name,Location,Mode,Size,Segment']
    for name, offset, size, mode in ranges:
        if size:
            rows.append(f'{name},{cro.text.off+offset:x},{mode},{size:x},.text')
    (root / 'symbols' / (source.name+'.csv')).write_text('\n'.join(rows)+'\n')
    (root / 'linker.ld').write_text('OUTPUT_FORMAT("elf32-littlearm")\nOUTPUT_ARCH(arm)\n'
                                  'SECTIONS { . = 0; .text : { *(.text) } }\n')
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', str(root), str(Path(reader).resolve())]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (root / 'pipeline.log').write_text(result.stdout)
    rebuilt_path = root / 'out' / source.name
    rebuilt = rebuilt_path.read_bytes() if rebuilt_path.exists() else b''
    differences = [i for i in range(min(len(original), len(rebuilt))) if original[i] != rebuilt[i]]
    report = {'pipeline_revision': PIPELINE_REVISION, 'command': command, 'toolchain': versions,
              'source_sha256': digest(original), 'rebuilt_sha256': digest(rebuilt),
              'original_size': len(original), 'rebuilt_size': len(rebuilt),
              'pipeline_exit_code': result.returncode,
              'different_byte_count': len(differences)+abs(len(original)-len(rebuilt)),
              'first_differences': [hex(i) for i in differences[:32]],
              'exact_match': rebuilt == original,
              'split_objects': len(list((root / 'split').rglob('*.o'))),
              'source_replacements': 0,
              'scope': 'Original text/data split into ARM ELF objects and linked; original CRO metadata retained.'}
    (root / 'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    if result.returncode == 0:
        from verify_rebuild import verify
        independent = verify(source, root)
        (root / 'independent-verification.json').write_text(json.dumps(independent, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if result.returncode or not report['exact_match']:
        raise SystemExit('Unchanged rebuild failed; inspect the private pipeline log and verification report')


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--worker':
        worker(Path(sys.argv[2]), Path(sys.argv[3]))
        raise SystemExit(0)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module')
    parser.add_argument('destination', help='New private run directory; existing directories are rejected')
    parser.add_argument('--reader', default='.local/pipeline-reference')
    args = parser.parse_args()
    run(args.module, args.destination, args.reader)
