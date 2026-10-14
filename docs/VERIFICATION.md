# Verification — 2026-10-15

Environment: Windows 11 x64; Python 3.14.8; NumPy 2.5.4; SciPy 1.18.1;
PySide6 6.12.0; pyqtgraph 0.14.0; openpyxl 3.1.5; PyInstaller 6.22.3.

## Completed checks

- `python -m pytest -q`: **64 passed**, 5.36 seconds in the final build run.
- Scientific checks: one/two RC systems, known tau and Rp, positive gamma,
  all RBFs/orders, analytical derivatives, noise, induction, reconstruction,
  every lambda criterion, finite-window quadrature and derivative penalty
  against independent adaptive integration, smoother against dense inverse.
- GUI checks: background result delivery, cancellation retaining previous
  snapshots, history and cached scan selection, PNG/SVG exports.
- Source smoke and portable smoke both passed: full Qt window, Undo/Redo,
  tables/JSON and all seven plots in PNG and SVG (14 figure files).
- Portable isolated smoke: PATH restricted to Windows directories; PYTHONHOME
  and PYTHONPATH cleared. Exit code 0. Loaded python314.dll and python3.DLL
  from `dist/DRTAnalyzer/_internal/`, confirmed through process modules.
- Source/portable synthetic Rp matched exactly: **100.43796596027559 Ohm**
  for true Rp=100 Ohm; two resolved peaks; relative RMS **0.008182631052037351**;
  Lin-KK Compatible. Numerical errors are finite-basis/discretization errors,
  not a claimed uncertainty interval.
- All **35/35** supplied TXT examples imported and analyzed; SHA-256 of source
  measurements unchanged. Total numerical analysis time approximately 10.9 s.
  Legacy positive Im was explicitly assumed to be -Im in the validation script.
- Lin-KK on the examples: 27 Compatible, 8 Review. Calculation success does not
  imply a scientifically adequate fit. Results/warnings are retained per file.
- Visual inspection of source and final portable screenshots: readable fonts,
  correct DRT marker positions, finite-window axes, two peak rows and restored
  Ready status after history navigation. SVG uses Qt native vector rendering.

## Artifacts

- `artifacts/source_smoke/`
- `artifacts/portable_smoke_DRTAnalyzer/`
- `artifacts/portable_isolated/`
- `artifacts/real_data_validation/report.json`
- `artifacts/real_data_validation/real_data_results.xlsx`
- `artifacts/real_data_validation/csv/`

Final executable SHA-256:
`260C4B9D7175F6EDA36600FF64BBC2A8572B2D42378DCB7B9571E512D706F9AC`.
Portable directory size approximately 239 MB; transfer the entire directory.

## Practical limits

The NOVA example has a large unfinished low-frequency tail. Its positive finite-
window DRT has about **14.8% relative RMS**, a lambda boundary warning and
significant boundary mass. Reported Rp is a window-dependent estimate; it must
not be mistaken for a fully resolved total polarization resistance. Compatible
Lin-KK and inadequate positive finite-window DRT can coexist.

No second Windows machine without Python was available. The self-contained
runtime was verified on this machine with isolated environment variables.
No full installed pyDRTtools numerical comparison was performed; independent
quadrature and matrix references were used. Bayesian DRT/uncertainty remain
unavailable. These limitations are also documented in README/MATHEMATICS.
