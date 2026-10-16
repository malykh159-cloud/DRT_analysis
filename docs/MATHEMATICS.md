# Mathematical definitions and verification

## Integral equation and conventions

`Z(ω) = Rs + jωL + ∫[a,b] γ(exp(u))/(1+jω exp(u)) du`, where `u = ln τ`.
Measured `Im(Z)` is negative for a capacitive RC relaxation. Under the user's
explicit predominantly-capacitive assumption, more positive than negative
nonzero samples in the original imaginary column implies a −Im export; more
negative implies Im. Zeros do not vote. A tie uses the header convention.
The rule is applied per source before frequency filtering and supersedes the
header when a majority exists. Counts/header/evidence are exported. This is a
domain assumption, not a general inference for predominantly inductive data.
The sign multiplier affects only the analysis representation; the original
column and source row order remain immutable. Nyquist displays `(Re Z, −Im Z)`.

Manual bounds select an inclusive subset of experimental frequencies. At least
8 points must remain; invalid, nonpositive or inverted bounds fail explicitly.
Bounds outside the experimental coverage add no new points. Lin-KK, induction,
weights, automatic τ grid, lambda selection, reconstruction and peaks all use
the same selected subset. Snapshots retain requested bounds, actual min/max,
used original row indices and excluded indices. All source samples remain
available; full source arrays are exported separately from selected fits.

The finite window is `a = ln(1/(2π fmax))`, `b = ln(1/(2π fmin))` using the
actual selected fmin/fmax (the full source if no bounds are enabled). No extra
decades are added. Consequently the reported Rp is a measured-window estimate;
not every real spectrum has enough bandwidth to determine full polarization.
There are 12 centers per decade, clipped to 36–144 centers. Dense trapezoidal
quadrature uses at least 721 points, at least 12 points per center spacing and
step <= 0.1/ε; requests over 30001 samples fail explicitly.

## Positive RBF expansion

`γ(exp(u)) = Σ c_k φ(ε(u−u_k))`. Positive functions and `c_k >= 0` guarantee
nonnegative γ throughout the finite window, not merely at evaluation nodes.
Writing `r = ε |u−u_k|`:

| Basis | φ |
|---|---|
| Gaussian | exp(−r²) |
| C2 Matérn | (1+r) exp(−r) |
| C4 Matérn | (1+r+r²/3) exp(−r) |
| C6 Matérn | (1+r+2r²/5+r³/15) exp(−r) |

