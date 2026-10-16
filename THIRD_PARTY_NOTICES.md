# Third-party notices and scientific references

The Tikhonov, RBF and analysis infrastructure is independently implemented.
The Bayesian exact Gaussian reflecting sampler is adapted from pyDRTtools
HMC.py (Francesco Ciucci, Ting Hei Wan, Baptiste Py, Adeleke Maradesa), MIT,
copyright (c) 2023 ciuccislab, commit 445ecce0b9ba01d741530183dd5cc49d5b8d5ea0.
Modifications include local RNG states, cooperative cancellation, elementwise
feasibility checks, outward root selection, bounded work and equivalent
constraint-coordinate reflections. Unmodified HMC.py and nearest_PD.py are
included under tests/reference_pydrttools solely for reference validation.
Scientific formulation and implementation differences: docs/BAYESIAN_DRT.md.

Scientific references:

- pyDRTtools, Ciucci lab: https://github.com/ciuccislab/pyDRTtools (MIT).
- Wan et al. 2015: https://doi.org/10.1016/j.electacta.2015.09.097.
- Maradesa et al. 2023: https://doi.org/10.1149/1945-7111/acbca4.
- Schönleber et al. 2014: https://doi.org/10.1016/j.electacta.2014.01.034.
- Hansen and O'Leary 1993: https://doi.org/10.1137/0914086.

Runtime libraries retain their respective licenses and copyright notices:

| Component | License | Upstream |
|---|---|---|
| Python | PSF | https://www.python.org/psf/license/ |
| NumPy | BSD-3-Clause and bundled notices | https://numpy.org/doc/stable/license.html |
| SciPy | BSD-3-Clause and bundled notices | https://github.com/scipy/scipy/blob/main/LICENSE.txt |
| PySide6 / Qt | LGPL-3.0 / GPL-3.0 / commercial (component-dependent) | https://doc.qt.io/qtforpython-6/licenses.html |
| pyqtgraph | MIT | https://github.com/pyqtgraph/pyqtgraph/blob/master/LICENSE.txt |
| openpyxl | MIT | https://openpyxl.readthedocs.io/en/stable/licence.html |
| PyInstaller | GPL-2.0-or-later with bootloader exception | https://pyinstaller.org/en/stable/license.html |

Portable builds use dynamically linked Qt libraries; keep the full distribution
and its included license/metadata files. No Qt WebEngine/PDF components are
used by the application. System fonts are loaded from Windows, not redistributed.
Build tooling is not an additional scientific dependency.

## pyDRTtools MIT license (Bayesian sampler adaptation)

MIT License

Copyright (c) 2023 ciuccislab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
