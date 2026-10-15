# Verification — 2026-10-15

## 0.2.0 functional update

- Full suite: **91 passed**. Includes inclusive frequency selection and rejection
  of invalid/too-small windows; selected-grid KK/tau/exports; sign-majority and
  ties; per-file Auto ranges; Del in list/history vs text editors; modeless help;
  correct Nyquist and both DRT-axis cursor frequencies; hidden comparison curves.
- Source executable smoke passed with all 0.2.0 features: 69/81 points selected,
  history/spectrum removal, parameter-help dialog and frequency readouts.
- Source images, range exports and JSON: `artifacts/source_smoke_0_2/`.
- Sign assumption: each full source is predominantly capacitive. A positive
  nonzero majority denotes -Im; a negative majority denotes Im. No sign dialog.
- Removing session entries/variants never removes original measurement files.
- All 35 real spectra were revalidated under automatic sign-majority import;
  source hashes remained unchanged. A 1–10000 Hz window was checked on NOVA
  (21/41 points), ERIS 850C (41/60), and DD hole 12 (42/50), including KK and
  preservation of complete sources. See `artifacts/range_integration/report.json`.
- Fixed the QtCore startup failure: an unrelated Poppler `icuuc.dll` with
  versioned `_78` symbols was collected through the build host PATH, while Qt
  imports the unversioned Windows ICU API. The Qt6Core binary itself matched
  the installed package. Clean dependency discovery now uses Python/venv/OS
  paths only. The bundle source check verified 186 native dependencies.
- The corrected EXE passed its full smoke check (exit 0), including all six new
  features, scientific reconstruction and PNG/SVG/XLSX/CSV/JSON exports.
- Packaging regression tests reject DLLs from unrelated directories, including
  roots with deceptively similar path prefixes. Early Qt imports are logged;
  smoke output is isolated per build and stdout/stderr are captured.
- Final build workflow completed successfully: **91 passed**, 186 native
  dependencies verified, frozen EXE smoke exit 0. Build evidence:
  `artifacts/portable_smoke_DRTAnalyzer_20261015_165356_352/`.
- Native Windows Qt platform was also checked with Python environment variables
  cleared and PATH restricted to Windows directories. Exit 0; the process
  loaded Python and QtCore from `_internal` and `icuuc.dll` from Windows System32.
  Evidence and screenshots: `artifacts/portable_windows_0_2/`.
- Final 0.2.0 executable SHA-256:
  `4CCF3BFF08A01E2AD9961EE358F1C94BA64F29B3ABB2821A5B6898915D6A71F4`.

The results below document the original 0.1.0 baseline. Its executable hash,
directory size and sign-confirmation workflow are historical, not the 0.2.0 build.

Environment: Windows 11 x64; Python 3.14.8; NumPy 2.5.4; SciPy 1.18.1;
PySide6 6.12.0; pyqtgraph 0.14.0; openpyxl 3.1.5; PyInstaller 6.22.3.

## 0.1.0 baseline checks

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
