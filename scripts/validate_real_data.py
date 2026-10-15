"""Analyze supplied predominantly capacitive spectra using sign-majority import.

Integration/robustness check, not ground-truth validation of physical spectra.
"""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
import hashlib
import json
import time
from drt_analyzer.data.importers import load_spectrum
from drt_analyzer.analysis.pipeline import analyze, auto_settings
from drt_analyzer.export.tables import export_xlsx, export_txt_bundle


def main():
    root = Path(__file__).resolve().parents[1]
    files = sorted((root/"data_test").glob("*.txt"))
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    pairs, records = [], []
    output = root/"artifacts"/"real_data_validation"
    output.mkdir(parents=True, exist_ok=True)
    for index, path in enumerate(files, 1):
        start = time.perf_counter()
        try:
            raw = load_spectrum(path)
            variant = analyze(raw, auto_settings())
            pairs.append((raw, variant))
            row = {"file": path.name, "points": len(raw.frequency), "rp_ohm": variant.rp_total,
                   "relative_rms": variant.quality["relative_rms"], "peaks": len(variant.peaks),
                   "lambda": variant.lambda_value, "kk": variant.kk.status,
                   "im_convention": raw.info.im_convention, "warnings": list(variant.warnings),
                   "seconds": time.perf_counter()-start}
        except Exception as exc:
            row = {"file": path.name, "error": str(exc)}
        records.append(row)
        print(f"{index}/{len(files)} {path.name}: {row.get('error', 'calculated')}", flush=True)
    unchanged = all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest for p, digest in before.items())
    report = {"source_count": len(files), "success_count": len(pairs), "source_hashes_unchanged": unchanged,
              "sign_assumption": "Predominantly capacitive spectra: negative nonzero-sign majority = Im; positive majority = -Im; ties use header.",
              "results": records}
    (output/"report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    export_xlsx(output/"real_data_results.xlsx", pairs)
    export_txt_bundle(output/"txt", pairs)
    assert unchanged, "Source measurements changed"
    assert len(pairs) == len(files), "Some spectra failed; inspect report.json"


if __name__ == "__main__":
    main()
