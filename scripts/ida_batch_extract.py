"""IDA batch-mode extractor for authorized CTF binaries.

Usage from IDA:
    idat64 -A -S"ida_batch_extract.py OUTPUT.json" TARGET
"""

import hashlib
import json
import os
import sys

import ida_auto
import ida_entry
import ida_funcs
import ida_hexrays
import ida_ida
import ida_nalt
import ida_segment
import idautils
import idc


def _hex(value):
    return f"0x{int(value):x}"


def _imports():
    rows = []

    def collect(ea, name, ordinal):
        rows.append(
            {
                "address": _hex(ea),
                "name": name or "",
                "ordinal": int(ordinal),
                "module": current_module[0],
            }
        )
        return True

    current_module = [""]
    for index in range(ida_nalt.get_import_module_qty()):
        current_module[0] = ida_nalt.get_import_module_name(index) or f"module_{index}"
        ida_nalt.enum_import_names(index, collect)
    return rows


def _entries():
    rows = []
    for index in range(ida_entry.get_entry_qty()):
        ordinal = ida_entry.get_entry_ordinal(index)
        ea = ida_entry.get_entry(ordinal)
        rows.append(
            {
                "ordinal": int(ordinal),
                "address": _hex(ea),
                "name": ida_entry.get_entry_name(ordinal) or idc.get_name(ea) or "",
            }
        )
    return rows


def _segments():
    rows = []
    for ea in idautils.Segments():
        segment = ida_segment.getseg(ea)
        rows.append(
            {
                "name": ida_segment.get_segm_name(segment),
                "start": _hex(segment.start_ea),
                "end": _hex(segment.end_ea),
                "permissions": int(segment.perm),
            }
        )
    return rows


def _strings(limit=20000):
    strings = idautils.Strings()
    strings.setup(strtypes=[0, 1])
    rows = []
    for item in strings:
        text = str(item)
        if text:
            rows.append({"address": _hex(item.ea), "length": int(item.length), "text": text})
        if len(rows) >= limit:
            break
    return rows


def _functions(limit=10000, decompile_limit=16):
    """Enumerate every function, but decompile only the highest-value subset.

    Large PE files often contain thousands of CRT/runtime functions.  Asking
    Hex-Rays to decompile all of them makes a batch triage job take minutes or
    hours, while CTF analysis normally needs entry points, named functions and
    functions that reference interesting strings first.
    """
    rows = []
    hexrays_ready = False
    try:
        hexrays_ready = bool(ida_hexrays.init_hexrays_plugin())
    except Exception:
        pass

    entry_eas = set()
    for index in range(ida_entry.get_entry_qty()):
        ordinal = ida_entry.get_entry_ordinal(index)
        entry_eas.add(ida_entry.get_entry(ordinal))

    string_ref_counts = {}
    strings = idautils.Strings()
    strings.setup(strtypes=[0, 1])
    for item in strings:
        for xref in idautils.XrefsTo(item.ea):
            owner = ida_funcs.get_func(xref.frm)
            if owner is not None:
                string_ref_counts[owner.start_ea] = string_ref_counts.get(owner.start_ea, 0) + 1

    for ea in idautils.Functions():
        function = ida_funcs.get_func(ea)
        if function is None:
            continue
        flags = idc.get_func_flags(ea)
        row = {
            "address": _hex(ea),
            "end": _hex(function.end_ea),
            "size": int(function.end_ea - function.start_ea),
            "name": ida_funcs.get_func_name(ea) or idc.get_name(ea) or "",
            "flags": int(flags),
            "library": bool(flags & ida_funcs.FUNC_LIB),
            "thunk": bool(flags & ida_funcs.FUNC_THUNK),
            "string_refs": int(string_ref_counts.get(ea, 0)),
        }
        rows.append(row)
        if len(rows) >= limit:
            break

    def candidate_score(row):
        ea = int(row["address"], 16)
        name = row["name"]
        score = 0
        if ea in entry_eas:
            score += 100000
        if name and not name.startswith(("sub_", "nullsub_", "loc_", "j_")):
            score += 10000
        score += min(row["string_refs"], 100) * 100
        if 16 <= row["size"] <= 0x10000:
            score += 10
        return score

    candidates = [row for row in rows if not row["library"] and not row["thunk"]]
    candidates.sort(key=lambda row: (-candidate_score(row), int(row["address"], 16)))
    for row in candidates[:decompile_limit]:
        row["decompile_selected"] = True
        if not hexrays_ready:
            continue
        try:
            row["pseudocode"] = str(ida_hexrays.decompile(int(row["address"], 16)))
        except Exception as exc:
            row["decompile_error"] = str(exc)
    return rows


def main():
    ida_auto.auto_wait()
    output_path = idc.ARGV[1] if len(idc.ARGV) > 1 else os.path.abspath("ida-analysis.json")
    input_path = ida_nalt.get_input_file_path()
    with open(input_path, "rb") as handle:
        sha256 = hashlib.sha256(handle.read()).hexdigest()

    payload = {
        "input": input_path,
        "sha256": sha256,
        "processor": ida_ida.inf_get_procname(),
        "bitness": 64 if ida_ida.inf_is_64bit() else 32 if ida_ida.inf_is_32bit_exactly() else 16,
        "image_base": _hex(ida_nalt.get_imagebase()),
        "entries": _entries(),
        "segments": _segments(),
        "imports": _imports(),
        "strings": _strings(),
        "functions": _functions(),
    }
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(f"[ida-batch] wrote {output_path}")
    idc.qexit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"[ida-batch] fatal: {type(error).__name__}: {error}", file=sys.stderr)
        idc.qexit(1)
