"""Run bounded negative probes on disposable copies of a verified BSS build."""
import argparse
import json
from pathlib import Path
import shutil

from bss_selection import select
from verify_main_rebuild import verify


def probe(code_path, header_path, build, object_path, destination):
    code, header = Path(code_path).read_bytes(), Path(header_path).read_bytes()
    root = Path(destination).resolve()
    root.relative_to((Path.cwd()/'analysis/private').resolve())
    root.mkdir(parents=True, exist_ok=False)
    verify(code_path, header_path, build)
    rejected = []

    def expect_rejection(name, action):
        try:
            action()
        except (ValueError, KeyError, FileNotFoundError):
            rejected.append(name)
        else:
            raise ValueError('Negative probe unexpectedly accepted: '+name)

    expect_rejection('default-exact-policy', lambda: select(object_path, code, header, False))
    source = root/'source'
    source.mkdir()
    for name in ('Os.o', 'comparison.json', 'behavior.json'):
        shutil.copyfile(Path(object_path).parent/name, source/name)
    behavior = (source/'behavior.json').read_bytes()
    (source/'behavior.json').unlink()
    expect_rejection('missing-behavior-receipt', lambda: select(source/'Os.o', code, header, True))
    (source/'behavior.json').write_bytes(behavior)
    comparison = json.loads((source/'comparison.json').read_text())
    comparison['source_sha256'] = '0'*64
    (source/'comparison.json').write_text(json.dumps(comparison))
    expect_rejection('wrong-compilation-source', lambda: select(source/'Os.o', code, header, True))

    def mutate_plan(path, change):
        plan = json.loads(path.read_text())
        change(plan)
        path.write_text(json.dumps(plan))

    def flip(path, offset):
        data = bytearray(path.read_bytes())
        data[offset] ^= 1
        path.write_bytes(data)

    mutations = {
        'tampered-behavior': lambda r: mutate_plan(r/'layout.json', lambda p: p['bss_replacement']['behavior'].update(cases_passed=0)),
        'tampered-compiler': lambda r: mutate_plan(r/'layout.json', lambda p: p['bss_replacement']['compilation']['compiler'].update(version='wrong')),
        'missing-retained-compilation': lambda r: mutate_plan(r/'layout.json', lambda p: p['bss_replacement'].pop('compilation')),
        'wrong-object': lambda r: shutil.copyfile(r/'split/code.bin/startup_zero_helper.o', r/'build/startup_zero_helper.o'),
        'missing-object': lambda r: (r/'build/startup_zero_helper.o').unlink(),
        'overlapping-ranges': lambda r: mutate_plan(r/'layout.json', lambda p: p['objects'][2].update(offset=0x44)),
        'wrong-count': lambda r: mutate_plan(r/'layout.json', lambda p: p.update(source_replacements=0)),
        'response-original-fallback': lambda r: (r/'out/code.bin.txt').write_text((r/'out/code.bin.txt').read_text().replace('/build/startup_zero_helper.o', '/split/code.bin/startup_zero_helper.o')),
        'map-original-fallback': lambda r: (r/'out/code.bin_linked.map').write_text((r/'out/code.bin_linked.map').read_text().replace('/build/startup_zero_helper.o', '/split/code.bin/startup_zero_helper.o')),
        'preserved-startup-literal': lambda r: flip(r/'out/code.bin', 0x48),
        'unrelated-image-byte': lambda r: flip(r/'out/code.bin', 0x100),
        'reinsert-original-body': lambda r: (r/'out/code.bin').write_bytes(code[:0x48]+(r/'out/code.bin').read_bytes()[0x48:]),
    }
    for name, mutate in mutations.items():
        run = root/name
        shutil.copytree(build, run, ignore=shutil.ignore_patterns('tools'))
        mutate(run)
        expect_rejection(name, lambda: verify(code_path, header_path, run))
    verify(code_path, header_path, build)
    result = {'negative_probes_rejected': len(rejected), 'probes': rejected,
              'original_build_reverified': True}
    (root/'probes.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('code', 'exheader', 'build', 'object', 'destination'):
        parser.add_argument(name)
    args = parser.parse_args()
    print(json.dumps(probe(args.code, args.exheader, args.build, args.object, args.destination), indent=2))
