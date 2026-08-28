# Symmetry-complete orbital response solver

Run with the visible Python/NumPy environment; no downloads or additional packages
are needed:

```sh
python /path/to/attempt/solve.py --input /path/to/case --output /path/to/result.npz
python /path/to/attempt/test_solver.py
python /path/to/attempt/workspace/smoke_check.py /path/to/result.npz
```

The supplied workspace is preserved in `workspace/`. The executable implementation
is `solve.py`, with `symmetry.py` and `response.py` beside it. Metadata describing
orbital ordering and Cartesian frames is not reapplied to the numerical arrays.

## Operator projection

The implementation first reconstructs the full position coefficients
`X_nm(R) = connection_nm(R) + delta_R0 delta_nm centers_n`. For each supplied
operation it sends a source matrix element to

`R_image = S R + shift_m - shift_n`.

The Hamiltonian contribution is `U_jn H_nm U_lm*`. The position contribution is

`U_jn [C X_nm + delta_R0 delta_nm (t_cart - shift_n_cart)] U_lm*`.

For an antiunitary operation the source H and X coefficients are conjugated
before this transformation. Position is time-reversal even and polar, so its
Cartesian transformation is C, without a time-reversal sign or determinant.
All operations receive equal weight, and the complete image support is included.
No Hermitization or small-coefficient truncation is performed on this output.

The repaired Wannier centers are the real onsite diagonal of the projected full
position operator; subtracting them gives the repaired connection. This includes
the contribution of onsite off-diagonal position elements when U mixes orbitals,
not just a probability-weighted transformation of the original diagonal centers.
Any imaginary onsite diagonal remainder stays in the connection, preserving the
complete full-position coefficients even for non-Hermitian input data.

## Responses and conventions

Both models use the specified positive-phase, center-embedded Fourier transform.
Analytic derivatives multiply each coefficient by
`i * (R @ lattice + center_m - center_n)` in Cartesian coordinates. Each Bloch
operator and its derivatives are Hermitized consistently, not its real-space
coefficients. Original energies are calculated before any repair.

Let `A_a` and `B_a` be the position connection and Hamiltonian derivative in the
eigenbasis, and use indices n in the occupied subspace and m in its complement.
The cross-subspace eigenvector derivative is

`D_nm,a = B_nm,a / (E_m - E_n)`.

The transition matrix is `K_nm,a = A_nm,a + i D_nm,a`, and the returned complex
kernel is exactly `Q_ab = i sum_nm K_nm,a K_nm,b*`. In particular Q is
anti-Hermitian and Q/i is positive semidefinite; its real part is antisymmetric
and its imaginary part is symmetric.

For each ordered pair (a,b) = (y,z), (z,x), (x,y), the curvature trace is

```text
Tr_I[U† (partial_a A_b - partial_b A_a) U]
  - 2 Im sum_nm D_nm,a D_nm,b*
  - 2 Re sum_nm (D_nm,a A_nm,b* - D_nm,b A_nm,a*) .
```

This is the curl of the Hamiltonian-gauge Berry connection with the convention
`A = i <u|grad u>`. It includes both the position-connection curl and its mixed
terms with the eigenvector derivatives. Only cross-subspace denominators are
formed, so degeneracies wholly within either subspace require no gauge choices.
There is no frequency integration, Fermi weighting, broadening, or SI conversion.

## Validation

`test_solver.py` checks a direct element-by-element affine projection, idempotence,
preservation of non-Hermitian real-space data, analytic derivatives on a skew
lattice, Berry curvature against finite differences of spectral projectors,
optical kernels against independent projector finite differences, an analytic
two-band curvature sign, arbitrary rotations of included degenerate eigenspaces,
center-embedding gauge changes, complex local orbital-basis changes, orbital
permutations, spinful antiunitary symmetry, improper Cartesian frame covariance,
empty/full subspaces, and finite-difference curvature on the supplied full-material
smoke model before and after repair.

The supplied smoke run has 24 orbitals and expands 195 R rows to 483. Its repaired
Hamiltonian adjoint residual is about 4.5e-16 eV; Hamiltonian coefficients agree
with the supplied scalar projector to 1.8e-15 eV. Original energies agree to
1.6e-14 eV. Repaired time-reversal Berry and optical residuals at the supplied
opposite points are below 2e-13 in their respective units. Repeating the operator
projection changes position coefficients/centers by less than 8e-9 angstrom;
the supplied Cartesian/orbital representations themselves contain rounding at
roughly the 1e-8 level.
Across all supplied magnetic operations, transformed-point energy residuals are
below 4e-8 eV, Berry residuals below 7e-7 angstrom squared, and optical residuals
below 1.4e-6 angstrom squared, consistent with that representation rounding.

## Scientific limitations

- An occupied boundary cutting an exactly degenerate eigenspace does not define
  a unique differentiable spectral subspace. For gaps below a numerical
  roundoff threshold the solver emits a warning and uses a zero pseudoinverse
  for those gaps; such results are a finite convention, not a uniquely defined
  physical Berry response. Degeneracies entirely inside either subspace do not
  have this limitation. Very small resolved cross-subspace gaps can produce
  legitimately large, numerically sensitive responses.
- Results are those of the complete supplied finite Wannier model, including its
  supplied position matrix. No claim is made about missing external bands or
  convergence to an untruncated first-principles response.
- Only the supplied material has been exercised as a real-material case; the
  other checks are controlled numerical/analytic invariants, not comparisons
  against an unavailable independent first-principles reference.
