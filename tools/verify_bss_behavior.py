"""Compare startup BSS clearing under ARM11 execution; no game runtime claim."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from unicorn import (Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_WRITE,
                     UC_PROT_READ, UC_PROT_EXEC, __version__)
from unicorn.arm_const import (UC_CPU_ARM_11MPCORE, UC_ARM_REG_R0, UC_ARM_REG_R1,
                              UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4,
                              UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
                              UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10,
                              UC_ARM_REG_R11, UC_ARM_REG_R12, UC_ARM_REG_SP,
                              UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_CPSR)
from compile_helper import standalone_helper
from rebuild_main import CODE_SHA256, EXHEADER_SHA256

ENTRY, RETURN, STACK = 0x100024, 0x120000, 0x300000
BSS_START, BSS_END = 0x6a3d48, 0x6d3f04
MEMORY_START, MEMORY_END = 0x6a3000, 0x6d5000
PRESERVED = (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
             UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_bounds(code, header):
    if digest(code) != CODE_SHA256 or digest(header) != EXHEADER_SHA256:
        raise ValueError('Inputs differ from the pinned base')
    address, pages, logical_size = struct.unpack_from('<III', header, 0x30)
    size = struct.unpack_from('<I', header, 0x3c)[0]
    if (address + logical_size, address + logical_size + size) != (BSS_START, BSS_END):
        raise ValueError('Logical data/BSS bounds differ from the recovered routine')
    if struct.unpack_from('<II', code, 0x40) != (BSS_START, BSS_END):
        raise ValueError('Original literal bounds differ')
    if BSS_START % 4 or size % 4 or logical_size > pages * 0x1000:
        raise ValueError('Invalid word alignment or data extent')


def execute(payload, *, pattern=0xa5, thumb_return=False):
    """Validate each store and the whole region, including both boundary canaries."""
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    machine.ctl_set_cpu_model(UC_CPU_ARM_11MPCORE)
    for address, size in ((0x100000, 0x1000), (RETURN, 0x1000),
                          (STACK, 0x1000), (MEMORY_START, MEMORY_END-MEMORY_START)):
        machine.mem_map(address, size)
    machine.mem_write(ENTRY, payload)
    machine.mem_protect(0x100000, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
    initial = bytearray([0x5a]) * (MEMORY_END-MEMORY_START)
    size = BSS_END-BSS_START
    contents = (bytes((i*73 + (i >> 8)) & 255 for i in range(size))
                if pattern is None else bytes([pattern])*size)
    initial[BSS_START-MEMORY_START:BSS_END-MEMORY_START] = contents
    machine.mem_write(MEMORY_START, bytes(initial))
    stack = bytes([0xc3])*0x1000
    machine.mem_write(STACK, stack)
    sp = STACK+0x800
    machine.reg_write(UC_ARM_REG_SP, sp)
    machine.reg_write(UC_ARM_REG_LR, RETURN+int(thumb_return))
    for i, register in enumerate((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                                   UC_ARM_REG_R3, UC_ARM_REG_R12)):
        machine.reg_write(register, 0xdead0000+i)
    saved = {r: 0xabc000+i for i, r in enumerate(PRESERVED)}
    for register, value in saved.items():
        machine.reg_write(register, value)
    machine.reg_write(UC_ARM_REG_CPSR, machine.reg_read(UC_ARM_REG_CPSR) | 0xf0000000)
    writes = 0

    def write_hook(uc, access, address, width, value, data):
        nonlocal writes
        if address != BSS_START + writes*4 or width != 4 or value != 0:
            raise ValueError('Store order, extent, width or value differs from BSS contract')
        if address+width > BSS_END:
            raise ValueError('Write exceeds BSS boundary')
        writes += 1

    machine.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    machine.emu_start(ENTRY, RETURN, count=300000)
    if machine.reg_read(UC_ARM_REG_PC) != RETURN:
        raise ValueError('Function did not return within instruction bound')
    if bool(machine.reg_read(UC_ARM_REG_CPSR) & 0x20) != thumb_return:
        raise ValueError('Return instruction mode differs')
    if machine.reg_read(UC_ARM_REG_SP) != sp or any(machine.reg_read(r) != v for r, v in saved.items()):
        raise ValueError('Callee-saved registers or stack were not restored')
    if writes != size//4:
        raise ValueError('Function did not clear every BSS word')
    expected = initial[:]
    expected[BSS_START-MEMORY_START:BSS_END-MEMORY_START] = bytes(size)
    memory = bytes(machine.mem_read(MEMORY_START, len(expected)))
    if memory != expected or bytes(machine.mem_read(STACK, len(stack))) != stack:
        raise ValueError('BSS contents, surrounding canaries or stack differ')
    return {'word_writes': writes, 'cleared_bytes': size, 'memory_sha256': digest(memory),
            'canaries_preserved': True, 'callee_saved_preserved': True,
            'stack_unchanged': True, 'thumb_return': thumb_return}


def verify(code_path, header_path, object_path):
    code, header, obj = (Path(p).read_bytes() for p in (code_path, header_path, object_path))
    check_bounds(code, header)
    compiled = standalone_helper(obj, 'ultrasun_clear_bss', thumb=False)
    cases = [{'pattern': 0xa5}, {'pattern': 0xff}, {'pattern': 0},
             {'pattern': None, 'thumb_return': True}]
    results = []
    for case in cases:
        original = execute(code[0x24:0x48], **case)
        candidate = execute(compiled, **case)
        if original != candidate:
            raise ValueError('Original and compiled BSS behavior differs')
        results.append({'case': case, 'result': candidate, 'passed': True})
    return {'entry': hex(ENTRY), 'mode': 'arm', 'bss_start': hex(BSS_START),
            'bss_end_exclusive': hex(BSS_END), 'bounds_verified_against_exheader': True,
            'cases_passed': len(results), 'cases': results, 'cpu_model': 'ARM11 MPCore',
            'unicorn_version': __version__, 'code_sha256': CODE_SHA256,
            'exheader_sha256': EXHEADER_SHA256, 'object_sha256': digest(obj),
            'source_sha256': digest(Path('src/runtime/clear_bss.c').read_bytes()),
            'harness_sha256': digest(Path(__file__).read_bytes()),
            'exact_byte_match_including_literals': compiled == code[0x24:0x48],
            'integrated': False,
            'scope': 'Fixed-target isolated BSS clearing and ABI checks; no game execution proof'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('code')
    parser.add_argument('exheader')
    parser.add_argument('object')
    parser.add_argument('--report')
    args = parser.parse_args()
    proof = verify(args.code, args.exheader, args.object)
    if args.report:
        destination = Path(args.report).resolve()
        destination.relative_to((Path.cwd()/'analysis/private').resolve())
        destination.write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps(proof, indent=2))
