# Third-party notices and scientific references

DRT Analyzer's application and numerical code were independently implemented.
No pyDRTtools or impedance.py source code is embedded or adapted. RBF definitions
and algorithm formulas were checked against publications and the authors'
public source, with numerical implementation differences disclosed in
docs/MATHEMATICS.md.

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
