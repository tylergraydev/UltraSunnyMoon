from pathlib import Path
import copy
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]/'tools'))
from startup_movie import generate, generate_plan, inspect, verify_log


class StartupMovieTests(unittest.TestCase):
    def test_source_owned_generated_sequence(self):
        movie = generate()
        proof = inspect(movie)
        self.assertEqual(proof['pad_samples'], 42120)
        self.assertEqual(proof['nominal_seconds'], 180)
        self.assertEqual(proof['sha256'], 'a1fbd184dfc17f999e01fc089c5d9572ca6d06aa28cfe147eba32992dbf40fba')
        for sample, held in ((0, 0), (3510, 1), (3568, 1), (3569, 0), (17550, 0)):
            self.assertEqual(struct.unpack_from('<H', movie, 256+sample*14+1)[0], held)

    def test_plan_combines_buttons_movement_and_touch_with_boundaries(self):
        plan = {'duration_seconds': 2, 'movie_id': 19,
                'pulses': [{'start_seconds': 0.5, 'end_seconds': 1.5,
                            'period_samples': 4, 'held_samples': 2, 'buttons': ['A', 'START']}],
                'holds': [{'start_seconds': 0, 'end_seconds': 1, 'buttons': ['RIGHT'],
                           'circle_x': -32768, 'circle_y': 32767},
                          {'start_seconds': 0.5, 'end_seconds': 1.5, 'buttons': 1024}],
                'touches': [{'start_seconds': 0.5, 'end_seconds': 1, 'x': 65535, 'y': 42}]}
        movie = generate_plan(plan)
        self.assertEqual(inspect(movie)['pad_samples'], 468)
        self.assertEqual(struct.unpack_from('<Q', movie, 40)[0], 19)
        for sample, mask, circle, touch in (
                (116, 16, (-32768, 32767), (0, 0, 0)),
                (117, 16 | 1024 | 9, (-32768, 32767), (65535, 42, 1)),
                (119, 16 | 1024, (-32768, 32767), (65535, 42, 1)),
                (121, 16 | 1024 | 9, (-32768, 32767), (65535, 42, 1)),
                (234, 1024 | 9, (0, 0), (0, 0, 0)),
                (351, 0, (0, 0), (0, 0, 0))):
            with self.subTest(sample=sample):
                self.assertEqual(struct.unpack_from('<BHhh', movie, 256+sample*14), (0, mask, *circle))
                self.assertEqual(struct.unpack_from('<BHHBB', movie, 263+sample*14), (1, *touch, 0))

    def test_fractional_poll_boundaries_round_up(self):
        movie = generate_plan({'duration_seconds': 0.015, 'movie_id': 0,
                               'holds': [{'start_seconds': 0.001, 'end_seconds': 0.01, 'buttons': ['B']}]})
        self.assertEqual(inspect(movie)['pad_samples'], 4)
        self.assertEqual([struct.unpack_from('<H', movie, 257+sample*14)[0]
                          for sample in range(4)], [0, 2, 2, 0])

    def test_plan_can_reproduce_retained_sequence(self):
        movie = generate_plan({'duration_seconds': 180, 'movie_id': 2,
                               'pulses': [{'start_seconds': 15, 'end_seconds': 75,
                                           'period_samples': 702, 'held_samples': 59, 'buttons': ['A']}]})
        self.assertEqual(movie, generate())

    def test_plan_rejects_invalid_inputs(self):
        base = {'duration_seconds': 2, 'movie_id': 19}
        invalid = [None, {}, {**base, 'typo': 1}]
        invalid += [{**base, 'duration_seconds': value}
                    for value in (0, -1, 3601, 10**1000, float('inf'), float('nan'), True, '2')]
        invalid += [{**base, 'movie_id': value} for value in (-1, 1 << 64, True, 1.5)]
        invalid += [{**base, 'holds': value} for value in (None, {}, [None])]
        hold = {'start_seconds': 0, 'end_seconds': 1, 'buttons': ['A']}
        changes = [{'start_seconds': -1}, {'end_seconds': 3}, {'end_seconds': 0},
                   {'start_seconds': float('nan')}, {'end_seconds': True},
                   {'end_seconds': 0.001, 'start_seconds': 0.0001},
                   {'buttons': ['a']}, {'buttons': ['ZL']}, {'buttons': 16384},
                   {'buttons': True}, {'circle_x': -32769}, {'circle_y': 32768},
                   {'circle_x': 1.1}, {'typo': 0}]
        invalid += [{**base, 'holds': [{**hold, **change}]} for change in changes]
        pulse = {**hold, 'period_samples': 4, 'held_samples': 2}
        invalid += [{**base, 'pulses': [{**pulse, **change}]} for change in (
            {'period_samples': 0}, {'held_samples': 0}, {'held_samples': 5},
            {'period_samples': True}, {'period_samples': 469})]
        touch = {'start_seconds': 0, 'end_seconds': 1, 'x': 1, 'y': 2}
        invalid += [{**base, 'touches': [{**touch, **change}]} for change in (
            {'x': -1}, {'y': 65536}, {'x': True}, {'y': 1.5})]
        for plan in invalid:
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                generate_plan(plan)

    def test_coordinate_overlap_requires_agreement(self):
        for kind, coordinates in (('holds', {'circle_x': 1, 'circle_y': 2}),
                                  ('touches', {'x': 1, 'y': 2})):
            first = {'start_seconds': 0, 'end_seconds': 1, **coordinates}
            second = {'start_seconds': 0.5, 'end_seconds': 1.5, **coordinates}
            plan = {'duration_seconds': 2, 'movie_id': 19, kind: [first, second]}
            generate_plan(plan)
            broken = copy.deepcopy(plan)
            broken[kind][1][next(iter(coordinates))] = 3
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'Conflicting'):
                generate_plan(broken)
            broken[kind][1]['start_seconds'] = 1
            generate_plan(broken)  # Adjacent differing coordinates are unambiguous.

    def test_cli_receipt_binds_exact_plan_and_generator(self):
        repo = Path(__file__).parents[1]
        source = repo/'tools/startup_movie.py'
        with tempfile.TemporaryDirectory(prefix='movie-plan-test-', dir=repo/'analysis/private') as temp:
            root = Path(temp)
            raw = b'{ "duration_seconds": 1, "movie_id": 19 }\n'
            plan = root/'input.json'
            plan.write_bytes(raw)
            destination = root/'output'
            subprocess.run([sys.executable, str(source), str(destination), '--plan', str(plan)],
                           cwd=repo, check=True, capture_output=True)
            proof = json.loads((destination/'movie.json').read_text())
            self.assertEqual((destination/'plan.json').read_bytes(), raw)
            self.assertEqual(proof['plan_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(proof['generator_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(proof['sha256'], inspect((destination/'startup.ctm').read_bytes())['sha256'])
            conflict = subprocess.run([sys.executable, str(source), str(root/'conflict'),
                                       '--plan', str(plan), '--seconds', '180'],
                                      cwd=repo, capture_output=True)
            self.assertNotEqual(conflict.returncode, 0)
            self.assertFalse((root/'conflict').exists())

    def test_extended_horizon_keeps_format_and_window(self):
        movie = generate(seconds=300, a_end=240)
        proof = inspect(movie)
        self.assertEqual(proof['pad_samples'], 234*300)
        self.assertEqual(proof['nominal_seconds'], 300)
        # A pulse at 15 s is kept; the window closes at 240 s, so 240 s+ is neutral.
        self.assertEqual(struct.unpack_from('<H', movie, 256+3510*14+1)[0], 1)
        self.assertEqual(struct.unpack_from('<H', movie, 256+(240*234+3)*14+1)[0], 0)
        # Final in-window sample is in the neutral part of its 702-poll cycle.
        self.assertEqual(struct.unpack_from('<H', movie, 256+(240*234-1)*14+1)[0], 0)

    def test_wrong_count_and_order_rejected(self):
        for offset in (84, 256, 263):
            data = bytearray(generate())
            data[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                inspect(data)

    def test_truncated_movie_rejected(self):
        with self.assertRaises(ValueError):
            inspect(generate()[:-1])

    def test_missing_load_and_desync_rejected(self):
        loaded = 'Loaded Movie, ID: 0000000000000002'
        valid = loaded+'\nPlayback finished'
        self.assertEqual(verify_log(valid)['input_type_desync_errors'], 0)
        self.assertFalse(verify_log(loaded)['completed'])
        for text in ('Playback finished', valid+'\nYour playback will be out of sync', valid+'\nThis movie was created on a different version of Citra'):
            with self.assertRaises(ValueError):
                verify_log(text)


if __name__ == '__main__':
    unittest.main()
