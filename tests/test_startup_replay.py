import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]/'tools'))
import verify_startup_replay
from startup_movie import generate, inspect, verify_log
from probe_runtime_rpc import retain_replay_log


class ReplayReceiptTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.movie = self.root/'test.ctm'
        self.movie.write_bytes(generate())
        self.runs = [self.root/'original', self.root/'rebuilt']
        for run in self.runs:
            run.mkdir()
            log = b'Loaded Movie, ID: 0000000000000002\n'
            (run/'replay-log.txt').write_bytes(log)
            receipt = dict(verify_log(log.decode()), movie=inspect(self.movie.read_bytes()),
                           log_sha256=hashlib.sha256(log).hexdigest())
            (run/'replay.json').write_text(json.dumps(receipt))

    def check(self):
        with patch.object(verify_startup_replay, 'verify_rpc', return_value={'live_helpers_verified': 2}):
            return verify_startup_replay.verify(*self.runs, 'original-code', 'rebuilt-code', self.movie)

    def test_same_movie_and_bounded_log_accepted(self):
        self.assertEqual(self.check()['movie']['pad_samples'], 42120)

    def test_changed_movie_receipt_rejected(self):
        path = self.runs[1]/'replay.json'
        receipt = json.loads(path.read_text())
        receipt['movie']['sha256'] = 'wrong'
        path.write_text(json.dumps(receipt))
        with self.assertRaises(ValueError):
            self.check()

    def test_later_desynchronization_rejected(self):
        path = self.runs[1]/'replay-log.txt'
        path.write_bytes(path.read_bytes()+b'Your playback will be out of sync\n')
        with self.assertRaises(ValueError):
            self.check()

    def test_crlf_log_bytes_preserved_and_verifiable(self):
        runtime = self.root/'runtime'
        log_dir = runtime/'user/log'
        log_dir.mkdir(parents=True)
        log = b'Loaded Movie, ID: 0000000000000002\r\n'
        (log_dir/'azahar_log.txt').write_bytes(log)
        retain_replay_log(runtime, self.movie, self.runs[1])
        self.assertEqual((self.runs[1]/'replay-log.txt').read_bytes(), log)
        self.check()

    def test_different_loaded_movie_id_rejected(self):
        runtime = self.root/'runtime'
        log_dir = runtime/'user/log'
        log_dir.mkdir(parents=True)
        (log_dir/'azahar_log.txt').write_bytes(b'Loaded Movie, ID: 0000000000000003\n')
        with self.assertRaises(ValueError):
            retain_replay_log(runtime, self.movie, self.runs[1])


if __name__ == '__main__':
    unittest.main()
