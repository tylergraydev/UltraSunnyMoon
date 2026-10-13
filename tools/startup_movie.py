"""Generate/inspect a bounded Azahar 2126.2 startup input experiment.

Format follows pinned core/movie.cpp. Runtime polling synchronization and
visual progression must still be verified; a valid file alone proves neither.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

REVISION = '219d743a1e698101fe1ab8bef43e6563126c3c27'
TITLE_ID = 0x00040000001b5000
POLL_RATE = 234
BUTTONS = {name: 1 << bit for bit, name in enumerate(
    ('A', 'B', 'SELECT', 'START', 'RIGHT', 'LEFT', 'UP', 'DOWN',
     'R', 'L', 'X', 'Y', 'DEBUG', 'GPIO14'))}


def _integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{label} must be an integer in {low}..{high}')
    return value


def _seconds(value, label):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f'{label} must be finite seconds')
    return value


def _buttons(value):
    if type(value) is int:
        return _integer(value, 0, (1 << 14)-1, 'buttons')
    if not isinstance(value, list) or any(
            not isinstance(name, str) or name not in BUTTONS for name in value):
        raise ValueError('buttons must be a 14-bit mask or a list of uppercase button names')
    mask = 0
    for name in value:
        mask |= BUTTONS[name]
    return mask


def generate_plan(plan):
    """Generate paired pad/touch records from a bounded declarative plan.

    Half-open times round up to poll boundaries; pulse periods begin at the
    first event sample. Buttons combine by OR. Overlapping explicit circle
    and touch coordinates must agree. Runtime synchronization is not proven.
    """
    if not isinstance(plan, dict) or set(plan) - {
            'duration_seconds', 'movie_id', 'pulses', 'holds', 'touches'}:
        raise ValueError('Unknown plan fields or non-object plan')
    duration = _seconds(plan.get('duration_seconds'), 'duration_seconds')
    if not 0 < duration <= 3600:
        raise ValueError('duration_seconds must be greater than 0 and at most 3600')
    count = math.ceil(duration * POLL_RATE)
    movie_id = _integer(plan.get('movie_id'), 0, (1 << 64)-1, 'movie_id')
    events = {}
    allowed = {
        'pulses': {'period_samples', 'held_samples', 'buttons'},
        'holds': {'buttons', 'circle_x', 'circle_y'},
        'touches': {'x', 'y'},
    }
    for kind, fields in allowed.items():
        entries = plan.get(kind, [])
        if not isinstance(entries, list):
            raise ValueError(f'{kind} must be a list')
        events[kind] = []
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) - fields - {'start_seconds', 'end_seconds'}:
                raise ValueError(f'Unknown {kind} fields or non-object event')
            start = _seconds(entry.get('start_seconds'), 'start_seconds')
            end = _seconds(entry.get('end_seconds'), 'end_seconds')
            if not 0 <= start < end <= duration:
                raise ValueError('Event must have 0 <= start < end <= duration')
            first, last = math.ceil(start*POLL_RATE), math.ceil(end*POLL_RATE)
            if first == last:
                raise ValueError('Event must contain at least one poll sample')
            if kind == 'pulses':
                period = _integer(entry.get('period_samples'), 1, count, 'period_samples')
                held = _integer(entry.get('held_samples'), 1, period, 'held_samples')
                value = (_buttons(entry.get('buttons')), period, held)
            elif kind == 'holds':
                circle = None
                if 'circle_x' in entry or 'circle_y' in entry:
                    circle = (_integer(entry.get('circle_x', 0), -32768, 32767, 'circle_x'),
                              _integer(entry.get('circle_y', 0), -32768, 32767, 'circle_y'))
                value = (_buttons(entry.get('buttons', [])), circle)
            else:
                value = (_integer(entry.get('x'), 0, 65535, 'x'),
                         _integer(entry.get('y'), 0, 65535, 'y'))
            events[kind].append((first, last, value))
    for kind in ('holds', 'touches'):
        entries = events[kind]
        for index, (first, last, value) in enumerate(entries):
            coordinates = value[1] if kind == 'holds' else value
            if coordinates is None:
                continue
            for other_first, other_last, other_value in entries[:index]:
                other = other_value[1] if kind == 'holds' else other_value
                if other is not None and max(first, other_first) < min(last, other_last) and coordinates != other:
                    raise ValueError(f'Conflicting {kind} coordinates overlap')
    header = bytearray(generate()[:256])
    struct.pack_into('<Q', header, 40, movie_id)
    struct.pack_into('<Q', header, 84, count)
    body = bytearray()
    for sample in range(count):
        buttons, circle, touch = 0, (0, 0), (0, 0, 0)
        for first, last, (mask, period, held) in events['pulses']:
            if first <= sample < last and (sample-first) % period < held:
                buttons |= mask
        for first, last, (mask, coordinates) in events['holds']:
            if first <= sample < last:
                buttons |= mask
                if coordinates is not None:
                    circle = coordinates
        for first, last, coordinates in events['touches']:
            if first <= sample < last:
                touch = (*coordinates, 1)
        body.extend(struct.pack('<BHhh', 0, buttons, *circle))
        body.extend(struct.pack('<BHHBB', 1, *touch, 0))
    return bytes(header+body)


def generate(seconds=180, a_start=15, a_end=75):
    header = bytearray(256)
    header[:4] = b'CTM\x1b'
    struct.pack_into('<Q', header, 4, TITLE_ID)
    header[12:32] = bytes.fromhex(REVISION)
    struct.pack_into('<QQ', header, 32, 1791763200, 2)
    author = b'UltraSunnyMoon startup test'
    header[48:48+len(author)] = author
    struct.pack_into('<IQq', header, 80, 1, POLL_RATE*seconds, 0)
    body = bytearray()
    for sample in range(POLL_RATE*seconds):
        # Integer sample boundaries: A for 59 polls every 702 polls, from
        # second a_start inclusive through second a_end exclusive. Neutral touch.
        held = int(a_start*POLL_RATE <= sample < a_end*POLL_RATE and sample % (3*POLL_RATE) < 59)
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


def verify_log(text, expected_movie_id=None):
    if 'Loaded Movie, ID:' not in text:
        raise ValueError('No loaded playback evidence')
    if expected_movie_id is not None and f'Loaded Movie, ID: {expected_movie_id:016X}' not in text:
        raise ValueError('Loaded movie ID differs from selected movie')
    if any(marker in text for marker in ('out of sync', 'Failed to playback movie', 'Playback file does not have valid header', 'different version of Citra', 'Movie <Error>')):
        raise ValueError('Movie error or synchronization failure in log')
    return {'loaded': True, 'completed': 'Playback finished' in text, 'input_type_desync_errors': 0,
            'scope': 'No type mismatch in retained log through capture; not proof of complete determinism or later playback'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', help='New private output directory')
    parser.add_argument('--seconds', type=int, help='Movie horizon in seconds (default 180, the retained proof)')
    parser.add_argument('--a-end', type=int, help='Second at which A pulses stop (default 75, the retained proof)')
    parser.add_argument('--plan', type=Path, help='JSON input plan; cannot combine with --seconds or --a-end')
    args = parser.parse_args()
    root = Path(args.destination).resolve()
    root.relative_to((Path.cwd()/'analysis/private').resolve())
    if args.plan and (args.seconds is not None or args.a_end is not None):
        parser.error('--plan cannot combine with --seconds or --a-end')
    seconds = args.seconds if args.seconds is not None else 180
    a_end = args.a_end if args.a_end is not None else 75
    plan_bytes = args.plan.read_bytes() if args.plan else None
    if plan_bytes is None and not 15 < a_end < seconds <= 3600:
        parser.error('--a-end must fall after second 15 and before a horizon of at most 3600 seconds')
    movie = generate_plan(json.loads(plan_bytes)) if plan_bytes is not None else generate(seconds, 15, a_end)
    root.mkdir(parents=True, exist_ok=False)
    proof = inspect(movie)
    proof['generator_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if plan_bytes is None:
        proof['sequence'] = f'{seconds} seconds; neutral pad/touch except A pulses from 15 to {a_end} seconds, every 3 seconds for 59 polls; capture before completion'
    else:
        proof['plan_sha256'] = hashlib.sha256(plan_bytes).hexdigest()
        proof['plan_file'] = 'plan.json'
        proof['movie_id'] = struct.unpack_from('<Q', movie, 40)[0]
        proof['sequence'] = 'Declarative plan; half-open times round up to poll boundaries; pulse phase starts at event start'
        (root/'plan.json').write_bytes(plan_bytes)
    (root/'startup.ctm').write_bytes(movie)
    (root/'movie.json').write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps(proof, indent=2))
