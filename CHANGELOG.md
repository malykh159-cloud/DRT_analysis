# Changelog

## 0.4.2 — 2026-10-16

- Forward live Bayesian chain/warm-up/sampling progress through Lambda Scan,
  including the current lambda and diagnostics stage before the first fit ends.
- Display fractional sampling percentages without resetting at lambda boundaries.
- Regression tests for first-lambda GUI activity, immediate Stop and retention
  of the previous result; frozen smoke exercises Bayesian scan progress too.
- Bayesian target, sampler settings, scan bounds and Tikhonov behavior unchanged.

## 0.4.1 — 2026-10-16

- Collapsible Frequency Range, Validation and Peaks; display-only folding
  preserves all settings and their effect on analysis.
- Regularization Advanced contains derivative order and lambda scan bounds/count.
- Detailed Russian help dialogs for all nine basic/advanced Bayesian parameters.

## 0.4.0 — 2026-10-16

- Conditional Bayesian DRT with positive joint Rs/L/RBF posterior, adapted
  exact reflecting Gaussian HMC, independent RNG chains, and credible intervals.
- Bayesian-only settings block, advanced controls, diagnostics, and existing
  history/plots/batch integration. Cooperative Stop beside the progress bar.
- Rank/folded split R-hat, bulk/tail ESS and numerical-transition warnings.
- Pinned pyDRTtools reference comparison and preimplementation Tikhonov snapshots.
- Import/export implementations, RBF/epsilon, Tikhonov selectors/defaults and
  existing layout remain unchanged apart from the requested Bayesian controls.

## 0.3.0 — 2026-10-15

- Import headerless three-column DRTtools TXT and BOM-marked UTF-16/UTF-32.
- Batch export all/selected calculated spectra to XLSX and tab-separated TXT.
- Select PNG plot types for all exported files; default Nyquist and DRT.
- Compact Summary: File, Rs, Rp total, lambda and peak Rp values.
- Manual fields remain editable; edits select their manual parameter mode.
- Default Manual shape, epsilon 6, including Auto analysis.
- Explain the unimplemented Bayesian engine and add Compare usage help.

## 0.2.0 — 2026-10-15

- Inclusive per-spectrum manual frequency range, shared by DRT/Lin-KK/Auto/Scan
  and exported in settings, summary tables and preprocessing indices.
- Run analysis replaces Calculate; original points outside the fit are gray.
- Automatic Im convention from the nonzero-sign majority of each full source.
- Remove selected spectra/history variants with Del or dedicated buttons;
  source files remain intact, history/plots/comparisons stay synchronized.
- Modeless Russian help beside every editable setting, with practical advice.
- Frequency cursor readouts on Nyquist, DRT, comparison, Bode and residuals;
  cursor overlays are excluded from PNG/SVG exports.
- Fix Windows QtCore startup failure caused by Poppler ICU DLLs collected from
  the host PATH; isolate dependency search and verify native library origins.
- Record Qt initialization failures, separate smoke artifacts per build and
  reliably retain child-process exit codes under Windows PowerShell.

## 0.1.0 — 2026-10-15

- Modular Windows desktop workspace with validated TXT/CSV/TSV/XLSX import.
- Nonnegative Tikhonov DRT, Gaussian/Matérn bases and derivative orders 0/1/2.
- Six lambda modes, cached Lambda Scan, Lin-KK and explicit induction model.
- Peak partition/integration, reconstruction/residuals, batch and cancellation.
- Snapshot history, Undo/Redo, DRT comparison, tables/settings/figure exports.
- Mathematical verification, real-data integration and portable build workflow.
- Bayesian engine reserved, unavailable in this release.
