"""Verify original/rebuilt live-helper and frame evidence from the RPC probes."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from probe_runtime_rpc import CLIENT_SHA256


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
        results.append({'variant': variant, 'helper_sha256': hashlib.sha256(helper).hexdigest(),
                        'frame_sha256': hashlib.sha256(frame).hexdigest(), 'frame_dimensions': list(struct.unpack_from('>II', frame, 16))})
    if results[0]['helper_sha256'] == results[1]['helper_sha256'] or results[0]['frame_dimensions'] != results[1]['frame_dimensions']:
        raise ValueError('Unexpected unchanged helper or differing frame geometry')
    return {'live_helpers_verified': 2, 'rendered_frames_verified': 2, 'observations': results,
            'scope': 'Selected live helper bytes and frame integrity; visual checkpoint comparison is separate'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original_run')
    parser.add_argument('rebuilt_run')
    parser.add_argument('original_code')
    parser.add_argument('rebuilt_code')
    args = parser.parse_args()
    print(json.dumps(verify(args.original_run, args.rebuilt_run, args.original_code, args.rebuilt_code), indent=2))
