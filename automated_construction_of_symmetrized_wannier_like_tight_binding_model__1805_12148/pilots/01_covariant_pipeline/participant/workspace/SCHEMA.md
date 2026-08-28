# I/O contract (version 1)

Dependencies: Python 3.10+, NumPy and SciPy. The baseline has no modern TBmodels,
symmetry-representation, HDF5, or vendor dependency. All arrays are float64 or
complex128 unless integer indices are specified. All energies use the input
energy unit. All Cartesian lengths are angstroms.

## Case directory

`case.json` contains `format_version: 1`, `import`, and `mapping` objects.
Paths are relative to the case directory. Input files are immutable.

`import` fields:
- `hr`, `win`, `xyz`: Wannier90 filenames; `wsvec`: filename or null.
- `pos_kind`: `wannier` or `nearest_atom`. XYZ `X` rows are Cartesian Wannier
  centres in orbital order. Other rows are explicit Cartesian atom positions.
  For nearest-atom assignment use the Euclidean Cartesian distance to these
  explicit rows, no periodic-image search. Ties select the first row.
- `supercell`: three positive integers. Include every source orbital and every
  hopping. Supercell images are ordered lexicographically by
  `itertools.product(range(sx), range(sy), range(sz))`, source orbital fastest.
- `permutation`: new-to-old indices applied AFTER forming the supercell.
- `kpoints`: a Q-by-3 array of reduced reciprocal coordinates of that supercell.

The hr degeneracy table divides each corresponding R block. Each wsvec record
is keyed by `(R, orbital_1, orbital_2)` using 1-based orbital indices. Its list
of N integer vectors replaces the corresponding hopping by N contributions
at `R + T`, each with weight `1/N`. hr matrix element `(i,j)` is
`<i,0|H|j,R>`. Correct the complete import before constructing its supercell.
Canonicalizing centres into `[0,1)` also changes the hopping gauge; it is not
an independent position-only modulo operation. No hopping cutoff is requested.

`mapping` fields:
- `model`: input NPZ containing `uc` (3,3 row vectors), `pos` (N,3), `R` (L,3
  integer), `hop` (L,N,N complex). This is an independent, already-correct model.
- The input uses **half storage**: `F(k) = sum_R hop[R] exp(2 pi i k.R)` and
  `H2(k) = F(k) + F(k)^dagger`. R=0 is also half stored. Do not double it again.
- `uc`: target 3-by-3 cell; `offset`: target origin relative to the old origin.
- `cartesian`: if false, both target cell rows and offset are expressed in the
  old reduced coordinates. If true, both are Cartesian. The integer change
  matrix has determinant +1 and is compatible with the old lattice within
  floating-point tolerance.
- `permutation`: new-to-old indices applied AFTER cell/origin transport.
- `kpoints`: Q-by-3 reduced reciprocal coordinates in the target cell.

Preserve all orbitals. Returned reduced positions are canonical `[0,1)`;
boundary values may differ by floating roundoff, but their hopping gauge must
be consistent. For either track, convention 1 is
`H1_ij(k) = H2_ij(k) exp(2 pi i k.(pos_j-pos_i))`.
Bands are sorted ascending along the last axis, without an energy shift.

## Output NPZ

Write exactly these numeric arrays (no pickles/objects):

| Key | Shape | Meaning |
| --- | --- | --- |
| `import_pos` | (Ni,3) | supercell positions after permutation |
| `import_h1`, `import_h2` | (Qi,Ni,Ni) | imported supercell matrices |
| `import_bands` | (Qi,Ni) | eigenvalues of imported matrices |
| `map_pos` | (Nm,3) | mapped positions after permutation |
| `map_uc` | (3,3) | target Cartesian row-vector cell |
| `map_h1`, `map_h2` | (Qm,Nm,Nm) | transported model matrices |
| `map_bands` | (Qm,Nm) | eigenvalues of transported matrices |

Inputs may have different Ni/Nm or Qi/Qm. Evaluated outputs have at least 16
orbitals; primitive import files may be smaller before the physical supercell.
The independent mapping model is never a substitute for the import data.

## Evaluation

Families are `cartesian_wsvec`, `nearest_atom`, and `cell_gauge`. Shape errors,
non-finite arrays, missing outputs, or a failed process receive zero for the
affected family. Valid numerical errors receive continuous credit relative to
a stored unrepaired baseline. The score is `1/(1+9*error/weak_error)`, so the
weak baseline scores 0.1 and the reference 1. Family errors combine positions,
full matrix errors, and bands; matrix entries dominate. No spectral matching,
unitary alignment, energy shifting, or clipping to a binary tolerance occurs.
Core score is the geometric mean of family scores; worst-family score is the
minimum. Each case has a 90-second limit; small dense models do not require a
GPU. Only the participant tree and writable attempt should be visible at run
time. Standard numerical libraries are allowed; private reference code is not.
