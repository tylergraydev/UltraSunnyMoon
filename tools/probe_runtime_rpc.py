"""Read-only Azahar RPC probe: selected game code, performance and game frame.

Uses the pinned official client shipped with the isolated Azahar 2126.2 build.
No memory writes, desktop control, or controller input injection is exposed.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

CLIENT_SHA256 = '3311da3b7e913d136b771f85f56b68694ecd6e35f065f8a7b0a0491ab711d018'


def load_client(runtime_directory):
    path = Path(runtime_directory)/'scripting/AzaharRPC.py'
    if hashlib.sha256(path.read_bytes()).hexdigest() != CLIENT_SHA256:
        raise ValueError('RPC client differs from pinned Azahar 2126.2 client')
    spec = importlib.util.spec_from_file_location('official_azahar_rpc', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.AzaharRPC


def retain_replay_log(runtime_directory, movie_path, root):
    from startup_movie import inspect, verify_log
    movie = Path(movie_path).read_bytes()
    log = (Path(runtime_directory)/'user/log/azahar_log.txt').read_bytes()
    text = log.decode('utf-8', errors='replace')
    status = verify_log(text)
    movie_id = int.from_bytes(movie[40:48], 'little')
    if f'Loaded Movie, ID: {movie_id:016X}' not in text:
        raise ValueError('Loaded movie ID differs from selected movie')
    replay = dict(status, movie=inspect(movie), log_sha256=hashlib.sha256(log).hexdigest())
    (Path(root)/'replay-log.txt').write_bytes(log)
    (Path(root)/'replay.json').write_text(json.dumps(replay, indent=2)+'\n', encoding='utf-8')


def probe(runtime_directory, code_path, destination, screenshot=True, movie_path=None):
    code = Path(code_path).read_bytes()
    known = {'b5388f7500d91be01499a99ca007c98212068608ed7c83c43952e1d5148e9e09': 'original',
             'c557617562525a2959a8fc3763b1398825b861ed69960646022dd34dd7ce2736': 'rebuilt-nonmatching',
             '1f13be78a12c7f47758271f1a8e8bd63dd4c811bb85c752b6be3f2fe6226b839': 'rebuilt-nonmatching'}
    code_hash = hashlib.sha256(code).hexdigest()
    if code_hash not in known:
        raise ValueError('Expected one of the verified original/rebuilt code images')
    root = Path(destination).resolve()
    root.relative_to((Path.cwd()/'analysis/private').resolve())
    if root.exists():
        raise ValueError('Use a new private RPC evidence directory')
    client = load_client(runtime_directory)(address='127.0.0.1', timeout=2, retries=0)
    try:
        processes = client.process_list()
        matches = [(pid, info) for pid, info in processes.items() if info[0] == 0x00040000001b5000]
        if len(matches) != 1:
            raise ValueError('Expected exactly one running Ultra Sun process')
        pid, (title_id, name) = matches[0]
        client.set_process(pid)
        if client.get_process() != pid:
            raise ValueError('RPC process selection did not take effect')
        actual = client.read_memory(0x100050, 34)
        if actual != code[0x50:0x72]:
            raise ValueError('Loaded helper bytes differ from the selected code image')
        startup = client.read_memory(0x100024, 44)
        if startup != code[0x24:0x50]:
            raise ValueError('Loaded BSS or preserved startup literals differ from selected image')
        stats = client.perf_stats(reset=False)
        root.mkdir(parents=True)
        (root/'loaded-helper.bin').write_bytes(actual)
        (root/'loaded-startup.bin').write_bytes(startup)
        frame_info = None
        if screenshot:
            frame = client.screenshot(res_scale=1)
            if not frame.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('RPC frame is not a PNG')
            (root/'game-frame.png').write_bytes(frame)
            frame_info = {'file': 'game-frame.png', 'sha256': hashlib.sha256(frame).hexdigest(), 'size': len(frame)}
        report = {'client_sha256': CLIENT_SHA256, 'endpoint': '127.0.0.1:45987 UDP',
                  'title_id': f'{title_id:016x}', 'process_name': name, 'process_id': pid,
                  'code_sha256': code_hash, 'variant': known[code_hash],
                  'helper_address': '0x100050', 'helper_size': 34,
                  'loaded_helper_sha256': hashlib.sha256(actual).hexdigest(),
                  'loaded_helper_verified': True, 'performance': stats, 'frame': frame_info,
                  'startup_address': '0x100024', 'startup_size': 44,
                  'loaded_startup_sha256': hashlib.sha256(startup).hexdigest(),
                  'loaded_startup_verified': True,
                  'scope': 'Live selected-process bytes and optional rendered game frame; full gameplay not asserted'}
        (root/'observations.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        if movie_path:
            retain_replay_log(runtime_directory, movie_path, root)
        print(json.dumps(report, indent=2))
        return report
    finally:
        client.socket.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime_directory')
    parser.add_argument('code')
    parser.add_argument('destination')
    parser.add_argument('--no-screenshot', action='store_true')
    parser.add_argument('--movie', help='Bind a selected movie and byte-preserved runtime log to the RPC capture')
    args = parser.parse_args()
    try:
        probe(args.runtime_directory, args.code, args.destination, not args.no_screenshot, args.movie)
    except (TimeoutError, ConnectionResetError) as error:
        raise SystemExit(f'Azahar RPC is unavailable. Enable it before starting the game. Transport: {error}')
