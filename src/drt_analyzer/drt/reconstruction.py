import numpy as np


def reconstruct(frequency, tau, gamma, weights, rs=0., inductance=0.):
    kernel = 1 / (1 + 2j*np.pi*np.asarray(frequency)[:, None]*np.asarray(tau)[None, :])
    return rs + 2j*np.pi*np.asarray(frequency)*inductance + kernel @ (gamma*weights)
