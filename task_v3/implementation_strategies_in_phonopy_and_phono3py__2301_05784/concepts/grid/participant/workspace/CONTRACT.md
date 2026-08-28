# Array and mathematical contract

## Invocation and environment

`python solve.py INPUT.npz OUTPUT.npz` takes exactly two positional paths.
Use ordinary, unpickled NumPy archives. Output only the five named arrays below;
all floating-point outputs must be finite. Deliver `solve.py` to the
runner-designated attempt/output directory; `workspace/` is read-only starter
material. Inputs are immutable. Python 3.10,
NumPy 1.21.5, and SciPy 1.8.0 are available in the execution sandbox. No network,
phonopy, phono3py, spglib, author files, other cases, or reference data are
available. Thread counts are one. Each case has a 180-second elapsed-time limit
and an 8192-MiB address-space limit; reported memory is peak resident KiB.

## Input arrays

Let N be the number of grid points, B the number of supplied branches, K the
number of geometry queries, and M the number of spectral thresholds.

| Key | dtype, shape | Meaning |
| --- | --- | --- |
| `grid_matrix` | int64, (3,3) | Nonsingular integer matrix A, det(A)=N>0. Not necessarily diagonal or triangular. |
| `reciprocal_lattice` | float64, (3,3) | Cartesian reciprocal basis C as **columns**, in inverse angstroms, **without 2*pi**. |
| `grid_addresses` | int64, (N,3) | A complete, arbitrary-order set of representatives a of Z^3 / A Z^3, as rows. |
| `query_addresses` | int64, (K,3) | Integer addresses a for geometry; may lie outside the supplied representative set. |
| `frequencies` | float64, (N,B) | Mode energies in THz, in exactly `grid_addresses` row order. Each column is interpolated independently. |
| `sampling_points` | float64, (M,) | Strictly increasing thresholds in THz. |
| `tie_tolerance` | float64, scalar () | Absolute tolerance on squared Cartesian reciprocal distance. |

Physical fractional q is A^(-1)a (column-vector convention). Addresses a and b
are equivalent precisely when a-b is in A Z^3. Frequency values at equivalent
addresses are identical by definition. Input rows are not guaranteed to be
lexicographic, a diagonal tensor-product order, or symmetry reduced. No extra
symmetry multiplicities are to be applied. Frequencies come from harmonic force
data; negative signed frequencies, repeated values, narrow branches, and
crossings are allowed. A one-point grid is a legitimate exactly flat periodic
interpolant of physical zone-center modes, not a finite-width peak.

## Geometry outputs

For query a, put q=A^(-1)a and

    d_min = min over n in Z^3 of || C (q+n) ||_2^2.

Return **all** integer shifts n whose squared distance is at most
`d_min + tie_tolerance`. The shift is added to q, not subtracted. Shifts are in
the original reciprocal fractional basis, not the integer-address basis.

| Key | dtype, shape | Meaning |
| --- | --- | --- |
| `image_offsets` | int64, (K+1,) | CSR offsets, starting at 0 and ending at L; every query has at least one image. |
| `image_shifts` | int64, (L,3) | Shifts for query k occupy `[image_offsets[k]:image_offsets[k+1]]`; unique and lexicographically sorted within each query. |
| `distance2` | float64, (K,) | d_min, in inverse square angstroms. |

There is no global fixed image multiplicity, search box, or component-rounding
assumption. Translated queries must have correspondingly translated shifts.

## Spectral mesh convention

The microcell basis is H=C A^(-1). Each representative a anchors one periodic
unit cube in integer-address coordinates. Cube vertex v is
`(v&1, (v>>1)&1, (v>>2)&1)`, for v=0,...,7. Its frequency is that of the
representative equivalent to a+v. These N cubes tile the reciprocal torus once.

Choose the shortest Cartesian cube body diagonal, using the first entry for an
exact floating-point tie, in this order: H(1,1,1), H(-1,1,1), H(1,-1,1),
H(1,1,-1). The following unordered vertex sets define the six tetrahedra in
every cube; these sets specify the mesh, not an integration implementation.

| Diagonal index | Six tetrahedron vertex sets |
| --- | --- |
| 0 | 0173, 0175, 0273, 0276, 0475, 0476 |
| 1 | 1602, 1604, 1623, 1637, 1645, 1657 |
| 2 | 2501, 2504, 2513, 2537, 2546, 2567 |
| 3 | 3401, 3402, 3415, 3426, 3457, 3467 |

Within each tetrahedron, linearly interpolate each branch in barycentric
coordinates. For four corner values e_j and uniform normalized barycentric
measure dmu on the three-simplex (integral dmu=1), define

    F_t,b(omega) = integral 1[sum_j lambda_j e_j <= omega] dmu(lambda)
    D_t,b(omega) = d F_t,b(omega) / d omega.

| Key | dtype, shape | Meaning |
| --- | --- | --- |
| `cumulative` | float64, (M,B) | (1/(6N)) sum over all 6N tetrahedra of F_t,b at each threshold. |
| `dos` | float64, (M,B) | (1/(6N)) sum over all 6N tetrahedra of D_t,b at each threshold; units THz^(-1). |

Normalization is **per supplied branch**: cumulative tends to 1 above that
branch, and DOS integrates to 1 including any point masses. Do not sum branches
or multiply by cell volume, atom count, spin, or 2*pi. A flat tetrahedron at e
has cumulative 0 below e and 1 above e; its ordinary DOS is 0 away from e and
its unit point mass is represented by that cumulative jump. Repeated corner
energies use the continuous simplex-integral limit, not artificial smearing.
No threshold equals any input frequency: the separation exceeds 1e-10 THz.
Thus no evaluation convention at a point mass or exact energy knot is needed.

## Scoring

Geometry combines mean image-set Jaccard error and normalized distance RMSE.
Spectra combine branchwise normalized RMSE for DOS and cumulative, equally.
Each independent component quality is
`1/(1 + error/max(measured_baseline_error, 1e-8))`. There is no acceptance
tolerance plateau: any residual error lowers quality. Perfect quality is 1;
the ordinary baseline level is 0.5. Baseline-exact components use the explicit
1e-8 normalization floor. Malformed components receive zero, without
erasing a valid independent component. Family-balanced mean and worst-family
quality are both reported, as are per-component quality, measured elapsed time,
peak RSS, and speed/memory ratios against the same case's measured baseline.
The tournament uses scientific core quality; resources are measured and
reported separately, not substituted for accuracy. Cases and resource ratios
are never inferred from the smoke input.
