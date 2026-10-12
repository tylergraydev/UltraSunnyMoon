"""Independently verify an ARM or Thumb function dossier against local code.

This verifies the selected function, not global disassembly coverage or behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN
from capstone.arm import ARM_OP_MEM, ARM_REG_PC
from verify_analysis import read_json


def canonical(opcode, operands):
    opcode = {"cpy": "mov", "bcc": "blo", "bcs": "bhs", "strcc": "strlo", "ldrcc": "ldrlo"}.get(opcode, opcode)
    if opcode == "push":
        opcode, operands = "stmdb", "sp!," + operands
    elif opcode == "pop":
        opcode, operands = "ldmia", "sp!," + operands
    operands = operands.lower().replace("#", "")
    operands = re.sub(r"(?<![a-z0-9_])(?:0x[0-9a-f]+|[0-9]+)",
                      lambda match: str(int(match[0], 16 if match[0].startswith("0x") else 10)), operands)
    operands = re.sub(r"\s+", "", operands)
    operands = operands.replace(',0]', ']') # Explicit zero memory displacement.
    return opcode, operands


def verify(code_path, elf_path, evidence_path, mode):
    evidence = read_json(evidence_path)
    if "error" in evidence:
        raise ValueError("REA reported an error")
    code, elf = Path(code_path).read_bytes(), Path(elf_path).read_bytes()
    if hashlib.sha256(elf).hexdigest() != evidence["subject"]["digest"]["sha256"] or elf[0x1000:] != code:
        raise ValueError("Evidence target or original code payload differs")
    value = evidence["raw_result"]["value"]
    body = value["procedure"]["body"]
    decoder = Cs(CS_ARCH_ARM, CS_MODE_LITTLE_ENDIAN | (CS_MODE_THUMB if mode == "thumb" else CS_MODE_ARM))
    decoder.detail = True
    decoded = []
    for area in body["ranges"]:
        start, end = int(area["start"], 16), int(area["end"], 16) + 1
        if start < 0x100000 or end > 0x100000 + len(code):
            raise ValueError("Function body leaves the original code image")
        instructions = list(decoder.disasm(code[start-0x100000:end-0x100000], start))
        if sum(item.size for item in instructions) != end-start:
            raise ValueError("Independent decoder did not cover the complete function range")
        decoded.extend(instructions)
    assembly = value["assembly"]
    if len(assembly) != len(decoded):
        raise ValueError("Instruction counts differ")
    for independent, observed in zip(decoded, assembly):
        match = re.fullmatch(r"0x([0-9a-f]+):\s+(\S+)\s*(.*)", observed, re.I)
        if not match or int(match[1], 16) != independent.address:
            raise ValueError("Instruction addresses differ")
        operands = independent.op_str
        if independent.mnemonic == "ldr" and independent.operands[1].type == ARM_OP_MEM and independent.operands[1].mem.base == ARM_REG_PC:
            pc = ((independent.address + 4) & ~3) if mode == "thumb" else independent.address + 8
            operands = f"{independent.reg_name(independent.operands[0].reg)}, [{pc + independent.operands[1].mem.disp:#x}]"
        if canonical(independent.mnemonic, operands) != canonical(match[2].lower(), match[3]):
            raise ValueError(f"Decoded instruction differs at {independent.address:#x}")
    return {"entry": value["procedure"]["address"], "mode": mode,
            "instructions": len(decoded), "function_bytes": body["total_bytes"],
            "evidence_id": evidence["evidence_id"], "target_digest_verified": True,
            "selected_payload_verified": True, "addresses_opcodes_operands_match": True,
            "scope": "selected static function; no runtime or global coverage claim"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code")
    parser.add_argument("elf")
    parser.add_argument("evidence")
    parser.add_argument("--mode", choices=("arm", "thumb"), required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.code, args.elf, args.evidence, args.mode), indent=2))
