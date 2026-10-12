"""Verify QSettings defaults and configuration preservation on source fixtures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell configuration tool')
class RpcConfigurationTests(unittest.TestCase):
    def test_real_qsettings_marker_and_legacy_marker_are_enabled_with_backup(self):
        project = Path(__file__).parents[1]
        private = project/'analysis/private'
        private.mkdir(parents=True, exist_ok=True)
        for marker in (chr(92), chr(92)*2):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory(dir=private) as temporary:
                root = Path(temporary).resolve()
                root.relative_to(private.resolve())
                profile = root/'profile'
                (profile/'user/config').mkdir(parents=True)
                exe = profile/'azahar.exe'
                exe.write_bytes(b'source-owned non-executable fixture')
                (root/'runtime.json').write_text(json.dumps({'profiles': [{'name': 'fixture',
                    'executable': str(exe), 'executable_sha256': hashlib.sha256(exe.read_bytes()).hexdigest()}]}))
                config = profile/'user/config/qt-config.ini'
                original = '[Debugging]\nenable_rpc_server'+marker+'default=true\nenable_rpc_server=false\nkeep_this_setting=42\n'
                config.write_bytes(original.encode())
                result = subprocess.run(['powershell', '-NoProfile', '-File', str(project/'tools/configure-runtime-rpc.ps1'),
                                '-RuntimeDirectory', str(root)], cwd=project, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
                expected = '[Debugging]\nenable_rpc_server'+chr(92)+'default=false\nenable_rpc_server=true\nkeep_this_setting=42\n'
                self.assertEqual(config.read_bytes(), expected.encode())
                backups = list(config.parent.glob('qt-config.ini.before-rpc-*'))
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_bytes(), original.encode())


if __name__ == '__main__':
    unittest.main()
