# Exact higher-order composite fluctuations

These are private candidate definitions, not changes to the frozen task.
The Hamiltonian and Pauli normalization are the unchanged
`H = -sum XX -sum Z`, with spin eigenvalues plus/minus one.

## General even-X moment

For ordered sites `x1 < x2 < ... < x(2m)`, let

```
A = union_i {x(2i-1)+1, ..., x(2i)}
B = union_i {x(2i-1), ..., x(2i)-1} = A-1
```

The infinite critical ground-state moment is the determinant with entries
`1 / [pi * (A_row - B_column - 1/2)]`. Jordan-Wigner cancellation leaves the
alternating Majorana strings on precisely these disjoint intervals; Wick's
theorem reduces their expectation to this determinant. The orientation is
fixed by `<X_0 X_1> = 2/pi > 0`, not chosen after looking at an MPS.

For an even periodic spin chain of size `N`, in its even-parity ground state,
the corresponding matrix entries are
`1 / [N * sin(pi*(A_row-B_column-1/2)/N)]`.
`manybody.validate_ed` independently constructs the full spin Hamiltonian,
without using a fermionic Hamiltonian or choosing a parity sector, and checks
all six-site combinations at `N=6,8,10,12` against this determinant. It also
checks the finite connected quantity below directly from spin expectations.

## Third joint cumulant of three interval pairs

Let `Q1=X_a X_b`, `Q2=X_c X_d`, `Q3=X_e X_f`, with
`a<b<c<d<e<f`. The proposed observable is

```
K3 = <(Q1-<Q1>)(Q2-<Q2>)(Q3-<Q3>)>
   = <Q1 Q2 Q3> - <Q1 Q2><Q3> - <Q1 Q3><Q2>
                 - <Q2 Q3><Q1> + 2<Q1><Q2><Q3>.
```

This is the connected three-point function of the pair-composite operators,
not the fully connected cumulant of six individual X operators. It probes
non-Gaussian joint fluctuations of interval order, beyond their pairwise
covariances. Every subtraction in the submitted observable uses the
submitted state's own means and lower moments; exact targets use exact
ground-state means and lower moments.

Let `mi` be the exact XX mean of interval `i`, and define for two disjoint
intervals `i` and `j`

```
Sij = sum_{u in A_i, v in A_j} -log1p(-1/[4(v-u)^2])
hij = expm1(Sij).
```

The Cauchy product identity separates within-interval and cross-interval
factors, giving

```
<Q1 Q2 Q3> = m1*m2*m3 * exp(S12+S13+S23)
K3_exact  = m1*m2*m3 * (h12*h13 + h12*h23 + h13*h23 + h12*h13*h23).
```

The latter expression is positive and avoids cancellation of nearly equal
six-, four-, and two-point moments. The finite-size product uses the same
expression, with interval means computed from the sine determinant and

```
Sij(N) = sum_{u in A_i, v in A_j}
           -log1p(-sin(pi/(2N))^2 / sin(pi*(v-u)/N)^2).
```

The code checks the infinite product against independently formed dense
determinants and rechecks selected targets by 70-digit direct sums, not just
the fast long-double prefix implementation used in the broad scan.

## Submitted-state contraction audit

For transfer channel `E` and X insertion `EX`, define the full interval map
`M_l = EX E^(l-1) EX`. The centered map is
`M_l - m_l E^(l+1)`, **not** `M_l - m_l I`.
The identity channel must propagate through all `l+1` physical sites in an
interval. The two outer centered boundaries simplify using stationarity
and right canonicality. Batched parity-sector contractions are independently
compared with full-matrix, site-by-site raw moments followed by the literal
cumulant subtraction above.

The finite-size spin ED certificates validate normalization and signs;
high precision validates exact small differences; full-matrix sequential
contractions validate the submitted quantity. None of these checks assumes
that the submitted MPS is Gaussian or is an exact ground state.
