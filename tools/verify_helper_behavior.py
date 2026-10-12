"""Compare original and compiled Thumb helpers under isolated ARM execution.

This is bounded ABI/behavior testing, not 3DS gameplay or exception validation.
"""
import argparse
import hashlib
import json
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, __version__
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                              UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
                              UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
                              UC_ARM_REG_R12, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC)
from unicorn.arm_const import UC_ARM_REG_CPSR, UC_CPU_ARM_11MPCORE
from verify_rebuild import elf_text
from rebuild_main import CODE_SHA256

ENTRY, CALLBACK, RETURN, ARRAY, STACK = 0x100050, 0x110000, 0x120000, 0x200000, 0x300000
PRESERVED = (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
             UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11)


def execute(payload, *, count, stride, null_constructor=False, arm_callback=False, null_array=False):
    machine = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    machine.ctl_set_cpu_model(UC_CPU_ARM_11MPCORE)
    for address, size in ((0x100000, 0x1000), (CALLBACK, 0x1000), (RETURN, 0x1000),
                          (ARRAY, 0x1000), (STACK, 0x1000)):
        machine.mem_map(address, size)
    machine.mem_write(ENTRY, payload)
    # Source-owned callback stubs: bx lr in Thumb or ARM mode.
    machine.mem_write(CALLBACK, bytes.fromhex('1eff2fe1' if arm_callback else '7047'))
    machine.mem_write(ARRAY, bytes([0xa5])*0x1000)
    array = 0 if null_array else ARRAY+0x100
    callback = 0 if null_constructor else CALLBACK+(0 if arm_callback else 1)
    sp = STACK+0x800
    for register, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3),
                                (array, callback, stride, count)):
        machine.reg_write(register, value)
    saved = {register: 0xabc000+index for index, register in enumerate(PRESERVED)}
    for register, value in saved.items():
        machine.reg_write(register, value)
    machine.reg_write(UC_ARM_REG_SP, sp)
    machine.reg_write(UC_ARM_REG_LR, RETURN+1)
    calls, outside_stack_writes = [], []

    def callback_hook(uc, address, size, data):
        if address != CALLBACK:
            return
        if uc.reg_read(UC_ARM_REG_SP) % 8:
            raise ValueError('Callback SP violates eight-byte alignment')
        pointer = uc.reg_read(UC_ARM_REG_R0)
        calls.append(pointer)
        if not ARRAY <= pointer < ARRAY+0x1000:
            raise ValueError('Unexpected constructor pointer')
        uc.mem_write(pointer, bytes([len(calls)]))
        # Return a different pointer and destroy permitted caller-saved values.
        for register in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R12):
            uc.reg_write(register, 0xdead0000)
        uc.reg_write(UC_ARM_REG_CPSR, (uc.reg_read(UC_ARM_REG_CPSR) & 0x0fffffff) | 0xf0000000)

    def write_hook(uc, access, address, size, value, data):
        if not STACK <= address < address+size <= STACK+0x1000:
            outside_stack_writes.append((address, size))

    machine.hook_add(UC_HOOK_CODE, callback_hook)
    machine.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    machine.emu_start(ENTRY+1, RETURN, count=10000)
    if machine.reg_read(UC_ARM_REG_PC) != RETURN:
        raise ValueError('Function did not return within instruction bound')
    if machine.reg_read(UC_ARM_REG_SP) != sp or any(machine.reg_read(r) != value for r, value in saved.items()):
        raise ValueError('Callee-saved registers or stack were not restored')
    if outside_stack_writes:
        raise ValueError('Helper wrote outside its stack')
    expected_calls = [] if null_constructor else [array+i*stride for i in range(count)]
    expected_memory = bytearray([0xa5]*0x1000)
    for index, pointer in enumerate(expected_calls, 1):
        expected_memory[pointer-ARRAY] = index
    if calls != expected_calls or machine.reg_read(UC_ARM_REG_R0) != array:
        raise ValueError('Callback order/count or returned array differs')
    memory = bytes(machine.mem_read(ARRAY, 0x1000))
    if memory != expected_memory:
        raise ValueError('Array mutations or surrounding canaries differ')
    return {'calls': calls, 'returned_array': array, 'memory_sha256': hashlib.sha256(memory).hexdigest(),
            'callee_saved_preserved': True, 'callback_stack_aligned': True}


def verify(code_path, object_path, image_path=None):
    code = Path(code_path).read_bytes()
    if hashlib.sha256(code).hexdigest() != CODE_SHA256:
        raise ValueError('Original image differs from pinned base')
    original, compiled = code[0x50:0x72], elf_text(Path(object_path).read_bytes())
    image = Path(image_path).read_bytes() if image_path else None
    if image is not None:
        if len(image) != len(code) or image[:0x50] != code[:0x50] or image[0x72:] != code[0x72:] or image[0x50:0x72] != compiled:
            raise ValueError('Integrated image contains unexpected bytes or a different helper')
    cases = [dict(count=0, stride=4), dict(count=1, stride=4), dict(count=5, stride=7),
             dict(count=3, stride=0), dict(count=0, stride=4, null_array=True),
             dict(count=0xffffffff, stride=0xffffffff, null_constructor=True, null_array=True),
             dict(count=5, stride=4, null_constructor=True),
             dict(count=5, stride=9, arm_callback=True)]
    results = []
    for case in cases:
        retail = execute(original, **case)
        candidate = execute(compiled, **case)
        if retail != candidate:
            raise ValueError('Original and compiled behavior differs')
        if image is not None and execute(image[0x50:0x72], **case) != retail:
            raise ValueError('Integrated helper behavior differs')
        results.append({'case': case, 'passed': True})
    return {'cases_passed': len(results), 'cases': results,
            'unicorn_version': __version__, 'cpu_model': 'ARM11 MPCore',
            'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'integrated_cases_passed': len(results) if image is not None else 0,
            'integrated_image_sha256': hashlib.sha256(image).hexdigest() if image is not None else None,
            'code_sha256': CODE_SHA256, 'object_sha256': hashlib.sha256(Path(object_path).read_bytes()).hexdigest(),
            'exact_byte_match': original == compiled,
            'scope': 'Bounded isolated ARM/Thumb behavior; not exception handling or full-game runtime proof'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('code')
    parser.add_argument('object')
    parser.add_argument('--report', help='Write proof to a private file')
    parser.add_argument('--image', help='Also execute the helper extracted from the rebuilt image')
    args = parser.parse_args()
    proof = verify(args.code, args.object, args.image)
    if args.report:
        destination = Path(args.report).resolve()
        destination.relative_to((Path.cwd()/'analysis/private').resolve())
        destination.write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps(proof, indent=2))
