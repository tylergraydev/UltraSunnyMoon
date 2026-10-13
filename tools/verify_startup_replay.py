"""Check paired movie/log receipts and original/rebuilt RPC checkpoint evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from compare_runtime_rpc import verify as verify_rpc
from startup_movie import inspect, verify_log


def verify(original, rebuilt, original_code, rebuilt_code, movie_path):
    movie = inspect(Path(movie_path).read_bytes())
    proof = verify_rpc(original, rebuilt, original_code, rebuilt_code)
    playback = []
    for directory in (original, rebuilt):
        root = Path(directory)
        receipt = json.loads((root/'replay.json').read_text())
        log = (root/'replay-log.txt').read_bytes()
        status = verify_log(log.decode('utf-8'))
        if receipt['movie'] != movie or receipt['log_sha256'] != hashlib.sha256(log).hexdigest():
            raise ValueError('Movie or retained log identity differs')
        if any(receipt[k] != status[k] for k in ('loaded', 'completed', 'input_type_desync_errors')):
            raise ValueError('Playback status receipt differs')
        playback.append(status)
    proof.update(movie=movie, playback=playback,
                 scope='Same selected movie and live-byte/frame integrity; observed checkpoint needs visual inspection; first controllable gameplay and complete determinism unproven')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'rebuilt', 'original_code', 'rebuilt_code', 'movie'):
        parser.add_argument(name)
    args = parser.parse_args()
    print(json.dumps(verify(args.original, args.rebuilt, args.original_code, args.rebuilt_code, args.movie), indent=2))
