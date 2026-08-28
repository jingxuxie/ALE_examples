# Covariant tight-binding solver

Run from any working directory:

```sh
python /path/to/attempt/solve.py --input /path/to/case --output /path/to/result.npz
```

Only the local Python modules, NumPy, and SciPy are required. The entrypoint
does not import code from the read-only participant directory. The output
contains exactly the nine numeric arrays specified in `SCHEMA.md`.

## Repairs

- Convert Cartesian XYZ centres to reduced coordinates using the row-vector
  unit cell before constructing the model. The constructor then canonicalizes
  the centres and shifts their hopping gauge together.
- Choose nearest atoms using a separate Cartesian Euclidean distance for each
  explicit atom, without periodic images. `argmin` retains the first atom in a
  tie. This assignment precedes conversion and canonicalization.
- Round transformed hopping vectors to their verified integer values before
  casting to integers, rather than truncating floating-point solutions. Use a
  tolerance for the determinant check on the integer cell-change matrix.
- Import orbital indices explicitly, allowing arbitrary ordering within an HR
  block. Preserve the historical degeneracy normalization, independently keyed
  Wigner–Seitz averaging, full-model import, and physical supercell construction.
- Keep the independent mapping input half stored, including its zero-vector
  block, and apply each requested orbital permutation only after transport.

No nonzero hopping cutoff, band alignment, energy shift, or gauge fitting is
used. Original source provenance and license remain in `HISTORY.md` and
`TBMODELS_LICENSE.txt`.

## Gauge identities

For raw reduced centres `p`, let `d = floor(p)` and `p_new = p - d`.
A hopping from orbital `i` in cell zero to orbital `j` in cell `R` becomes

```text
R_new = R + d[j] - d[i].
```

For a cell change `A_new = C @ A_old` and an origin `a` in old reduced
coordinates, the raw new centres and lattice translations are

```text
q = (p - a) @ inverse(C)
R_rotated = R @ inverse(C).
```

Canonicalizing `q` applies the same hopping-shift rule. Equivalently, at
`k_old = k_new @ inverse(C).T`, the old convention-2 Hamiltonian is conjugated
by the diagonal phases `exp(2 pi i k_new . floor(q))`. Convention 1 is
invariant at the corresponding physical wavevector because the common
origin phase cancels. The test suite checks these identities against direct
Fourier sums of the input, not merely against output bands.

## Validation

```sh
cd /path/to/attempt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m unittest -v test_covariance
python solve.py --input ../participant/input/smoke --output smoke_result.npz
python smoke_check.py --input ../participant/input/smoke --output smoke_result.npz
```

The seven regression tests include independent directed-bond supercell sums,
nontrivial HR degeneracies, shuffled HR and Wigner–Seitz records, Cartesian
and Bohr cell input, both centre assignments, explicit-distance ties, tiny
nonzero hoppings, both Bloch conventions, supercell band folding, post-transport
permutations, distinct track sampling grids, half-stored zero blocks, cell-change
composition, 24 unimodular transformations in both coordinate modes, and
positions on opposite sides of a cell boundary.

## Scope and limitations

This solves the supplied finite tight-binding models; it does not reconstruct
omitted first-principles hoppings or perform disentanglement, refitting, or
additional symmetry averaging. Wannier files are expected to be complete
standard-format files with mutually Hermitian hopping pairs. The historical
Hermiticity consistency check is retained, so inconsistent imports fail rather
than silently being fitted to a different model. Dense storage is appropriate
for the stated small-model task, not arbitrarily large supercells. Validation
uses the supplied material smoke input and independently constructed cases;
no labeled reference output or unseen evaluation cases were available.
