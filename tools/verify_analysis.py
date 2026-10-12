"""Compare a REA function dossier with independent Capstone decoding.

Evidence and decoded retail instructions stay in ignored local files.
Install capstone==5.0.7 in a local virtual environment before running.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_LITTLE_ENDIAN
from capstone.arm import ARM_OP_MEM, ARM_REG_PC


def read_json(path):
    data = Path(path).read_bytes()
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    result = json.loads(data.decode(encoding))
    # Support both direct CLI Evidence and retained MCP CallToolResult envelopes.
    if "content" in result and "evidence_id" not in result:
        structured = result.get("structuredContent")
        if structured is not None:
            return structured
        text_blocks = [item["text"] for item in result["content"] if item["type"] == "text"]
        if len(text_blocks) != 1:
            raise ValueError("Expected one JSON Evidence text block")
        return json.loads(text_blocks[0])
    return result


def verify(code_path, evidence_path, address, elf_path=None):
    evidence = read_json(evidence_path)
    if "error" in evidence:
        raise ValueError("REA reported an error; no function evidence is available")
    result = evidence["raw_result"]["value"]
    body = result["procedure"]["body"]
    code = Path(code_path).read_bytes()
    elf = Path(elf_path or Path(evidence_path).parent / "base-pilot.elf").read_bytes()
    if hashlib.sha256(elf).hexdigest() != evidence["subject"]["digest"]["sha256"]:
        raise ValueError("Evidence target digest does not match the selected ELF")
    if elf[0x1000:] != code:
        raise ValueError("Analysis ELF payload differs from the selected original code")
    if int(result["procedure"]["address"], 16) != address:
        raise ValueError("Evidence resolves to a different function entry")
    decoder = Cs(CS_ARCH_ARM, CS_MODE_ARM | CS_MODE_LITTLE_ENDIAN)
    decoder.detail = True
    decoded = []
    for area in body["ranges"]:
        start, end = int(area["start"], 16), int(area["end"], 16) + 1
        if start < 0x100000 or end > 0x100000 + len(code):
            raise ValueError("Function range lies outside the selected code image")
        decoded.extend(decoder.disasm(code[start-0x100000:end-0x100000], start))
    independent_addresses = [item.address for item in decoded]
    rea_assembly = result["assembly"]
    rea_addresses = [int(re.match(r"0x([0-9a-f]+):", line, re.I)[1], 16)
                     for line in rea_assembly]
    if independent_addresses != rea_addresses:
        raise ValueError("REA/Capstone instruction address coverage differs")
    # Compare semantic opcodes, allowing assembler aliases for branches/conditions.
    aliases = {"bcc": "blo", "bcs": "bhs", "stmia": "stm", "strcc": "strlo",
               "b": "b", "bx": "bx", "ldr": "ldr", "mov": "mov", "cmp": "cmp"}
    def normalize_operands(text):
        text = text.lower().replace("#", "")
        text = re.sub(r"\s+", "", text)
        return re.sub(r"(?<![a-z0-9_])(?:0x[0-9a-f]+|[0-9]+)",
                      lambda match: str(int(match[0], 16 if match[0].startswith("0x") else 10)), text)
    for item, line in zip(decoded, rea_assembly):
        rea_opcode, rea_operands = line.split(":", 1)[1].strip().split(maxsplit=1)
        rea_opcode = rea_opcode.lower()
        if aliases.get(item.mnemonic, item.mnemonic) != aliases.get(rea_opcode, rea_opcode):
            raise ValueError(f"Opcode differs at {item.address:#x}: {item.mnemonic} / {rea_opcode}")
        independent_operands = item.op_str
        if item.mnemonic == "ldr" and item.operands[1].type == ARM_OP_MEM and item.operands[1].mem.base == ARM_REG_PC:
            literal_address = item.address + 8 + item.operands[1].mem.disp
            independent_operands = f"{item.reg_name(item.operands[0].reg)}, [{literal_address:#x}]"
        if normalize_operands(independent_operands) != normalize_operands(rea_operands):
            raise ValueError(f"Operands differ at {item.address:#x}")
    # This pilot is deliberately scoped to the ARM startup zeroing helper.
    if address != 0x100024 or len(decoded) != 7:
        raise ValueError("Pilot verification expects the seven-instruction startup helper")
    zero_start, zero_end = struct.unpack_from("<II", code, 0x40)
    if zero_end < zero_start or (zero_end-zero_start) % 4:
        raise ValueError("Invalid zeroing range")
    incoming = result["incoming_references"]
    if not any(int(item["source_address"], 16) == 0x100000 and
               int(item["target_address"], 16) == address and item["kind"].get("call")
               for item in incoming):
        raise ValueError("Expected startup caller reference is missing")
    reference_targets = {int(item["target_address"], 16) for item in result["outgoing_references"]}
    if not {0x100040, 0x100044}.issubset(reference_targets):
        raise ValueError("Expected literal references are missing")
    return {"evidence_id": evidence["evidence_id"], "entry": hex(address),
            "code_sha256": hashlib.sha256(code).hexdigest(),
            "instruction_addresses_match": True, "instruction_opcodes_match": True,
            "instruction_operands_match": True, "startup_caller_reference_verified": True,
            "literal_references_verified": True,
            "evidence_target_digest_verified": True, "original_code_payload_verified": True,
            "instructions": len(decoded), "zero_start": hex(zero_start),
            "zero_end_exclusive": hex(zero_end), "zero_bytes": zero_end-zero_start,
            "independent_decoder": "Capstone 5.0.7", "scope": "static analysis; no execution or compiled replacement",
            "operand_verification": "Capstone operands compared with REA; PC-relative literal loads resolved to absolute addresses; branch aliases normalized."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code")
    parser.add_argument("evidence")
    parser.add_argument("--address", type=lambda value: int(value, 0), default=0x100024)
    parser.add_argument("--elf", help="Analysis ELF; defaults to base-pilot.elf next to the evidence")
    args = parser.parse_args()
    print(json.dumps(verify(args.code, args.evidence, args.address, args.elf), indent=2))
