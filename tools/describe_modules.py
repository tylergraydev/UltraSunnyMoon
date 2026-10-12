"""Describe selected local modules and map CRS exports to the main executable."""
import argparse
import hashlib
import json
from pathlib import Path
from module_view import load_reader, describe


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', default='.local/pipeline-reference')
    args = parser.parse_args()
    CRO, BinaryReader = load_reader(args.reader)
    summaries = []
    exports = []
    for path in sorted(Path('extracted/base/modules').glob('*')):
        cro = CRO.from_reader(BinaryReader.from_path(path))
        summaries.append({'name':path.name, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} | describe(cro))
        if path.name == 'static.crs':
            for item in cro.named_export_table.obj:
                segment = cro.segment_table.obj[item.seg_off.index]
                value = segment.off + item.seg_off.off
                exports.append({'name':str(item.name.obj), 'segment':item.seg_off.index,
                                'encoded_address':hex(value), 'canonical_address':hex(value & ~1),
                                'thumb_bit':bool(value & 1)})
    output = Path('analysis/private')
    (output/'module-layouts.json').write_text(json.dumps(summaries,indent=2), encoding='utf-8')
    (output/'static-exports.json').write_text(json.dumps(exports,indent=2), encoding='utf-8')
    print(json.dumps({'selected_modules':len(summaries),'static_named_exports':len(exports)}))
