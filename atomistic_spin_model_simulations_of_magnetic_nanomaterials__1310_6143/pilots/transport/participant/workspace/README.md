# Starting workspace

`baseline.py` is an executable, deliberately cell-averaged starting point. It combines sublattices before transport and allocates currents using atom fractions. It does not implement resolved-channel physics.

`pre_sublattice_resistance.cpp` is the official single-channel source at commit `c3e38ec6134e8bb9342f1b2c4cd8406a7820ad49`, immediately before the `f415696ef7dfac24d57bd8c1e8cdca8d2c35c583` sublattice scaffolding commit. It is context, not a standalone compilation unit. The associated BSD licence is included.

Copy or adapt the baseline as `solve.py` within your submission directory. It uses only the Python standard library, not NumPy, Numba, SciPy, or user-site packages. The output interface is JSON.
