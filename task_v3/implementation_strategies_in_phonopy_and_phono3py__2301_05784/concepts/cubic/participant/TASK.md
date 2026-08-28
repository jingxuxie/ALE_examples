# Cubic reciprocal interpolation

Deliver `solve.py` in the runner-designated attempt/output directory to interpolate third-order force constants at
momentum-conserving phonon triplets and compute their mode coupling strengths.
The target averages the three choices of lattice origin. Both the complex
Cartesian tensor and the mass-, eigenvector-, and frequency-dependent strengths
are scored separately.

Run `python solve.py INPUT.npz OUTPUT.npz`. The complete array schema and
mathematical conventions are in `workspace/CONTRACT.md`. `input/smoke.npz` is an
unlabeled interface example. Inputs include actual crystal geometry and force
constants; no fitting or thermal-transport calculation is required.

`workspace/` is a read-only starter; copy any needed files into your output
directory. The supplied NumPy program is an author-written, deliberately restricted
single-origin baseline, not an unmodified upstream checkout. Replace or extend
your copy. Do not import an external cubic-interpolation implementation or access
private files. NumPy and the Python standard library suffice. The per-case limit
is 180 seconds and 8192 MiB, with one BLAS/OpenMP thread.
