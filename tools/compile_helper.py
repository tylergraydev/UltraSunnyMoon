"""Compile bounded GCC candidates and compare the first Thumb helper's bytes.

Run in WSL; all compiled objects, disassembly and reports stay private.
No unmatched candidate is integrated and no original-byte fallback is allowed.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import struct

from rebuild_module import digest
from rebuild_main import CODE_SHA256
from verify_rebuild import elf_text


def build(code_path, destination, source='src/runtime/aeabi_vec_ctor.c'):
    code = Path(code_path).read_bytes()
    if digest(code) != CODE_SHA256:
        raise ValueError('Original code differs from the pinned base')
    root = Path(destination).resolve()
    root.relative_to((Path.cwd()/'analysis/private').resolve())
    root.mkdir(parents=True, exist_ok=False)
    compiler = shutil.which('arm-none-eabi-gcc')
    if not compiler:
        raise ValueError('Install gcc-arm-none-eabi in WSL')
    source = Path(source).resolve()
    flags = ['-mcpu=mpcore', '-mthumb', '-mfloat-abi=soft', '-ffreestanding', '-fno-builtin',
             '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-fomit-frame-pointer',
             '-fno-stack-protector', '-Wall', '-Wextra', '-Werror']
    profiles = [('Os', ['-Os']), ('O1', ['-O1']), ('O2', ['-O2']), ('O3', ['-O3']),
                ('Os_no_reorder', ['-Os', '-fno-reorder-blocks']),
                ('O2_no_schedule', ['-O2', '-fno-schedule-insns', '-fno-schedule-insns2'])]
    results = []
    for label, extra in profiles:
        target = root/(label+'.o')
        command = [compiler, *flags, *extra, '-c', str(source), '-o', str(target)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        payload = elf_text(target.read_bytes())
        disassembly = subprocess.check_output(['arm-none-eabi-objdump', '-dr', str(target)], text=True)
        (root/(label+'.disassembly.txt')).write_text(disassembly)
        original = code[0x50:0x72]
        exact = payload == original
        results.append({'profile': label, 'command': command, 'object': target.name,
                        'object_sha256': digest(target.read_bytes()), 'text_sha256': digest(payload),
                        'compiled_size': len(payload), 'original_size': len(original),
                        'exact_match': exact,
                        'different_bytes': sum(a != b for a, b in zip(payload, original))+abs(len(payload)-len(original))})
    report = {'compiler': {'path': compiler, 'sha256': digest(Path(compiler).read_bytes()),
                          'version': subprocess.check_output([compiler, '--version'], text=True).splitlines()[0]},
              'source_path': str(source), 'source_sha256': digest(source.read_bytes()),
              'code_sha256': digest(code), 'entry': '0x100050', 'thumb': True,
              'original_function_sha256': digest(code[0x50:0x72]), 'profiles': results,
              'integration': 'not attempted; exact match required; no fallback to original objects'}
    backend = Path(subprocess.check_output([compiler, '-print-prog-name=cc1'], text=True).strip())
    report['compiler']['backend'] = {'path': str(backend), 'sha256': digest(backend.read_bytes())}
    (root/'comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'compiler': report['compiler']['version'],
                      'profiles': [{k: p[k] for k in ('profile', 'compiled_size', 'exact_match')} for p in results]}, indent=2))
    return report


def require_exact(object_path, code_path):
    code = Path(code_path).read_bytes()
    if digest(code) != CODE_SHA256:
        raise ValueError('Original code differs from the pinned base')
    if elf_text(Path(object_path).read_bytes()) != code[0x50:0x72]:
        raise ValueError('Compiled helper does not match the original 34-byte slot; integration rejected')


def standalone_helper(data):
    """Reject external dependencies, relocation records and wrong entry symbols."""
    payload = elf_text(data)
    fields = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    if fields[1] != 1:
        raise ValueError('Expected relocatable compiled object')
    sections = [struct.unpack_from('<10I', data, fields[6]+i*40) for i in range(fields[12])]
    names_section = sections[fields[13]]
    names = data[names_section[4]:names_section[4]+names_section[5]]
    text_index = next(i for i, s in enumerate(sections) if names[s[0]:].split(b'\0', 1)[0] == b'.text')
    found = False
    for index, section in enumerate(sections):
        if section[1] in (4, 9) and section[5]:
            raise ValueError('Compiled helper contains relocations')
        if section[2] & 2 and section[5] and index != text_index:
            raise ValueError('Compiled helper has another allocated section')
        if section[1] != 2:
            continue
        if section[9] != 16 or section[6] >= len(sections) or section[4]+section[5] > len(data):
            raise ValueError('Invalid compiled symbol table')
        strings_section = sections[section[6]]
        strings = data[strings_section[4]:strings_section[4]+strings_section[5]]
        for offset in range(section[4], section[4]+section[5], 16):
            name, value, size, info, visibility, shndx = struct.unpack_from('<IIIBBH', data, offset)
            symbol = strings[name:].split(b'\0', 1)[0]
            if symbol and shndx == 0:
                raise ValueError('Compiled helper has undefined symbols')
            if symbol == b'__aeabi_vec_ctor_nocookie_nodtor':
                if value != 1 or size != len(payload) or info != 0x12 or shndx != text_index:
                    raise ValueError('Compiled Thumb entry/extent differs')
                found = True
    if not found:
        raise ValueError('Compiled helper entry symbol missing')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('code')
    parser.add_argument('destination')
    parser.add_argument('--source', default='src/runtime/aeabi_vec_ctor.c')
    parser.add_argument('--check-exact', action='store_true',
                        help='Treat destination as an existing object and reject a nonmatching candidate')
    args = parser.parse_args()
    if args.check_exact:
        require_exact(args.destination, args.code)
        print('Exact helper payload verified; integration still requires compiled-object selection proof.')
    else:
        build(args.code, args.destination, args.source)
