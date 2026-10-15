import csv
import json
import re
from pathlib import Path
from .settings import metadata, export_settings


def safe_cell(value):
    # Prevent filenames and free-text headers becoming executable Excel formulas.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'"+value
    return value


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerows([[safe_cell(v) for v in row] for row in rows])


def summary_rows(pairs):
    max_peaks = max((len(v.peaks) for _, v in pairs), default=0)
    header = ["File", "Rp total (Ohm)", "Peak count", "DRT method", "Lambda method", "Lambda",
              "RBF", "Shape epsilon (1/ln tau)", "Derivative order", "Relative RMS",
              "RMS Re (Ohm)", "RMS Im (Ohm)", "Lin-KK status", "Rs (Ohm)", "L (H)", "Warnings",
              "Used f min (Hz)", "Used f max (Hz)", "Source points", "Used points",
              "Requested f min (Hz)", "Requested f max (Hz)"]
    for i in range(1, max_peaks+1):
        header.extend([f"Peak {i} tau (s)", f"Peak {i} f (Hz)", f"Peak {i} Rp (Ohm)", f"Peak {i} edge"])
    rows = [header]
    for raw, v in pairs:
        row = [raw.name, v.rp_total, len(v.peaks), v.settings.method, v.settings.lambda_method,
               v.lambda_value, v.settings.rbf, v.shape_value, v.settings.derivative_order,
               v.quality["relative_rms"], v.quality["rms_real_ohm"], v.quality["rms_imag_ohm"],
               v.kk.status if v.kk else "Not run", v.rs_ohm, v.inductance_h, " | ".join(v.warnings),
               float(v.frequency.min()), float(v.frequency.max()), len(raw.frequency), len(v.frequency),
               v.settings.frequency_min_hz, v.settings.frequency_max_hz]
        for peak in v.peaks:
            row.extend([peak.tau_s, peak.frequency_hz, peak.rp_ohm, peak.edge])
        rows.append(row+[""]*(len(header)-len(row)))
    return rows


def detail_tables(raw, v):
    drt = [["Tau (s)", "Frequency (Hz)", "Gamma (Ohm per d ln tau)"]]
    import numpy as np
    drt.extend(zip(v.tau, 1/(2*np.pi*v.tau), v.gamma))
    z = [["Frequency (Hz)", "Re experimental (Ohm)", "Im experimental (Ohm)",
          "Re DRT (Ohm)", "Im DRT (Ohm)", "Relative residual Re", "Relative residual Im",
          "Re KK (Ohm)", "Im KK (Ohm)", "KK residual Re", "KK residual Im"]]
    for i, f in enumerate(v.frequency):
        row = [f, v.impedance[i].real, v.impedance[i].imag, v.reconstructed[i].real,
               v.reconstructed[i].imag, v.residuals[i].real, v.residuals[i].imag]
        row += [v.kk.reconstructed[i].real, v.kk.reconstructed[i].imag,
                v.kk.residuals[i].real, v.kk.residuals[i].imag] if v.kk else [None]*4
        z.append(row)
    peaks = [["Index", "Tau (s)", "Frequency (Hz)", "Gamma peak (Ohm)", "Rp (Ohm)",
              "Fraction", "Left tau (s)", "Right tau (s)", "Unresolved edge"]]
    for p in v.peaks:
        peaks.append([p.index, p.tau_s, p.frequency_hz, p.gamma_ohm, p.rp_ohm,
                      p.fraction, p.left_tau_s, p.right_tau_s, p.edge])
    source = [["Source row (1-based)", "Frequency (Hz)", "Re original (Ohm)", "Imaginary original (Ohm)"]]
    source.extend((i+1, f, re, im) for i, (f, re, im) in enumerate(zip(raw.frequency, raw.real, raw.imaginary_original)))
    selection = [["Lambda", "Selection score", "Residual norm (L-curve)", "Penalty norm (L-curve)"]]
    sel = v.lambda_selection
    for i, lam in enumerate(sel.lambdas):
        selection.append([lam, float(sel.scores[i]) if i < len(sel.scores) and np.isfinite(sel.scores[i]) else None,
                          float(sel.residual_norms[i]) if i < len(sel.residual_norms) else None,
                          float(sel.penalty_norms[i]) if i < len(sel.penalty_norms) else None])
    return {"DRT": drt, "Impedance": z, "Peaks": peaks, "Raw source": source, "Lambda selection": selection}


def _format_sheet(ws):
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="244A64")
    for column in ws.columns:
        length = max(len(str(c.value or "")) for c in list(column)[:100])
        ws.column_dimensions[get_column_letter(column[0].column)].width = min(60, max(15, length+2))
    for row in ws.iter_rows(min_row=2):
        for c in row:
            if isinstance(c.value, float):
                c.number_format = "0.000000E+00"


def export_xlsx(path, pairs):
    from openpyxl import Workbook
    pairs = list(pairs)
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    for row in summary_rows(pairs):
        ws.append([safe_cell(v) for v in row])
    meta = wb.create_sheet("Settings")
    meta.append(["File", "Parameter", "Value (JSON)"])
    for n, (raw, v) in enumerate(pairs, 1):
        for title, rows in detail_tables(raw, v).items():
            sheet = wb.create_sheet(f"{n} {title}"[:31])
            for row in rows:
                sheet.append([safe_cell(value.item() if hasattr(value, "item") else value) for value in row])
        for key, value in metadata(raw, v).items():
            # Split large JSON (e.g. scan arrays) into chunks below Excel's 32767-char limit.
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
            for chunk in range(0, max(1, len(encoded)), 30000):
                meta.append([safe_cell(raw.name), key if chunk == 0 else f"{key} continued", safe_cell(encoded[chunk:chunk+30000])])
    for sheet in wb.worksheets:
        _format_sheet(sheet)
    wb.save(path)


def export_csv_bundle(directory, pairs):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    pairs = list(pairs)
    write_csv(directory/"summary.csv", summary_rows(pairs))
    for index, (raw, v) in enumerate(pairs, 1):
        stem = re.sub(r'[<>:"/\\|?*]', "_", Path(raw.name).stem)[:70]
        prefix = f"{index:03d}_{stem}_{v.id[:8]}"
        for name, rows in detail_tables(raw, v).items():
            write_csv(directory/f"{prefix}_{name.replace(' ', '_')}.csv", rows)
        export_settings(directory/f"{prefix}_settings.json", raw, v)
