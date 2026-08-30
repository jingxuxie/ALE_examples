# Submitted partial witness

`witness.json` contains a constant reference kernel and a reciprocal,
inversion-symmetric, Fourier-limited kernel with the same degree profile and
the same full velocity-projected Dirichlet matrix.

- Degree profile: `d(theta) = 1` for both kernels.
- Dirichlet matrix: `D = I_2/2` for both kernels.
- Linewidth moments for orders 0, 1, 2: `1`, `1.9`, `4.9` at every angle.
- Transport moment matrices: `I_2/2`, `0.95 I_2`, `2.45 I_2`.
- Reference conductivity: `diag(0.5, 0.5)`.
- Second conductivity: `diag(0.70781230538142, 0.9895393685137284)`.
- Conductivity-trace ratio: **1.6973516738951484**.

The requested **1.75** ratio was not reached. This is a valid partial result,
not a falsification of the stated factor-1.75 claim.

For the second kernel, the required 1024-point continuum certificate gives
`0.08000010000032849 <= K <= 5.9999998999973325`, and the Fourier collision
gap is `0.2819261518892668`. Independent direct collision solves on 64, 128,
and 256 angles satisfy the invariant and numerical-consistency checks.
Details are saved in `validation.json`; the supplied local check is saved in
`supplied_check.json`. The only scored artifact is `witness.json`.
