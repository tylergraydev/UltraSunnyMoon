"""Check paired movie/log receipts and original/rebuilt RPC checkpoint evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from compare_runtime_rpc import verify as verify_rpc
from startup_movie import generate_plan, inspect, verify_log


def verify(original, rebuilt, original_code, rebuilt_code, movie_path, plan_path=None):
    movie_data = Path(movie_path).read_bytes()
    movie = inspect(movie_data)
    movie_id = int.from_bytes(movie_data[40:48], 'little')
    plan_hash = None
    if plan_path:
        plan_data = Path(plan_path).read_bytes()
        if generate_plan(json.loads(plan_data)) != movie_data:
            raise ValueError('Selected input plan does not reproduce movie bytes')
        plan_hash = hashlib.sha256(plan_data).hexdigest()
    proof = verify_rpc(original, rebuilt, original_code, rebuilt_code)
    playback = []
    for directory in (original, rebuilt):
        root = Path(directory)
        receipt = json.loads((root/'replay.json').read_text())
        log = (root/'replay-log.txt').read_bytes()
        status = verify_log(log.decode('utf-8'), expected_movie_id=movie_id)
        if receipt['movie'] != movie or receipt['log_sha256'] != hashlib.sha256(log).hexdigest():
            raise ValueError('Movie or retained log identity differs')
        if any(receipt[k] != status[k] for k in ('loaded', 'completed', 'input_type_desync_errors')):
            raise ValueError('Playback status receipt differs')
        playback.append(status)
    proof.update(movie=movie, playback=playback, plan_sha256=plan_hash,
                 scope='Same selected movie and live-byte/frame integrity; observed checkpoint needs visual inspection; first controllable gameplay and complete determinism unproven')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'rebuilt', 'original_code', 'rebuilt_code', 'movie'):
        parser.add_argument(name)
    parser.add_argument('--plan', help='Independently regenerate and compare the selected declarative plan')
    args = parser.parse_args()
    print(json.dumps(verify(args.original, args.rebuilt, args.original_code, args.rebuilt_code, args.movie, args.plan), indent=2))
