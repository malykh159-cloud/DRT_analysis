# Bayesian DRT in the existing RBF pipeline

This implements conditional Bayesian DRT, not hierarchical Bayes or Gaussian
process DRT. `gamma` in AnalysisVariant is the posterior mean. Its existing
`uncertainty` slot stores immutable coefficient draws (chain, draw, normalized
coefficient), pointwise credible bounds, noise estimate and diagnostics.
The nested BayesianSettings in the existing settings snapshot records all
controls; history/Undo/Redo use the same AnalysisVariant and History classes.

## Model and lambda

Reuse the unchanged frequency preprocessing, Lin-KK, finite tau window, RBF
basis, epsilon convention and normalized design matrix from Tikhonov. In those
modulus-weighted coordinates:

`y | x, sigma ~ Normal(A x, sigma² I)`

`p(x | lambda, sigma) ∝ exp[-lambda ||R x||² / (2 sigma²)] 1{x >= 0}`

Thus the joint posterior of Rs, detected series L, and RBF coefficients is a
Gaussian restricted to the positive orthant, with untruncated parameters
`Q = (AᵀA + lambda RᵀR)/sigma²` and `mu = Q⁻¹ Aᵀy/sigma²`.
Rs/L retain the existing flat nonnegative priors and zero derivative penalty.
For derivative orders 1/2 the smoothing prior can be intrinsic/improper;
the posterior must be proper. Cholesky failure raises an explicit error.
No nearest-PD repair, silent ridge/jitter, or sample clipping is performed.

All six current lambda choices remain applicable as **plug-in MAP/predictive
regularization selection**, not posterior evidence maximization. Manual fixes
lambda. GCV/mGCV/rGCV retain their documented unconstrained smoother surrogate;
L-curve and k-fold retain their existing constrained MAP criteria. These do not
integrate over lambda or become fully Bayesian selectors merely by choosing
Bayesian DRT. Their selected lambda and arrays are retained unchanged.

Auto sigma is the population standard deviation of MAP residuals in weighted
normalized coordinates, with an explicit user-visible floor (default 1e-6).
This mirrors the residual plug-in approach in pyDRTtools, extended to the current
modulus weighting. Residuals contain model error as well as measurement noise.
Advanced permits a known fixed sigma; 0 selects Auto. This is a conditional
noise model, not an inferred noise posterior. Real/imag weighted errors are
assumed independent, Gaussian, with the same variance.

## Sampling and defaults

Exact harmonic Hamiltonian dynamics with specular reflection at each x_i = 0,
following Pakman–Paninski and pyDRTtools HMC.py. Gaussian whitening is implicit:
constraint-coordinate reflections use covariance columns, algebraically equal
to whitened reflections, avoiding repeated dense matvecs. No leapfrog step,
Metropolis tuning, adaptation, or integrator divergence statistic is needed.
Actual acceptance and numerical failures are recorded per chain. A transition
exceeding the reflection limit or failing feasibility is rejected by retaining
the previous state, never by clipping it; any such event produces a warning.

Defaults: 1000 discarded warm-up transitions, 2000 retained draws **per chain**,
4 independent chains, SeedSequence seed 42, central 95% interval. These are
starting budgets, not a convergence guarantee. The reference discards 501
draws and uses a pi/2 trajectory; this application exposes warm-up and records
independent chains. Exact HMC needs no step adaptation; warm-up only removes
initialization effects. Each chain starts at an independent positive perturbation
of MAP; SeedSequence.spawn supplies independent local Generator states.

Advanced is initially collapsed: noise sigma/floor, trajectory time (pi/2),
maximum reflections per transition (10000). Small lambda and tightly constrained
nearly noiseless data can require many reflections and be much slower than
Tikhonov. Increasing lambda changes the scientific target; it is not a substitute
for verifying convergence. Cooperative Stop is checked at every trajectory and
reflection, and between diagnostic grid chunks. No thread termination is used.

## Mean, uncertainty and diagnostics

