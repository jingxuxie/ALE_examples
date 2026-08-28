# Repaired covariant tight-binding pipeline

Run from the pilot directory:

```sh
python attempt/solve.py --input participant/input/smoke --output attempt/result.npz
```

`solve.py` is executable and imports only the modules in this directory and
NumPy/SciPy. It does not load the unrepaired participant implementation or use
the independent mapping model as a substitute for the Wannier90 import.
The NPZ contains exactly the nine numeric arrays specified in `SCHEMA.md`.

## Scientific implementation

- The shared Cartesian loader reads the row-vector unit cell first and solves
  `position_cartesian = position_reduced @ cell`. XYZ coordinates stay in
  angstroms even when the WIN cell uses bohr.
- Nearest-atom assignment minimizes the Euclidean Cartesian distance over the
  explicit atom rows. It uses neither periodic images nor reduced-coordinate
  distances; `argmin` preserves the first row in an exact tie.
- Every HR block is divided by its degeneracy. WS corrections are matched by
  the explicit orbital and lattice indices, irrespective of record order.
  All vectors in a record contribute at `R + T` with weight `1 / N`.
  No nonzero hopping is discarded by a cutoff.
- If an orbital position has integer part `shift`, canonicalization changes
  each hopping vector to `R + shift_j - shift_i`. This is applied before the
  physical supercell. Supercell images have the requested lexicographic order,
  and the final new-to-old permutation acts on both matrix axes and positions.
- For a cell change `new_cell = M @ old_cell`, positions before wrapping are
  `(old_position - offset_reduced) @ inverse(M)`. The unimodular inverse is
  rounded once to an integer matrix and checked by an exact integer product.
  Hopping vectors use integer multiplication, not floating-point solutions
  truncated to integers. A determinant close to one is not rejected merely
  because floating-point elimination did not produce exactly `1.0`.
- Half-storage input is maintained throughout geometric transport: the
  Fourier matrix is completed as `F + F.conj().T`, including the already
  half-stored zero block exactly once. Convention 1 is obtained from
  convention 2 using the returned orbital positions. Bands use `eigvalsh`
  without an energy shift.

The historical Fourier and supercell construction are retained. The import
paths now share the corrected loader. Text parsing additionally accepts
arbitrary degeneracy-line wrapping, explicit HR matrix-element order,
Fortran D exponents, and ordinary whitespace/comments in the relevant files.
Original source provenance and licensing remain in `HISTORY.md` and
`TBMODELS_LICENSE.txt`.

## Validation

```sh
python attempt/validate.py --case participant/input/smoke
python attempt/smoke_check.py --input participant/input/smoke --output attempt/result.npz
```

`validate.py` independently sums the full corrected HR contributions directly
into supercell Hamiltonians, without constructing a `Model`. It separately
checks cell transport by Fourier evaluation in the old coordinates and the
analytically required orbital phases. It also exercises:

- Both assignments, skew Cartesian cells, bohr input, and explicit atom ties.
- Shuffled WS records, unequal degeneracies, complex hoppings, and several
  anisotropic supercells, with independent band-folding checks.
- 32 random unimodular transformations in both reduced and Cartesian modes,
  arbitrary half-storage matrices, off-cell positions, and origin shifts.
- Positions exactly on a simple cell boundary and on either side by `2e-10`,
  without snapping nearby physical positions to the boundary.
- End-to-end cases with different import/mapping orbital counts and different
  numbers of k-points; exact output keys, Hermiticity, and both conventions.

The supplied smoke case agrees with the direct import sum to about `6e-15`
in matrix entries. The random geometric tests agree to about `4e-12` in
absolute matrix entries. A smoke CLI run takes about 0.3 seconds here;
a separate 64-orbital dense cell-transport check takes about one second.
`validation_report.json` records the maximum errors of the executed checks.

## Scope and limitations

No external material reference or unseen evaluation input is available, so
validation establishes the stated algebraic and geometric identities rather
than an independent comparison with those materials. The importer expects a
complete Hermitian HR model and retains the historical `1e-12` conjugate-pair
consistency check; it does not repair physically non-Hermitian source data.
It also expects a correction record for every retained HR entry when WS data
are provided, as in the supplied Wannier90 output.

At a mathematically exact cell boundary, floating-point arithmetic can select
either neighboring representative. Hopping shifts always use the same floor
operation as the positional wrapping, so the physical position-inclusive
Hamiltonian remains covariant. Near-boundary positions are not rounded with a
broad tolerance. Extremely ill-conditioned cells or integers outside int64
range are not covered by the tests; an unresolvable integer inverse is rejected
rather than silently used.
