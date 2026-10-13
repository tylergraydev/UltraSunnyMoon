"""Generate/inspect a bounded Azahar 2126.2 startup input experiment.

Format follows pinned core/movie.cpp. Runtime polling synchronization and
visual progression must still be verified; a valid file alone proves neither.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

REVISION = '219d743a1e698101fe1ab8bef43e6563126c3c27'
TITLE_ID = 0x00040000001b5000
POLL_RATE = 234


def generate():
    header = bytearray(256)
    header[:4] = b'CTM\x1b'
    struct.pack_into('<Q', header, 4, TITLE_ID)
    header[12:32] = bytes.fromhex(REVISION)
    struct.pack_into('<QQ', header, 32, 1791763200, 2)
    author = b'UltraSunnyMoon startup test'
    header[48:48+len(author)] = author
    struct.pack_into('<IQq', header, 80, 1, POLL_RATE*180, 0)
    body = bytearray()
    for sample in range(POLL_RATE*180):
        # Integer sample boundaries: A for 59 polls every 702 polls, from
        # second 15 inclusive through second 75 exclusive. Neutral touch.
        held = int(15*POLL_RATE <= sample < 75*POLL_RATE and sample % (3*POLL_RATE) < 59)
        body.extend(struct.pack('<BHhh', 0, held, 0, 0))
        body.extend(struct.pack('<BHHBB', 1, 0, 0, 0, 0))
    return bytes(header+body)


def inspect(data):
    if len(data) <= 256 or data[:4] != b'CTM\x1b' or (len(data)-256) % 14:
        raise ValueError('Movie header or paired record extent differs')
    if struct.unpack_from('<Q', data, 4)[0] != TITLE_ID or data[12:32].hex() != REVISION:
        raise ValueError('Movie target or revision differs')
    pads = (len(data)-256)//14
    if struct.unpack_from('<Q', data, 84)[0] != pads:
        raise ValueError('Movie input count differs')
    for offset in range(256, len(data), 14):
        if data[offset] != 0 or data[offset+7] != 1:
            raise ValueError('Movie record order differs')
    return {'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data),
            'title_id': f'{TITLE_ID:016x}', 'revision': REVISION,
            'pad_samples': pads, 'controller_records': pads*2,
            'nominal_seconds': pads/POLL_RATE,
            'scope': 'Static file format/count checks; runtime synchronization and progression require evidence'}


def verify_log(text):
    if 'Loaded Movie, ID:' not in text:
        raise ValueError('No loaded playback evidence')
    if any(marker in text for marker in ('out of sync', 'Failed to playback movie', 'Playback file does not have valid header', 'different version of Citra', 'Movie <Error>')):
        raise ValueError('Movie error or synchronization failure in log')
    return {'loaded': True, 'completed': 'Playback finished' in text, 'input_type_desync_errors': 0,
            'scope': 'No type mismatch in retained log through capture; not proof of complete determinism or later playback'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', help='New private output directory')
    args = parser.parse_args()
    root = Path(args.destination).resolve()
    root.relative_to((Path.cwd()/'analysis/private').resolve())
    root.mkdir(parents=True, exist_ok=False)
    movie = generate()
    proof = inspect(movie)
    proof['generator_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    proof['sequence'] = '180 seconds; neutral pad/touch except A pulses from 15 to 75 seconds, every 3 seconds for 59 polls; capture before completion'
    (root/'startup.ctm').write_bytes(movie)
    (root/'movie.json').write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps(proof, indent=2))
