"""Preserve a manually launched Azahar run and extract narrow runtime evidence.

No window control or gameplay automation. Logs/configs stay private.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def collect(user_path, package_path, destination, screen=None, screen_source='user'):
    user, package = Path(user_path), Path(package_path).resolve()
    log = (user/'log/azahar_log.txt').read_bytes()
    config = (user/'config/qt-config.ini').read_bytes()
    text, config_text = log.decode('utf-8', errors='replace'), config.decode('utf-8', errors='replace')
    version = re.search(r'Azahar Version: ([^\r\n]+)', text)
    title = re.search(r'Program ID: ([0-9A-Fa-f]+)', text)
    recent = re.search(r'^Paths\\recentFiles=([^\r\n]+)', config_text, re.MULTILINE)
    if not version or not title or title[1].lower() != '00040000001b5000':
        raise ValueError('No Ultra Sun load/version evidence found')
    if not recent or Path(recent[1].split(',')[0]).resolve().as_posix().casefold() != package.as_posix().casefold():
        raise ValueError('Most recent runtime input does not match selected package')
    keys = ('Core_UseCpuJit', 'Core_CPUClockPercentage', 'Renderer_GraphicsAPI',
            'Renderer_UseHwShader', 'Renderer_UseShaderJit', 'Renderer_UseResolutionFactor',
            'Renderer_AsyncShaderCompilation', 'System_IsNew3ds', 'System_RegionValue')
    settings = {}
    for key in keys:
        matches = re.findall(re.escape(key)+r': ([^\r\n]+)', text)
        if matches:
            settings[key] = matches[-1]
    modules = [{'name': name, 'address': address.lower(), 'fixed_end': end.lower()}
               for name, address, end in re.findall(r'CRO "([^"]+)" loaded at (0x[0-9A-Fa-f]+), fixed_end=(0x[0-9A-Fa-f]+)', text)]
    package_hash = hashlib.sha256()
    with package.open('rb') as stream:
        while chunk := stream.read(8*1024*1024):
            package_hash.update(chunk)
    root = Path(destination).resolve()
    root.relative_to((Path.cwd()/'analysis/private').resolve())
    root.mkdir(parents=True, exist_ok=False)
    (root/'azahar_log.txt').write_bytes(log)
    (root/'qt-config.ini').write_bytes(config)
    custom = user/'config/custom/00040000001B5000.ini'
    if custom.exists():
        (root/'title-config.ini').write_bytes(custom.read_bytes())
    report = {'runtime_version': version[1], 'program_id': title[1].lower(),
              'package_sha256': package_hash.hexdigest(), 'config_sha256': hashlib.sha256(config).hexdigest(),
              'log_sha256': hashlib.sha256(log).hexdigest(), 'settings': settings,
              'loaded_modules': modules, 'user_reported_screen': screen if screen_source == 'user' else None,
              'screen_observation': {'description': screen, 'source': screen_source} if screen else None,
              'input_binding': 'user-profile recent-file record; no process memory attestation',
              'scope': 'Loader/config/module events and declared screen observation; live-byte proof is separate RPC evidence'}
    (root/'observations.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('user_directory')
    parser.add_argument('package')
    parser.add_argument('destination')
    parser.add_argument('--screen', help='Record a screen description with its declared observation source')
    parser.add_argument('--screen-source', choices=('user', 'agent-rpc-frame'), default='user')
    args = parser.parse_args()
    collect(args.user_directory, args.package, args.destination, args.screen, args.screen_source)
