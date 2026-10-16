"""Rank-normalized split/folded R-hat and Geyer initial-monotone ESS.

Vehtari et al. (2021), doi:10.1214/20-BA1221. Arrays: chain, draw, variable.
"""
import numpy as np
from scipy.special import ndtri
from scipy.stats import rankdata


def _rank(x):
    flat = x.reshape(-1, x.shape[-1])
    return ndtri((rankdata(flat, axis=0)-.375)/(len(flat)+.25)).reshape(x.shape)


def _variance(x):
    n = x.shape[1]
    within = np.mean(np.var(x, axis=1, ddof=1), axis=0)
    between = n*np.var(np.mean(x, axis=1), axis=0, ddof=1)
    return within, within*(n-1)/n+between/n


def _rhat(x):
    within, variance = _variance(x)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.sqrt(variance/within)


def _ess(x):
    m, n, d = x.shape
    within, variance = _variance(x)
    centered = x-x.mean(axis=1, keepdims=True)
    size = 1 << (2*n-1).bit_length()
    fft = np.fft.rfft(centered, n=size, axis=1)
    acov = np.fft.irfft(fft*np.conjugate(fft), n=size, axis=1)[:, :n].real/n
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = 1-(within[None, :]-acov.mean(axis=0))/variance[None, :]
    rho[0] = 1
    count = (n//2)*2
    paired = rho[:count:2]+rho[1:count:2]
    positive = np.logical_and.accumulate(paired > 0, axis=0)
    monotone = np.minimum.accumulate(np.where(positive, paired, 0), axis=0)
    tau = np.maximum(1., -1+2*monotone.sum(axis=0))
    return np.minimum(m*n, m*n/tau)


def diagnose(draws):
    m, n, _ = draws.shape
    half = n//2
    split = np.concatenate((draws[:, :half], draws[:, -half:]), axis=0)
    ranked = _rank(split)
    folded = _rank(np.abs(split-np.median(split, axis=(0, 1))))
    rhat = np.maximum(_rhat(ranked), _rhat(folded)) if m > 1 else None
    bulk = _ess(ranked)
    bounds = np.quantile(split, [.05, .95], axis=(0, 1))
    tail = np.minimum(_ess((split <= bounds[0]).astype(float)),
                      _ess((split <= bounds[1]).astype(float)))
    return rhat, bulk, tail
