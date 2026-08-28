# Localization solver

Run with Python, NumPy, and SciPy:

```sh
python solve.py --input /path/to/input --output /path/to/predictions.json
```

`solve.py` follows the supplied schema and never uses the finite-device witness
to infer a bulk length. It solves the zero-energy complex-band polynomial
`T z² + H z + T†`, retains nonzero factors strictly inside the unit circle, and
returns the largest amplitude length `-cell_length_nm / log(abs(z))`.
For singular hopping, a rank-reduced generalized eigenproblem eliminates cell
interiors; an unreduced pencil handles singular or ill-conditioned interiors.
No inverse of the hopping matrix, boundary potential, or changed device length
is used. The physical cell length accounts for grouped representations.

For finite devices, it first diagonalizes the supplied six-dimensional energy
matrix, then minimizes projected position within only the closest-to-zero
two-state subspace. Squared amplitudes are summed over all orbitals at each x
and normalized. The reported finite-window amplitude length is exactly the
specified second-quarter log-density OLS statistic, including its factor of two.
Both extractions are invariant under orbital gauge transformations, and the
finite extraction is invariant under rotations of the supplied six-state basis.

The solver limits BLAS libraries to one thread and requires no external data,
Kwant, or full finite-system diagonalization.
