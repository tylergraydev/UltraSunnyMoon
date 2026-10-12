"""Create a synthetic locally relocated CRO view using a pinned pipeline reader.

This is not a complete runtime loader. Imports and unsupported relocation types
are rejected; runtime load addresses remain unknown. Original files stay intact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

PIPELINE_REVISION = '621bbce909ad2f9c551563c7443ed80c0123fe77'


def load_reader(directory):
    import subprocess
    actual = subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'], text=True).strip()
    if actual != PIPELINE_REVISION:
        raise ValueError('Pipeline reader revision differs from the pinned version')
    sys.path.insert(0, str(Path(directory).resolve()))
    from ctrtype import CRO
    from util import BinaryReader
    return CRO, BinaryReader


def describe(cro):
    return {'declared_size':cro.cro_size, 'header_bss_size':cro.bss_size,
            'segments':[{'index':i,'type':segment.type.name,'offset':hex(segment.off),'size':segment.size}
                        for i,segment in enumerate(cro.segment_table.obj)],
            'named_exports':len(cro.named_export_table.obj), 'named_imports':len(cro.named_import_table.obj),
            'import_modules':len(cro.import_module_table.obj), 'internal_relocations':len(cro.internal_relocs.obj),
            'import_relocations':len(cro.import_relocations.obj)}


def build(module, output, reader_directory, base=0x100000):
    CRO, BinaryReader = load_reader(reader_directory)
    original = Path(module).read_bytes()
    cro = CRO.from_reader(BinaryReader(Path(module).name, original))
    if Path(module).suffix == '.crs':
        raise ValueError('Static CRS describes absolute main-image segments; do not rebase it as a CRO')
    if cro.named_import_table.obj or cro.indexed_import_table.obj or cro.anon_import_table.obj or cro.import_relocations.obj:
        raise ValueError('Cross-module imports are unsupported in this initial local view')
    if len(original) != cro.cro_size:
        raise ValueError('Module size differs from the header')
    segments = cro.segment_table.obj
    relocated = bytearray(original)
    patches = []
    for relocation in cro.internal_relocs.obj:
        source = segments[relocation.seg_off.index]
        position = source.off + relocation.seg_off.off
        if relocation.seg_off.off+4 > source.size or position+4 > len(original):
            raise ValueError('Relocation target leaves a file-backed segment')
        symbol_segment = relocation.misc[0]
        addend = struct.unpack_from('<I', relocation.misc, 3)[0]
        symbol_base = base + segments[symbol_segment].off
        kind = int(relocation.type)
        if kind == 0:
            continue
        if kind in (2,38):
            value = symbol_base+addend
        elif kind == 3:
            value = symbol_base+addend-(base+position)
        else:
            raise ValueError(f'Unsupported internal relocation type {kind}')
        value &= 0xffffffff
        struct.pack_into('<I', relocated, position, value)
        patches.append({'offset':position,'type':kind,'symbol_segment':symbol_segment,'addend':addend,
                        'original_word':struct.unpack_from('<I',original,position)[0],'relocated_word':value})
    active = [segment for segment in segments if segment.size]
    for segment in active:
        if segment.type.name == 'BSS' or segment.off+segment.size > len(original):
            raise ValueError('Non-file-backed segments require a fuller loader')
    entry = base + active[0].off
    ident = b'\x7fELF'+bytes([1,1,1,0])+bytes(8)
    elf = struct.pack('<16sHHIIIIIHHHHHH',ident,2,40,1,entry,52,0,0x05000000,52,32,len(active),0,0,0)
    for segment in active:
        flags = {'TEXT':5,'RODATA':4,'DATA':6}[segment.type.name]
        elf += struct.pack('<IIIIIIII',1,0x1000+segment.off,base+segment.off,base+segment.off,
                           segment.size,segment.size,flags,0x1000)
    elf += bytes(0x1000-len(elf)) + relocated
    destination = Path(output)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(elf)
    destination.with_suffix('.relocated').write_bytes(relocated)
    report = describe(cro) | {'source_sha256':hashlib.sha256(original).hexdigest(),
             'relocated_sha256':hashlib.sha256(relocated).hexdigest(),'elf_sha256':hashlib.sha256(elf).hexdigest(),
             'entry':hex(entry),'synthetic_base':hex(base),'patches':patches,
             'scope':'synthetic static local relocation; runtime addresses and lifecycle are not established'}
    destination.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module')
    parser.add_argument('output')
    parser.add_argument('--reader',default='.local/pipeline-reference')
    args = parser.parse_args()
    print(json.dumps(build(args.module,args.output,args.reader),indent=2))
