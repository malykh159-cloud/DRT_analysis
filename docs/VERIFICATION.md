# Verification — 2026-10-15

## 0.4.2 Bayesian Lambda Scan progress

- Complete regression suite: 129 passed (60.51 seconds).
- Reproduced on the reported private 60-point spectrum without modifying source
  data: a 20-transition probe used 633 reflections at lambda 5.6234e-5 versus
  36765 at lambda 1e-8. A wide scan cannot be timed by multiplying the cost of
  a single run at a different lambda.
- Fixed missing callback forwarding in lambda_scan/worker. The status now shows
  lambda index/value, chain, warm-up/sampling and diagnostics; percentages use
  fractional values. Global progress remains monotone across lambda boundaries.
- Added regression coverage for live progress before the first lambda completes,
  full Bayesian variants on all scan nodes, GUI responsiveness, cooperative Stop
  and preservation of the previous result. A real-spectrum Qt event-loop check
  observed first-chain status after about 3.4 s and stopped successfully.
- GUI checks use a well-conditioned lambda to isolate event delivery from
  expensive trajectories. Full frozen smoke also exercises scan progress.
- Model, numerical sampler, budgets, scan bounds, Tikhonov and import/export
  behavior remain unchanged. Screenshot: `artifacts/lambda_scan_progress_0_4_2/`.
- Portable build passed its 186-native-dependency audit and embedded scan smoke
  (`artifacts/portable_smoke_DRTAnalyzer_20261016_120542_276/`). Native Windows Qt
  smoke also passed with isolated PATH, including Bayesian scan live progress
  (`artifacts/scan_0_4_2_windows/`).

## 0.4.1 settings panel update

- Complete test suite: 127 passed (46.56 seconds), including help dialogs for all
  nine Bayesian controls, background calculation/Stop and Tikhonov regressions.
- Manual Qt check confirmed that folding/unfolding Frequency Range, Validation,
  Peaks and Regularization Advanced leaves AnalysisSettings unchanged; loading
  another settings snapshot preserves the user's display folding state.
- Inspected the compact panel and Advanced/help screenshots under
  `artifacts/settings_folds_0_4_1/`. Folded controls stay enabled; numerical,
  import/export and worker implementations were not changed.
- Portable build passed its embedded smoke and 186 native dependency checks;
  inspected the actual bundled panel screenshot. Native Windows Qt smoke also
  passed with isolated PATH (`artifacts/settings_0_4_1_windows/`).

## 0.4.0 Bayesian DRT

- Complete test suite: 127 passed (45.62 seconds) before portable packaging.
- Portable build and embedded Bayesian smoke passed. Native dependency audit:
  186 binaries, all from the project Python/venv or Windows. Build artifacts:
  `artifacts/portable_smoke_DRTAnalyzer_20261016_111041_274/`.
- Native Windows Qt smoke passed with Python environment variables removed and
  PATH restricted to Windows (`artifacts/bayesian_portable_windows/`). Bayesian
  smoke Rp = 84.051575 Ohm for a deliberately short 30/80 x 2-chain run;
  convergence warnings remain visible for these small testing budgets.
- EXE SHA-256:
  `9837f7a568aa112acc529711515b08ecb4161a904a8679eba89b773c440e6927`.
- Before implementation: all 110 existing tests passed. Three numerical
  Tikhonov snapshots were captured before changing the pipeline; regression
  checks compare complete gamma/reconstruction/residual/tau arrays and scalars.
- Added analytic half-normal, single/two RC, controlled-noise width, same/different
  seed, multiple-chain diagnostics, all six unchanged MAP lambda selectors,
  current-chain cancellation, GUI responsiveness, restart, band and history tests.
- Unmodified pyDRTtools HMC at commit 445ecce0b9ba01d741530183dd5cc49d5b8d5ea0
  compared on the same joint conditional posterior: mean relative L2 0.3643%,
  credible bounds 0.7788%, identical peak tau 0.00493727 s, Rp 16.12217 vs
  16.12510 Ohm, combined Rp MCSE 0.004535 Ohm. All pointwise mean differences
  were within 4 combined MCSE; R-hat max 1.00412, minimum bulk/tail ESS
  3447/3139. Known finite-RBF truth was within the pointwise band on this case.
- Stronger lambda .001 produced prior-induced undercoverage (72.7%) despite
  reference agreement. This limitation and the sensitivity investigation are
  disclosed in docs/BAYESIAN_DRT.md; no comparison tolerance was enlarged.
- Source full smoke passed (`artifacts/bayesian_source_smoke_polygon/`), including
  actual Bayesian solve, Qt-rendered credible band and existing XLSX export.
- Render investigation caught a native Qt 6.12 crash with FillBetweenItem.
  The band now uses a supported enclosed PlotDataItem; GUI tests render/grab the
  actual plot to guard against this failure, in addition to numerical tests.
- No importer/exporter, Tikhonov solver, RBF/epsilon, lambda selector or Lin-KK
  implementation files were changed; no new runtime dependency was introduced.

## 0.3.0 functional update

- 110 tests passed, including headerless TXT separators, UTF-8/UTF-16, both
  imaginary conventions, malformed rows, editable automatic controls and batch
  export of all six PNG types for two distinct analysis variants.
- All 35 supplied spectra imported, calculated and exported to XLSX/TXT;
  source SHA-256 values were unchanged (`artifacts/real_data_validation/`).
- Two additional real headerless 60-point DRTtools files from the import error
  log imported, calculated and exported successfully. These private source files
  remain outside the repository; derived checks are under ignored artifacts/.
- Source application smoke passed at `artifacts/source_smoke_0_3/`: Manual shape
  epsilon 6, synthetic two-RC Rp = 100.29587 Ohm, relative RMS = 0.54351%,
  two peaks, headerless import, manual edits and two-file XLSX/TXT/PNG export.
- Inspected the export dialog and real PNG output visually. PNG filenames
  identify each source and plot type; Nyquist and DRT are the default selection.
- Cross-basis numerical regression tests explicitly use Auto shape to match
  basis width to grid spacing, as before. The new Manual-6 Gaussian default is
  independently exercised by GUI/export tests and the executable smoke test.
- Bayesian investigation confirmed an unimplemented engine stub, not a missing
  dependency. No Bayesian results or uncertainty bands are represented as working.
- Full batch export passed for all 35 spectra: XLSX, TXT, and 70 default PNG
  plots (`artifacts/all_spectra_export_172519/`).
- Final portable EXE passed offscreen and native Windows Qt smoke checks with
  PATH restricted to Windows and Python environment variables removed. All 186
  native dependencies passed provenance checks. Final artifacts are under
  `artifacts/portable_final_0_3/`.

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
