"""Bind BSS selection to standalone code and retained compilation/execution receipts."""
import json
from pathlib import Path

from compile_helper import standalone_helper
from rebuild_module import digest


def validate(object_data, receipt, code, header):
    payload = standalone_helper(object_data, 'ultrasun_clear_bss', thumb=False)
    comparison, behavior = receipt['compilation'], receipt['behavior']
    for name in ('compilation', 'behavior'):
        if receipt[name+'_sha256'] != digest(json.dumps(receipt[name], sort_keys=True).encode()):
            raise ValueError('BSS retained receipt was modified')
    object_hash = digest(object_data)
    source_hash = digest(Path('src/runtime/clear_bss.c').read_bytes())
    profiles = [p for p in comparison['profiles'] if p['object'] == receipt['object_name']]
    if len(payload) != 36 or len(profiles) != 1:
        raise ValueError('BSS object extent or compilation selection differs')
    profile = profiles[0]
    for record in (comparison, behavior):
        if (record['source_sha256'], record['code_sha256'], record['exheader_sha256']) != (source_hash, digest(code), digest(header)):
            raise ValueError('BSS receipt source or target differs')
    if (profile['object_sha256'], profile['text_sha256'], profile['compiled_size']) != (object_hash, digest(payload), 36):
        raise ValueError('BSS compilation receipt object differs')
    if receipt['object_sha256'] != object_hash or behavior['object_sha256'] != object_hash:
        raise ValueError('BSS behavior receipt object differs')
    if (comparison['entry'], comparison['mode']) != ('0x100024', 'arm'):
        raise ValueError('BSS compilation entry differs')
    if not comparison['compiler']['sha256'] or not comparison['compiler']['backend_sha256'] or not profile['command']:
        raise ValueError('BSS compiler identity missing')
    if (comparison['original_with_literals_sha256'] != digest(code[0x24:0x48]) or
            behavior['harness_sha256'] != digest(Path('tools/verify_bss_behavior.py').read_bytes())):
        raise ValueError('BSS evidence identity differs')
    expected_cases = [{'pattern': 0xa5}, {'pattern': 0xff}, {'pattern': 0},
                      {'pattern': None, 'thumb_return': True}]
    if (behavior['cases_passed'] != 4 or behavior['cpu_model'] != 'ARM11 MPCore' or
            [c['case'] for c in behavior['cases']] != expected_cases or
            not all(c['passed'] is True for c in behavior['cases']) or
            behavior['bounds_verified_against_exheader'] is not True or
            (behavior['entry'], behavior['mode'], behavior['bss_start'], behavior['bss_end_exclusive']) !=
            ('0x100024', 'arm', '0x6a3d48', '0x6d3f04')):
        raise ValueError('BSS behavior receipt coverage differs')
    for case in behavior['cases']:
        result = case['result']
        if (result['word_writes'], result['cleared_bytes'], result['thumb_return']) != (49263, 197052, case['case'].get('thumb_return', False)) or not all(result[k] is True for k in ('canaries_preserved', 'callee_saved_preserved', 'stack_unchanged')):
            raise ValueError('BSS behavior result differs')
    policy = 'exact' if payload == code[0x24:0x48] else 'behavior-tested-nonmatching'
    if receipt['policy'] != policy:
        raise ValueError('BSS replacement policy differs')
    return payload


def select(path, code, header, allow_nonmatching):
    path = Path(path)
    data = path.read_bytes()
    payload = standalone_helper(data, 'ultrasun_clear_bss', thumb=False)
    receipt = {'object_name': path.name, 'object_sha256': digest(data),
               'compilation': json.loads((path.parent/'comparison.json').read_text()),
               'behavior': json.loads((path.parent/'behavior.json').read_text()),
               'policy': 'exact' if payload == code[0x24:0x48] else 'behavior-tested-nonmatching'}
    for name in ('compilation', 'behavior'):
        receipt[name+'_sha256'] = digest(json.dumps(receipt[name], sort_keys=True).encode())
    validate(data, receipt, code, header)
    if receipt['policy'] != 'exact' and not allow_nonmatching:
        raise ValueError('Nonmatching BSS requires --allow-nonmatching')
    return receipt
