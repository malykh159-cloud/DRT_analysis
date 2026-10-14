# DRT Analyzer 0.1.0 — implementation plan

1. Immutable source models, explicit sign conventions, validated TXT/CSV/XLSX import;
   Qt workspace with spectrum table and experimental Nyquist/Bode views.
2. Independent Tikhonov core, quadrature of RBF kernels and derivative penalty,
   nonnegative solve, impedance reconstruction, Rp and synthetic verification.
3. Manual/GCV/mGCV/rGCV/L-curve/paired k-fold selection and cached lambda scan.
4. Complex Lin-KK diagnostic with mu model-order selection, HF inductance model,
   explicit residuals, preprocessing records and quality warnings.
5. Prominence-based peaks, valley partitioning and integration of Rp per peak.
6. Cancellable background batch, cached switching, DRT comparison with legends.
7. Snapshot history, Undo/Redo, CSV/XLSX/JSON and PNG/SVG export.
8. Independent numerical reference checks and portable PyInstaller build.

Dependencies: NumPy, SciPy, PySide6, pyqtgraph, openpyxl; pytest and PyInstaller
for development. No GUI dependencies in numerical modules.

Plotting: pyqtgraph (Qt interaction, hover, pan/zoom and PNG/SVG exporters).
Solver: column-scaled augmented least squares with scipy.optimize.nnls;
nonnegative RBF coefficients imply gamma >= 0. Rs and L are nonnegative too.
Penalty: integral of the squared order-0/1/2 derivative in ln(tau).
Tau: measured [1/(2*pi*fmax), 1/(2*pi*fmin)], 12 centers/decade, 36–144
centers; dense trapezoid quadrature, no artificial extension outside this window.
RBF: Gaussian, C2/C4/C6 Matern, definitions verified against pyDRTtools basics.py.
Auto shape: deterministic half-maximum width equal to one center spacing.
GCV family: unconstrained linear smoother scores; clearly disclosed as a surrogate
for the final constrained fit. mGCV uses rho, rGCV uses xi and tr(H.T H).
L-curve: positive signed curvature of log residual vs log penalty along log lambda,
using constrained fits. k-fold: fixed-seed five folds, Re/Im paired by frequency.
Lin-KK: weighted complex RC regression, unrestricted RC strengths, series L,
optional series capacitance, increasing M until mu <= 0.85.
HF induction: contiguous high-frequency positive Im(Z), relative noise threshold;
retain all data and add series j*w*L. Mixed low-frequency induction is flagged.

Critical checks: RBF derivatives, ln versus log10 integration, finite-window edge
bias, lambda scaling and smoother degrees of freedom, mu stopping, imaginary
sign ambiguity, peak partition integrals. Sources and formulas: MATHEMATICS.md.
Bayesian interface is reserved; no unverified uncertainty estimates in 0.1.0.
