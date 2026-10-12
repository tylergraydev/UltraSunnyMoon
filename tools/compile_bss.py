"""Compile the reconstructed startup BSS clearer in WSL; no image integration."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from compile_helper import standalone_helper
from rebuild_module import digest
from rebuild_main import CODE_SHA256, EXHEADER_SHA256

SOURCE = Path('src/runtime/clear_bss.c')


def build(code_path, exheader_path, destination):
    code, header = Path(code_path).read_bytes(), Path(exheader_path).read_bytes()
    if digest(code) != CODE_SHA256 or digest(header) != EXHEADER_SHA256:
        raise ValueError('Inputs differ from the pinned base')
    root = Path(destination).resolve()
    root.relative_to((Path.cwd()/'analysis/private').resolve())
    root.mkdir(parents=True, exist_ok=False)
    compiler = shutil.which('arm-none-eabi-gcc')
    if not compiler:
        raise ValueError('Install gcc-arm-none-eabi in WSL')
    flags = ['-mcpu=mpcore', '-marm', '-mfloat-abi=soft', '-ffreestanding',
             '-fno-builtin', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
             '-fomit-frame-pointer', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror']
    results = []
    for profile in ('Os', 'O2'):
        target = root/(profile+'.o')
        command = [compiler, *flags, '-'+profile, '-c', str(SOURCE.resolve()), '-o', str(target)]
        subprocess.run(command, check=True, capture_output=True)
        payload = standalone_helper(target.read_bytes(), 'ultrasun_clear_bss', thumb=False)
        (root/(profile+'.disassembly.txt')).write_text(subprocess.check_output(
            ['arm-none-eabi-objdump', '-dr', str(target)], text=True))
        results.append({'profile': profile, 'command': command, 'object': target.name,
                        'object_sha256': digest(target.read_bytes()), 'text_sha256': digest(payload),
                        'compiled_size': len(payload), 'original_body_size': 28,
                        'original_with_literals_size': 36,
                        'exact_match_including_literals': payload == code[0x24:0x48]})
    backend = Path(subprocess.check_output([compiler, '-print-prog-name=cc1'], text=True).strip())
    report = {'compiler': {'path': compiler, 'sha256': digest(Path(compiler).read_bytes()),
                          'version': subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
                          'backend_sha256': digest(backend.read_bytes())},
              'source_sha256': digest(SOURCE.read_bytes()), 'code_sha256': CODE_SHA256,
              'exheader_sha256': EXHEADER_SHA256, 'entry': '0x100024', 'mode': 'arm',
              'original_body_sha256': digest(code[0x24:0x40]),
              'original_with_literals_sha256': digest(code[0x24:0x48]), 'profiles': results,
              'integration': 'not attempted; compiled source is not yet selected in a game image'}
    (root/'comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'compiler': report['compiler']['version'], 'profiles': results}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('code')
    parser.add_argument('exheader')
    parser.add_argument('destination')
    args = parser.parse_args()
    build(args.code, args.exheader, args.destination)
