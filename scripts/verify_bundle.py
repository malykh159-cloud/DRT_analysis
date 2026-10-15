"""Reject native dependencies accidentally collected from unrelated PATH tools.

PyInstaller searches for binary dependencies and may select another tool's DLL
with the same basename. In particular, Poppler's icuuc.dll exports versioned
ICU symbols, whereas this Windows Qt build imports the unversioned OS ICU API.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import sys


def binary_records(value):
    if isinstance(value, (tuple, list)):
        if len(value) == 3 and isinstance(value[2], str) and value[2] in {"BINARY", "EXTENSION"}:
            yield tuple(value)
        else:
            for child in value:
                yield from binary_records(child)


def foreign_binaries(records, allowed_roots):
    roots = [Path(root).resolve() for root in allowed_roots]
    return [record for record in records
            if not any(Path(record[1]).resolve().is_relative_to(root) for root in roots)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="DRTAnalyzer")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    toc = root/"build"/args.name/"COLLECT-00.toc"
    records = list(binary_records(ast.literal_eval(toc.read_text(encoding="utf-8"))))
    if not records:
        raise RuntimeError("No native dependency records found; cannot verify the bundle.")
    roots = [root/".venv", Path(sys.base_prefix), Path(os.environ.get("SystemRoot", "C:/Windows"))]
    foreign = foreign_binaries(records, roots)
    report = {"binary_count": len(records), "allowed_roots": [str(p) for p in roots],
              "foreign_binaries": foreign, "passed": not foreign}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if foreign:
        raise RuntimeError("Unexpected native dependency sources: "+str(foreign))
    print(f"Verified {len(records)} native dependencies; no DLLs from unrelated PATH tools.")


if __name__ == "__main__":
    main()
