"""Verify original/rebuilt live-helper and frame evidence from the RPC probes."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from probe_runtime_rpc import CLIENT_SHA256


def verify_startup(root, proof, code):
    startup = (root/'loaded-startup.bin').read_bytes()
    if (proof['startup_address'], proof['startup_size'], proof['loaded_startup_verified']) != ('0x100024', 44, True):
        raise ValueError('Live startup address or extent differs')
    if startup != code[0x24:0x50] or proof['loaded_startup_sha256'] != hashlib.sha256(startup).hexdigest():
        raise ValueError('Live BSS/literal evidence differs from selected image')
    return {'bss_sha256': hashlib.sha256(startup[:36]).hexdigest(),
            'preserved_literals_sha256': hashlib.sha256(startup[36:]).hexdigest()}


def verify(original_run, rebuilt_run, original_code, rebuilt_code):
    results = []
    for directory, code_path, variant in ((original_run, original_code, 'original'),
                                          (rebuilt_run, rebuilt_code, 'rebuilt-nonmatching')):
        root = Path(directory)
        proof = json.loads((root/'observations.json').read_text())
        code = Path(code_path).read_bytes()
        helper = (root/'loaded-helper.bin').read_bytes()
        if proof['client_sha256'] != CLIENT_SHA256 or proof['title_id'] != '00040000001b5000' or proof['variant'] != variant:
            raise ValueError('RPC client/title/variant differs')
        if proof['code_sha256'] != hashlib.sha256(code).hexdigest() or helper != code[0x50:0x72] or proof['loaded_helper_sha256'] != hashlib.sha256(helper).hexdigest():
            raise ValueError('Live helper evidence differs from selected image')
        frame = (root/'game-frame.png').read_bytes()
        if frame[:8] != b'\x89PNG\r\n\x1a\n' or hashlib.sha256(frame).hexdigest() != proof['frame']['sha256']:
            raise ValueError('Rendered-frame integrity differs')
        startup = None
        if 'startup_address' in proof or hashlib.sha256(code).hexdigest() == '1f13be78a12c7f47758271f1a8e8bd63dd4c811bb85c752b6be3f2fe6226b839':
            startup = verify_startup(root, proof, code)
        results.append({'variant': variant, 'helper_sha256': hashlib.sha256(helper).hexdigest(),
                        'startup': startup,
                        'frame_sha256': hashlib.sha256(frame).hexdigest(), 'frame_dimensions': list(struct.unpack_from('>II', frame, 16))})
    if results[0]['helper_sha256'] == results[1]['helper_sha256'] or results[0]['frame_dimensions'] != results[1]['frame_dimensions']:
        raise ValueError('Unexpected unchanged helper or differing frame geometry')
    startups = [r['startup'] for r in results]
    if any(startups) and (not all(startups) or startups[0]['preserved_literals_sha256'] != startups[1]['preserved_literals_sha256']):
        raise ValueError('Missing paired startup evidence or changed preserved literals')
    if all(startups) and Path(original_code).read_bytes()[0x24:0x48] != Path(rebuilt_code).read_bytes()[0x24:0x48] and startups[0]['bss_sha256'] == startups[1]['bss_sha256']:
        raise ValueError('Unexpected unchanged live BSS')
    return {'live_helpers_verified': 2, 'rendered_frames_verified': 2, 'observations': results,
            'live_startup_ranges_verified': 2 if all(startups) else 0,
            'scope': 'Selected live routine/literal bytes and frame integrity; execution counts and gameplay unproven'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original_run')
    parser.add_argument('rebuilt_run')
    parser.add_argument('original_code')
    parser.add_argument('rebuilt_code')
    args = parser.parse_args()
    print(json.dumps(verify(args.original_run, args.rebuilt_run, args.original_code, args.rebuilt_code), indent=2))
