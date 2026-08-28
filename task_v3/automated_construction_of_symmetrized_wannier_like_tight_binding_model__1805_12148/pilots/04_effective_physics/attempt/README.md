# Gauge-resolved low-energy exporter

Run with the supplied Python environment (NumPy and SciPy):

```sh
./solve.py --input ../participant/input/smoke.npz --output result.npz
```

`solve.py` is executable and self-contained. It also exposes `export(case)` for
an NPZ archive or a dictionary of arrays. The output contains exactly the six
complex128 arrays `U`, `H0`, `H1`, `H2`, `H3`, and `G` in the supplied contract.
All remote bands are used. No electronic-structure data are fitted, filtered,
or averaged over symmetry operations. Cartesian axes remain the supplied axes;
`cart_rotation` is not needed to compute the internal-basis intertwiner or the
Cartesian tensors.

## Basis recovery

The unitary and antiunitary intertwining equations are assembled as one
**real-linear** system in the real and imaginary parts of `U`. Candidate
intertwiners are obtained from its smallest-singular-value subspaces. Considering
multiple subspace dimensions avoids assuming irreducibility or a particular
residual gauge. The polar factor of an invertible exact intertwiner is a unitary
intertwiner, also for antiunitary generators.

The best polar candidates are refined by least squares with the exactly unitary
parameterization `U_initial exp(i K)`, where `K` is Hermitian. This permits
rounded numerical representations without assuming that the equations have an
exact solution. Only representation arrays enter this fit, not Hamiltonian or
spin data. All physical tensors are subsequently transformed by `U† H U`.

## Canonical reduction

The following formulas apply in the supplied target eigenbasis, before the final
change of basis. Let `P` denote the retained bands and `Q` all other bands. Define

```text
c   = 3.809982208629016 eV Angstrom^2
v_a = (2 c / bohr) momentum[a]
A_a = P v_a P
C_a = Q v_a P
B_a = Q v_a Q
D_ri = 1 / (E_i - E_r),   i in P, r in Q
```

Using elementwise multiplication `*` only in the formulas containing `D`, the
first two wave-operator coefficients are

```text
X_a  = D * C_a
X_ab = D * (B_a X_b - X_a A_b).
```

They follow from the invariant-subspace Riccati equation. The canonical embedding
is `[I; X] (I + X†X)^(-1/2)`, whose retained diagonal block is Hermitian positive.
Expanding its Hermitian Hamiltonian through cubic order gives

```text
R_ab   = (C_a† X_b + X_a† C_b) / 2
H0     = diag(E_P)
H1_a   = A_a
H2_ab  = c delta_ab I + Sym_ab R_ab
H3_abc = Sym_abc Herm(C_a† X_bc).
```

Here `Herm(M) = (M + M†)/2` and `Sym` is the average over Cartesian permutations,
not the sum. These are polynomial coefficients, with no extra factorials.
For example, an off-diagonal quadratic coefficient occurs twice in the full
Cartesian contraction. The `-X_a A_b` term supplies the retained-space
normalization/folded contribution; omitting it would not give the canonical
Hermitian cubic Hamiltonian. No denominator between two retained energies is
introduced. The common free-electron quadratic term is proportional to the
full-space identity and produces no additional cubic term. For order 2, `H3`
is exactly zero.

## Magnetic response

The ordered coefficient `R_ab`, before Cartesian symmetrization, retains the
information lost when the wavevectors are assumed to commute. The specified
electron commutator gives

```text
G_gamma = spin[gamma] - i/(2 c) sum_ab epsilon_abgamma R_ab.
```

In particular, `G_z = spin[z] - i (R_xy - R_yx)/(2 c)`. Since the contract uses
`H_Z = mu_B G.B` and supplies projected Pauli-spin matrices, the spin contribution
is added with coefficient one. There is no extra factor of two. This formula
uses only the remote space and has the same pairwise Hermitian energy
denominators as `H2`. It also transforms as an axial vector under a reflection.

## Validation performed

- **Supplied 800-band smoke input:** the command completed in 1.07 seconds with
  approximately 108 MiB peak resident memory, with one BLAS thread. All output
  arrays have the required shapes, complex dtype, and finite entries.
- **Smoke basis:** unitarity error was zero at printed precision; generator
  residual norms were `4.04e-7`, `1.57e-16`, and `9.82e-8`, consistent with the
  input representation rounding. Matrix Hermiticity was exact at printed
  precision; Cartesian permutation differences were at most `1.78e-15`.
- **Independent exact canonical reduction of the smoke Hamiltonian:** selected
  exact eigenvectors were aligned by the polar factor of their retained block.
  Along an oblique direction, halving `|q|` from `0.016` to `0.002` inverse
  Angstrom reduced the cubic model error by factors `15.70`, `15.86`, and
  `15.93`, approaching the expected fourth-order factor of 16. The final
  matrix error was `6.21e-10` eV.
- **Synthetic nondegenerate four-band target:** comparison with independent
  exact canonical block diagonalization gave error reduction factors `15.95`,
  `15.98`, and `15.99`. This checks the cubic normalization terms without
  assuming equal target energies. Order-2 export agreed in all lower-order
  arrays and returned an exactly zero cubic tensor.
- **60 basis-recovery cases:** dimensions 1 through 4, unitary-only generators,
  antiunitary real structures, Kramers structures, repeated spinor irreps,
  distinct characters, and generic constraints were checked with exact data
  and noise amplitudes `1e-6` and `1e-3`. Maximum exact intertwining error was
  `2.57e-14`; maximum unitarity error was `2.99e-15`. Noisy fitted residuals
  were no larger than those of the known generating basis, to numerical
  precision.
- **Zeeman sign and normalization:** for a two-band Dirac model with coupling
  `lambda` and remote gap `Delta`, the solver gives
  `G_z = -lambda^2/(c Delta)` for the lower band with zero supplied spin.
  Direct diagonalization with noncommuting oscillator wavevectors confirmed
  the predicted weak-field energy shift, with the remaining error quadratic
  in field.
- **Quasi-degenerate Zeeman check:** a separate five-band oscillator model
  with two distinct retained energies reproduced `H2` plus the orbital `G`.
  Centered finite differences of the exact canonical Hamiltonian approached
  the predicted quadratic coefficient with error reduction factors `3.99967`
  and `3.99994` when the wavevector scale was halved.
- Proper and improper Cartesian-coordinate changes reproduced the expected
  polar Hamiltonian tensors and axial magnetic tensor to below `3e-15`.
  Unitary gauge changes within degenerate target and remote spaces, full-band
  permutations, and target-order permutations agreed to below `9e-15`.
  Empty remote space was also checked.

These are numerical and analytic consistency checks, not comparisons with
unavailable labeled material-reference tensors. `smoke_result.npz` is the
generated output for the supplied smoke case.

## Scientific limits

The expansion is local in wavevector and weak field. Its useful range depends
on the remote gaps and matrix elements; it is not a globally accurate band
interpolation. The requested constant `G` does not include wavevector-dependent
magnetic terms or higher powers of field.

A target exactly degenerate with an excluded band has no nonsingular reduction
of this type; the exporter raises an error rather than regularizing a zero gap.
Small nonzero gaps are used without modification, but can greatly restrict the
validity range and worsen numerical conditioning. Degeneracies entirely inside
the target or entirely inside the remote space are allowed.

Inconsistent representation data need not admit an exact admissible basis; the
returned basis then minimizes the representation residual numerically. No
material-specific accuracy beyond the supplied matrices, no convergence in the
number of electronic-structure bands beyond those supplied, and no behavior on
unseen labeled cases can be established from the unlabeled smoke input alone.
