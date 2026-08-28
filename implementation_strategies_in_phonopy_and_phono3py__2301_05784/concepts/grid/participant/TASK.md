# Generalized Brillouin-zone integration

Implement accurate Brillouin-zone geometry and linear-tetrahedron spectral
integration on integer-generated reciprocal grids. The supplied starting solver
uses diagonal-grid rounding and a histogram; extend its capabilities without
changing the interface.

Run `python solve.py INPUT.npz OUTPUT.npz`. The complete mathematical and array
contract is in `workspace/CONTRACT.md`; `input/example.npz` is an unlabeled smoke
input. Deliver `solve.py` into the runner-designated attempt/output directory;
the participant workspace is a read-only starter. Only NumPy, SciPy, and the
Python standard library are available. Private
grid, lattice-reduction, and phonon-integration packages are not available.

Geometry and spectra are scored independently against high-accuracy references,
relative to measured starting-solver errors. Evaluation includes skew and
non-diagonal grids, boundary multiplicities, narrow/degenerate branches, and
grids exceeding 100,000 points. Mean and worst-family accuracy determine quality;
actual elapsed time and peak memory are also reported. Do not specialize to the
smoke input.
