# Symmetry-complete orbital response

Run with the visible NumPy installation; no other package or external data is
required:

```sh
python solve.py --input ../participant/input/smoke --output result.npz
python workspace/smoke_check.py result.npz
python validate.py
```

`solve.py` is the executable entry point. `operators.py` and `response.py` are
its required local modules. The supplied starting workspace is preserved in
`workspace/`. The implementation uses the displayed orbital ordering and
Cartesian frame directly; it does not reapply provenance transformations.

## Operator projection

First reconstruct the full position coefficients

    P_nm(R) = connection_nm(R) + delta_R0 delta_nm centers_m.

For every operation and source pair, the image translation is

    R' = S R + shift_m - shift_n.

The Hamiltonian is mapped by `U H U†`, with source coefficients conjugated for
antiunitary operations. The position is mapped by `U (O P) U†`, with the same
conjugation, and has the additional affine onsite contribution

    U diag(t_cart - shift_n_cart) U†.

This is the polar, time-reversal-even transformation of the position of the
image ket, followed by translating its bra back to cell zero. Fractional
translations and orbital cell shifts therefore cannot be omitted even though
the connection is stored center-subtracted.

All operations receive equal weight. The support is the union of their complete
images and the original support; no coefficient cutoff, hopping truncation,
orbital reduction, or Hermitian projection is used. Source orbitals are grouped
by cell shift only to perform the same sum with matrix multiplication.

The repaired centers are the real onsite diagonal of the averaged full position
operator. Subtracting them defines the returned connection. Off-diagonal onsite
position elements participate in this center extraction when an operation mixes
orbitals. Any imaginary onsite diagonal is retained in the connection, as are
all other coefficient-level deviations from adjoint symmetry.

## Response conventions

Both models use the required embedded Fourier phase. Derivatives multiply each
coefficient by `i (R_cart + center_m - center_n)_a`; these are Cartesian
wavevector derivatives, not reduced-coordinate derivatives. The Fourier
Hamiltonian, connection, and their derivatives are Hermitized, without modifying
the real-space operators.

Write `Abar = V† A V`, where `V` diagonalizes the Hermitian Fourier Hamiltonian.
Only occupied-to-complement blocks are needed:

    D_nm,a = (V† partial_a H V)_nm / (E_m - E_n),  n in I, m in J
    B_nm,a = Abar_nm,a + i D_nm,a
    T_ab   = sum_(n in I,m in J) B_nm,a conj(B_nm,b)
    T0_ab  = sum_(n in I,m in J) Abar_nm,a conj(Abar_nm,b).

The requested optical numerator is `Q_ab = i T_ab`. The Berry trace is

    Omega_ab = Tr_I[V† (partial_a A_b - partial_b A_a) V]
               - 2 Im(T_ab - T0_ab).

Equivalently, it is the trace of the basis non-Abelian curvature
`partial_a A_b - partial_b A_a - i[A_a,A_b]` plus the inter-subspace connection
contribution. Keeping this basis-curvature term is essential: the Berry trace
is not generally recoverable from the optical kernel alone. The stored order
is `(Omega_yz, Omega_zx, Omega_xy)`. The original energies are returned in
ascending order, and both responses include the complete specified subspace.

## Validation

`validate.py` checks:

- The two-band analytic Berry sign and connection-only optical transitions.
- Cartesian derivatives and both responses against independent projector finite
  differences, including non-adjoint real-space connection coefficients.
- Dense complex orbital-basis changes with re-extracted centers, fully included
  degenerate subspaces, and improper passive Cartesian frame changes.
- Identity preservation, affine dense-orbital inversion, nonsymmorphic support
  expansion and shifts, and antiunitary time reversal.
- Optical anti-Hermiticity and positivity of `-i Q`.

The supplied full-material smoke case also passes its provided checker. Recorded
checks on that case give:

- Hamiltonian coefficient agreement with the supplied scalar projection:
  maximum absolute error `2.3e-16`.
- Original energy agreement with its supplied implementation: `1.6e-14` eV.
- Repaired Hamiltonian adjoint residual: `4.5e-16` eV.
- Repaired time-reversal Berry/optical residuals below `8.1e-14` square angstroms.
- Independent projector finite-difference Berry/optical errors below `2.8e-8`
  square angstroms at Cartesian step `2e-6` inverse angstroms.
- Reprojection changes below `7.4e-9` in the position coefficients. Covariance
  over all twelve operations has maximum Berry/optical residuals `6.4e-7` and
  `1.4e-6` square angstroms. The supplied orbital rotation matrices themselves
  have unitarity residuals around `1e-8`; they are used as supplied, not silently
  altered to impose a different group representation.

## Scientific limitations

Degeneracies wholly within I or J require no denominator and do not affect the
traces. If the requested band count splits an exactly degenerate eigenspace,
there is no unique smooth spectral subspace. The solver emits a warning and
sets the inverse gaps of only those unresolved pairs to zero (a finite
pseudoinverse convention); the resulting boundary-degenerate response is not
claimed to be uniquely physical or invariant under rotations across that
boundary. Nonzero resolved small gaps are not broadened.

The results are responses of the complete supplied finite Wannier model. They
are not a frequency-dependent conductivity, a treatment of bands outside that
model, or a metal's physical Fermi occupation. No unseen-material numerical
reference was available; validation uses the supplied smoke case and independent
analytic, finite-difference, gauge, and symmetry checks.