Compute sampled `gamma = B x_DRT * impedance_scale` before taking the two
pointwise equal-tail quantiles. Mapping coefficient quantiles through B is
generally incorrect for correlated coefficients. Mean gamma, reconstruction,
residuals, peaks, finite-window Rp and peak Rp use the existing linear mapping
and unchanged analysis routines. Ideal RC DRTs are delta distributions; finite
peak heights have no literal pointwise delta coverage interpretation.

Diagnostics inspect all joint coefficients and all DRT grid points before
pooling chains. Rank-normalized split/folded R-hat takes the larger value;
bulk ESS uses ranked split draws and Geyer initial-positive, monotone paired
autocorrelations; tail ESS is the minimum at pooled 5% and 95% quantiles.
Warn for R-hat > 1.01, bulk/tail ESS < 400, or numerical failures. One chain has
no between-chain R-hat and always warns. Results remain viewable as Review.
The band is pointwise, conditional on lambda/basis/noise/window, not simultaneous
coverage, model uncertainty, or a guarantee of physical peak interpretation.

## Reference validation and implementation differences

Run `python scripts/validate_bayesian_reference.py`. The pinned unmodified
pyDRTtools HMC.py and nearest_PD.py (MIT) are in tests/reference_pydrttools,
commit `445ecce0b9ba01d741530183dd5cc49d5b8d5ea0`.
Compare the same finite-grid synthetic spectrum, A, R, Gaussian epsilon 6,
derivative order 2, lambda .0001, fixed weighted sigma .02 and joint posterior.
The reference precision/covariance is constructed independently using NumPy.
Compare mean curves, peak locations, integrated Rp, and pointwise bounds under
independent RNGs, using reported MCSE as well as predeclared relative thresholds.
Also check finite-RBF ground truth coverage. This is not a claim of equality
to the full pyDRTtools UI defaults or discretization: those grids, weighting,
nuisance-variable treatment and published coefficient-quantile plotting differ.
We sample joint Rs/L uncertainty, and take quantiles after mapping sampled DRTs.

Sensitivity investigation: using lambda .001 on this known finite-RBF truth
gave only 72.7% pointwise truth coverage despite excellent convergence and
agreement with the reference sampler. The stronger prior oversmoothed the peak;
this was not an HMC discrepancy. Lambda .0001 is used for the truth-coverage
check after inspecting this sensitivity. Error tolerances were not enlarged.
This example is why fixed-lambda credible bands must not be described as
automatically covering the physical truth; inspect regularization sensitivity.

Analytic half-normal sampler tests, controlled-noise widening, one/two RC peaks,
seed reproducibility, multiple-chain diagnostics, live worker cancellation and
preimplementation Tikhonov numerical snapshots provide additional checks.
Existing import/export code, formats, naming and table column order are unchanged.
Generic table export uses the current posterior mean; existing PNG rendering
includes the band. Dedicated interval table export is deliberately deferred.

## Sources

- Ciucci & Chen (2015), *Analysis of electrochemical impedance spectroscopy
  data using the distribution of relaxation times: A Bayesian and hierarchical
  Bayesian approach*, Electrochimica Acta 167, 439–454.
  https://doi.org/10.1016/j.electacta.2015.03.123
- Effat & Ciucci (2017), *Bayesian and Hierarchical Bayesian Based Regularization
  for Deconvolving the Distribution of Relaxation Times from Electrochemical
  Impedance Spectroscopy Data*, Electrochimica Acta 247, 1117–1129.
  https://doi.org/10.1016/j.electacta.2017.07.050
- Pakman & Paninski, *Exact Hamiltonian Monte Carlo for Truncated Multivariate
  Gaussians*, JCGS 23 (2014), 518–542. https://arxiv.org/abs/1208.4118
- Vehtari et al. (2021), *Rank-normalization, folding, and localization: An
  improved R-hat for assessing convergence of MCMC*. https://arxiv.org/abs/1903.08008
- Author reference implementation and MIT license:
  https://github.com/ciuccislab/pyDRTtools
