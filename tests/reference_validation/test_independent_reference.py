"""Independent high-accuracy quadrature and explicit dense inverse checks.

These validate our equations without importing or copying a reference package.
pyDRTtools integrates on (-infinity, infinity); our documented finite window must
be used on both sides for a meaningful comparison. See docs/MATHEMATICS.md.
"""
import numpy as np
import pytest
from scipy.integrate import quad
from drt_analyzer.drt.discretization import build_matrices
from drt_analyzer.drt.rbf import RBF_NAMES
from drt_analyzer.regularization.selection import smoother_statistics, gcv_score


def independent_phi(x, eps, name):
    r = abs(x)*eps
    if name == "Gaussian":
        return np.exp(-r*r)
    if name == "C2 Matern":
        return (1+r)*np.exp(-r)
    if name == "C4 Matern":
        return (3+3*r+r*r)/3*np.exp(-r)
    return (15+15*r+6*r*r+r**3)/15*np.exp(-r)


@pytest.mark.parametrize("rbf", RBF_NAMES)
def test_kernel_against_adaptive_quad(rbf):
    f = np.geomspace(1e4, .1, 12)
    d = build_matrices(tuple(f), rbf, "Auto", 1., 2)
    for row, col in ((0, 0), (5, len(d.centers)//2), (11, len(d.centers)-1)):
        def integrand(u):
            return independent_phi(u-d.centers[col], d.epsilon, rbf)/(1+2j*np.pi*f[row]*np.exp(u))
        re = quad(lambda u: integrand(u).real, d.ln_tau[0], d.ln_tau[-1], epsabs=1e-11)[0]
        im = quad(lambda u: integrand(u).imag, d.ln_tau[0], d.ln_tau[-1], epsabs=1e-11)[0]
        assert abs(d.kernel[row, col]-(re+1j*im)) < 2e-5


def test_smoother_against_dense_reference():
    rng = np.random.default_rng(7)
    a = rng.normal(size=(18, 7))
    y = rng.normal(size=18)
    r = np.diag(np.arange(1., 8.))
    lam = .017
    h = a@np.linalg.solve(a.T@a+lam*r.T@r, a.T)
    expected = (np.linalg.norm(y-h@y)**2, np.trace(h), np.trace(h.T@h))
    actual = smoother_statistics(a, y, r, lam)
    np.testing.assert_allclose(actual, expected, rtol=1e-10)
    sse, tr, tr2 = expected
    for method in ("GCV", "mGCV", "rGCV"):
        rho = 1.3 if method == "mGCV" else 1.
        score = (sse/18)/(1-rho*tr/18)**2
        if method == "rGCV":
            score *= .2+.8*tr2/18
        assert gcv_score(*actual, 18, method) == pytest.approx(score, rel=1e-10)


@pytest.mark.parametrize("order", [0, 1, 2])
def test_gaussian_penalty_against_independent_integral(order):
    f = np.geomspace(1e4, .1, 12)
    d = build_matrices(tuple(f), "Gaussian", "Manual", 1.7, order)
    k = len(d.centers)//2
    eps, center = d.epsilon, d.centers[k]
    def derivative_squared(u):
        x = u-center
        value = np.exp(-(eps*x)**2)
        if order == 1:
            value *= -2*eps**2*x
        elif order == 2:
            value *= 4*eps**4*x*x-2*eps**2
        return value*value
    expected = quad(derivative_squared, d.ln_tau[0], d.ln_tau[-1], epsabs=1e-11)[0]
    assert np.dot(d.penalty[:, k], d.penalty[:, k]) == pytest.approx(expected, rel=1e-7)
