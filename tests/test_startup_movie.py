from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]/'tools'))
from startup_movie import generate, inspect, verify_log


class StartupMovieTests(unittest.TestCase):
    def test_source_owned_generated_sequence(self):
        movie = generate()
        proof = inspect(movie)
        self.assertEqual(proof['pad_samples'], 42120)
        self.assertEqual(proof['nominal_seconds'], 180)
        for sample, held in ((0, 0), (3510, 1), (3568, 1), (3569, 0), (17550, 0)):
            self.assertEqual(struct.unpack_from('<H', movie, 256+sample*14+1)[0], held)

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
