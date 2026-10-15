import csv
import re
from pathlib import Path
from .settings import metadata


def safe_cell(value):
    # Prevent filenames and free-text headers becoming executable Excel formulas.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'"+value
    return value


def write_txt(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerows([[safe_cell(v) for v in row] for row in rows])


def summary_rows(pairs):
    max_peaks = max((len(v.peaks) for _, v in pairs), default=0)
    header = ["File", "Rs (Ohm)", "Rp total (Ohm)", "Lambda"]
    for i in range(1, max_peaks+1):
        header.append(f"Peak {i} Rp (Ohm)")
    rows = [header]
    for raw, v in pairs:
        row = [raw.name, v.rs_ohm, v.rp_total, v.lambda_value]
        for peak in v.peaks:
            row.append(peak.rp_ohm)
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
    meta.append(["File", "Parameter", "Value"])
    for n, (raw, v) in enumerate(pairs, 1):
        for title, rows in detail_tables(raw, v).items():
            sheet = wb.create_sheet(f"{n} {title}"[:31])
            for row in rows:
                sheet.append([safe_cell(value.item() if hasattr(value, "item") else value) for value in row])
        for key, value in settings_rows(metadata(raw, v)):
            meta.append([safe_cell(raw.name), safe_cell(key), safe_cell(value)])
    for sheet in wb.worksheets:
        _format_sheet(sheet)
    wb.save(path)


def settings_rows(values, prefix=""):
    for key, value in values.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            yield from settings_rows(value, name)
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                yield from settings_rows({str(index+1): item}, name)
        else:
            yield name, value


def export_txt_bundle(directory, pairs):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    pairs = list(pairs)
    write_txt(directory/"summary.txt", summary_rows(pairs))
    for index, (raw, v) in enumerate(pairs, 1):
        stem = re.sub(r'[<>:"/\\|?*]', "_", Path(raw.name).stem)[:70]
        prefix = f"{index:03d}_{stem}_{v.id[:8]}"
        for name, rows in detail_tables(raw, v).items():
            write_txt(directory/f"{prefix}_{name.replace(' ', '_')}.txt", rows)
        write_txt(directory/f"{prefix}_settings.txt", [["Parameter", "Value"], *settings_rows(metadata(raw, v))])