These are the definitions used in [pyDRTtools basics.py](https://github.com/ciuccislab/pyDRTtools/blob/master/pyDRTtools/basics.py).
No source code from that package was copied. The implementation differentiates
these formulas analytically. For Matérn `P(r) exp(−r)`, one derivative replaces
P by `P'−P`; the second gives `P''−2P'+P`, with the appropriate ε and sign factors.
Auto shape solves `φ(r_half)=1/2` and sets `ε=2 r_half/Δu`; hence FWHM=Δu.
This is a deterministic resolution convention, not optimization of a mechanism.

RBF discretization reference: Wan, Saccoccio, Chen and Ciucci (2015),
*Influence of the discretization methods on the distribution of relaxation times
deconvolution: implementing radial basis functions with DRTtools*,
[Electrochimica Acta 184, 483–499](https://doi.org/10.1016/j.electacta.2015.09.097).

## Tikhonov and numerical scaling

The complex matrix contains the integrated basis kernels, a constant Rs column
and, if detected, an inductance column. Let `s = median |Z|`, `ωmax=max ω`.
Unknowns are `Rs/s`, `ωmax L/s`, and `c_k/s`. The inductance matrix column is
`jω/ωmax`. Real and imaginary rows are stacked, each divided by `|Z|/s`.
The weight denominator is floored at `1e-12` in these dimensionless units;
the experimental numbers themselves are never modified.

The exact solved objective is `||Ax−y||² + λ ||Rx||²` with `x >= 0`.
There is no extra square of λ, no implicit normal-equation jitter and no
division by sample count. `R = diag(sqrt(w_q)) B^(d)` padded with zero columns
for Rs and L, where `d=0,1,2` and `w_q` are trapezoid weights in natural log τ.
Thus the penalty approximates the integral of squared γ magnitude, slope or
curvature in ln τ in normalized impedance units. λ values depend on basis,
order, weighting, number of data and these normalization conventions.

We stack `A` and `sqrt(λ)R`, scale columns to unit norm and use SciPy NNLS.
Unconstrained reference/smoother solves use augmented SVD least squares with
relative singular cutoff `1e-12`. Singular matrices and convergence failures
are surfaced; no fabricated optimum is returned.

## Lambda selection

`H = A (AᵀA+λRᵀR)⁻¹ Aᵀ` denotes the unconstrained smoother. Implementation
computes its action via augmented SVD rather than explicitly inverting normal
equations. Let `n=2 Nfrequency`, `e=y−Hy`, `ν=tr H`, `μ₂=tr(HᵀH)/n`.

- GCV: `(||e||²/n)/(1−ν/n)²`.
- mGCV: replace denominator by `(1−ρν/n)²`; `ρ=1.3` for n<50, else 2.
  Values on the nonpositive-denominator branch are rejected to avoid spurious
  minima beyond the pole.
- rGCV: multiply GCV by `ξ+(1−ξ)μ₂`; ξ=0.2 for n<100, else 0.3.

Formulas and these parameter conventions are checked against the authors'
[parameter_selection.py](https://github.com/ciuccislab/pyDRTtools/blob/master/pyDRTtools/parameter_selection.py)
and the article by Maradesa et al., *Selecting the Regularization Parameter in
the Distribution of Relaxation Times*,
[Journal of The Electrochemical Society 170 (2023) 030502](https://doi.org/10.1149/1945-7111/acbca4).
The GCV family is an **unconstrained surrogate** for this application's final
positive estimator. It must not be presented as exact constrained GCV.

L-curve uses constrained solutions: x=`ln ||Ax−y||`, y=`ln ||Rx||`, parameter
t=`ln λ`. Signed curvature `(x'y''−y'x'')/(x'²+y'²)^(3/2)` is estimated on the
logarithmic grid. The maximum positive curvature is selected; two samples at
each edge are ineligible. No positive corner or failed fits produce an explicit
failure. This is a finite-grid curvature approximation, not an analytic optimum.
See Hansen and O'Leary, *The use of the L-curve in the regularization of discrete
ill-posed problems*, [SIAM J. Sci. Comput. 14 (1993) 1487–1503](https://doi.org/10.1137/0914086).

Five-fold CV uses nonnegative fits, NumPy default_rng(seed=34054) permutation,
and holds out both Re and Im rows of each test frequency. Score is the total
held-out weighted squared error divided by the number of held-out scalar rows.
The full-data modulus weights are fixed across folds, and the τ window/basis
remain fixed; this is a conditional sensitivity criterion for a given grid.
All automatic methods search a finite log grid (default 41 points, 10⁻⁸–10²).
Boundary selection is explicitly warned. No silent fallback criterion is used.

## Lin-KK

The diagnostic fits `Rs + Σ Rk/(1+jωτk) + jωL`, optionally `−j Q/ω`.
τk are log-spaced in the measured τ window. RC strengths, Rs, L and Q are
unrestricted for this diagnostic. Complex modulus-weighted least squares is
solved by SVD. `μ = 1−Σ|negative Rk|/Σ positive Rk`. Increase M until μ<=0.85.

Application-specific resolution guard: start M at
`min(max_M, max(3, ceil(3 log10(fmax/fmin))))` rather than 3. Three RC/decade is
an exposed heuristic, needed because coarse dictionaries can cross the μ cutoff
while severely underfitting sharp RC peaks. It is **not** attributed to the
original paper. Max M is limited to min(user maximum, Nfrequency−3).
The guard, threshold, maximum M and optional capacitance are exported.

Relative reconstruction RMS above the user threshold (default 2%) gives Review;
unreached μ or rank deficiency gives Inconclusive; otherwise Compatible.
These labels are diagnostics, not a statistical proof. Finite bandwidth,
noise, narrow processes, representation choices and the guard influence them.
Failure does not prevent DRT and never automatically excludes points.
See Schönleber, Klotz and Ivers-Tiffée,
[*A Method for Improving the Robustness of linear Kramers-Kronig Validity Tests*,
Electrochimica Acta 131 (2014) 20–27](https://doi.org/10.1016/j.electacta.2014.01.034),
and [impedance.py's documented implementation](https://impedancepy.readthedocs.io/en/latest/validation.html).

## Inductance, residuals and peaks

HF detection is a disclosed screening heuristic: descending-frequency contiguous
prefix where Im/|Z|>0.002. The capacitive solver adds a positive series L and
retains all samples. Isolated, weak, mixed or completely inductive behavior
generates warnings. This cannot represent every inductive loop.

`r_i = (Zobserved_i−Zfit_i)/|Zobserved_i|`.
Relative RMS = `sqrt(mean |r|²)`. Re/Im RMS in ohms use the corresponding
**absolute** residual components. Relative component RMS are exported too.
Plots show 100*r. No unweighted SSE is mislabeled chi-square.

`Rp,total = ∫ γ(τ) d ln τ`; it is not an integral in log10 without ln(10).
`f_peak=1/(2πτ_peak)`. SciPy find_peaks uses relative prominence and minimum
distance in decades, without manual process assignment. Regions partition at
the minimum γ between adjacent maxima, sharing the boundary node so trapezoid
intervals are neither lost nor duplicated. Thus sum Rp,i=Rp,total whenever peaks
exist. Regions are descriptive partitions, not unique physical deconvolution.
Endpoint maxima are explicitly marked unresolved; if no peak is resolved,
Rp,total still exists. Significant edge mass warns of finite-window bias.

## Verification and unsupported methods

Tests cover known one/two RC τ and Rp, noise, induction, sign conventions,
all bases/orders, reconstruction, lambda criteria, cancellation, GUI/history,
exports, direct dense smoother formulas and independent scipy.quad kernel
integration on **the same finite window**. The latter is not a full pyDRTtools
comparison: its unbounded basis integration has different edge behavior.
Conditional Bayesian DRT uses the same matrices and a Gaussian smoothing prior,
with exact reflecting HMC and pointwise posterior quantiles. Formulation,
diagnostics, reference comparison and limitations: [BAYESIAN_DRT.md](BAYESIAN_DRT.md).

Cursor readouts are display helpers. On Nyquist, nearest experimental frequency
is chosen by Euclidean screen distance, accounting for both view scales. No
unique frequency is inferred from an arbitrary Re/Im location. On τ plots the
continuous coordinate is converted by `f=1/(2πτ)`, and displayed curve values
are linearly interpolated in the logarithmic x coordinate. Hidden comparison
curves are ignored. Cursor annotations are excluded from scientific exports.
