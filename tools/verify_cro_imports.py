"""Cross-check resolve_cro_imports.py receipts with the pinned pipeline CRO reader.

The pipeline reader parses the same tables through a different implementation.
This verifier requires exact agreement on every named import (name, batch
offset, batch records) and export (name -> segment/offset), recomputes every
expected word from static.crs, and confirms the original patch words are zero.
It does not apply patches or prove the runtime loader's behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from module_view import load_reader


def verify(crs_path, receipt_dir, module_paths, reader):
    CRO, BinaryReader = load_reader(reader)
    crs_raw = Path(crs_path).read_bytes()
    crs = CRO.from_reader(BinaryReader('static.crs', crs_raw))
    pipeline_exports = {str(e.name.obj): (e.seg_off.index, e.seg_off.off) for e in crs.named_export_table.obj}
    receipt_dir = Path(receipt_dir)
    summary = json.loads((receipt_dir/'resolution.json').read_text(encoding='utf-8'))
    if summary['static_crs_sha256'] != hashlib.sha256(crs_raw).hexdigest():
        raise ValueError('static.crs digest differs from the receipt')
    if summary['static_named_exports'] != len(pipeline_exports):
        raise ValueError('export count differs from the pipeline reader')
    checked_names = checked_words = 0
    for path in module_paths:
        raw = Path(path).read_bytes()
        name = Path(path).name
        receipt = json.loads((receipt_dir/(name+'.imports.json')).read_text(encoding='utf-8'))
        module = CRO.from_reader(BinaryReader(name, raw))
        if module.cro_size != len(raw):
            raise ValueError(f'{name}: declared size differs')
        expected = [item for item in module.named_import_table.obj]
        if len(expected) != len(receipt):
            raise ValueError(f'{name}: named import count differs')
        for entry, got in zip(expected, receipt):
            if str(entry.name.obj) != got['name'] or entry.name.off != got['name_offset']:
                raise ValueError(f'{name}: import name differs')
            if entry.off != got['batch_offset']:
                raise ValueError(f'{name}: batch offset differs for {got["name"]}')
            batch = []
            position = entry.off
            while True:
                index = (position-module.import_relocations.off)//12
                record = module.import_relocations.obj[index]
                batch.append(record)
                if record.misc[0]:
                    break
                position += 12
            if len(batch) != len(got['relocations']):
                raise ValueError(f'{name}: batch length differs for {got["name"]}')
            for record, item in zip(batch, got['relocations']):
                if record.seg_off.index != item['segment'] or record.seg_off.off != item['offset']:
                    raise ValueError(f'{name}: patch location differs')
                if int(record.type) != item['type'] or struct.unpack_from('<I', record.misc, 3)[0] != item['addend']:
                    raise ValueError(f'{name}: relocation type or addend differs')
                position_in_file = module.segment_table.obj[record.seg_off.index].off+record.seg_off.off
                if position_in_file != item['patch_file_offset']:
                    raise ValueError(f'{name}: patch file offset differs')
                if struct.unpack_from('<I', raw, position_in_file)[0] != 0:
                    raise ValueError(f'{name}: original patch word is not zero')
                checked_words += 1
            if got['status'] == 'resolved':
                if pipeline_exports.get(got['name']) != (got['static_segment'], got['static_offset']):
                    raise ValueError(f'{name}: export target differs for {got["name"]}')
                for item in got['relocations']:
                    segment = crs.segment_table.obj[got['static_segment']]
                    address = segment.off+got['static_offset']
                    if item['expected_word'] != (address+item['addend']) & 0xFFFFFFFF:
                        raise ValueError(f'{name}: expected word differs')
            checked_names += 1
    return {'static_crs_sha256': hashlib.sha256(crs_raw).hexdigest(), 'modules': len(module_paths),
            'named_imports_checked': checked_names, 'patch_words_checked': checked_words,
            'scope': 'static parse agreement only; no runtime loader behavior is verified'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('crs')
    parser.add_argument('receipt_dir')
    parser.add_argument('modules', nargs='+')
    parser.add_argument('--reader', default='.local/pipeline-reference')
    args = parser.parse_args()
    print(json.dumps(verify(args.crs, args.receipt_dir, args.modules, args.reader), indent=2))
    sys.exit(0)
