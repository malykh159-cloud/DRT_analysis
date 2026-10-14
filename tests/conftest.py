import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from drt_analyzer.data.models import RawSpectrum, ImportInfo


def synthetic(f=None, branches=((80., 0.01),), rs=5., inductance=0., noise=0.):
    if f is None:
        f = np.geomspace(1e5, 1e-2, 81)
    z = np.full(len(f), rs, dtype=complex)+2j*np.pi*f*inductance
    for resistance, tau in branches:
        z += resistance/(1+2j*np.pi*f*tau)
    if noise:
        rng = np.random.default_rng(1234)
        z += noise*np.abs(z)*(rng.normal(size=len(f))+1j*rng.normal(size=len(f)))/np.sqrt(2)
    return RawSpectrum("synthetic.csv", "synthetic", f, z.real, z.imag,
                       ImportInfo("synthetic", ",", ("f", "Re", "Im"), (0, 1, 2), "Im(Z)", 1, "synthetic"))


@pytest.fixture
def rc():
    return synthetic()
