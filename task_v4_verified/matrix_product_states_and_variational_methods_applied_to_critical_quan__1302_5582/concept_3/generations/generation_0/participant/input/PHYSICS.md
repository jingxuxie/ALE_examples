# Exact finite-system definition

With hbar = lattice spacing = 1, the open-chain Hamiltonian is

```text
H = sum_i [pi_i^2/2 + mu2*phi_i^2/2 + lambda*phi_i^4/24]
    + kappa/2 * sum_{i=0}^{L-2} (phi_{i+1} - phi_i)^2,
[phi_i, pi_j] = i delta_ij, lambda > 0, kappa > 0.
```

There is one bond for L=2 and two bonds for L=3, no periodic double counting,
no counterterm, no normal-ordering subtraction, and no continuum extrapolation.
All parameters and gaps are in the same lattice units.

The parity operation flips every phi and pi. Write E_a^+ and E_a^- for the
ordered levels within the even and odd sectors, with a=0,1,... . Outputs are
`odd_gap = E_0^- - E_0^+`, `even_gap = E_1^+ - E_0^+`, and
`odd_spacing = E_1^- - E_0^-`. The first is an odd particle-like gap in the
single-well regime and a tunnelling splitting in deep finite double wells.
The latter two describe excitation spacings within fixed parity. No assertion
that these are asymptotic scattering-particle masses is made.

## Low-cutoff input records

Every case has `id`, `family`, `sites`, `mu2`, `lambda`, `kappa`, `boundary`, and
six `spectra` entries. Each entry uses an independent product basis
`|n_0,...,n_{L-1}>`, `0 <= n_i < cutoff`, with
`phi=(a+a_dagger)/sqrt(2*omega)` and
`pi=i*sqrt(omega/2)*(a_dagger-a)`. Parity is `(-1)^sum(n_i)`.
Crucially the Hamiltonian uses `P phi^2 P`, `P phi^4 P`, `P pi^2 P`,
not powers of `P phi P` or `P pi P`. Mixed-site products are tensor products
of the corresponding projected local factors. Projection is onto the same
product Fock space for every term.

`even_energies` and `odd_energies` are the two lowest levels per sector of
`H - energy_origin*I`. The common origin is the sum of the classical on-site
potential minima, `-L*3*min(mu2,0)^2/(2*lambda)`. Add it to either array to
recover physical energies; differences do not need it. `signed_gaps` contains
the three directly computed low-cutoff differences, which are not labels.
The first may even be negative: separate finite parity projections need not
preserve the exact ground-state ordering. Do not interpret it as a positive
physical tunnelling gap by definition.

`state_residuals` is a 2-by-2 array of Euclidean residual norms in physical
energy units; rows are even/odd and columns are levels 0/1.
`boundary_weights` has the same layout and contains
`mean_i Pr(n_i >= cutoff-2)` in each state. Values are dimensionless, in [0,1].
No high-cutoff observable, certificate, private seed, or private label is a
public feature. Training cases additionally have a `targets` object. Validation
labels use the prediction-output schema. IDs are opaque, not physical features.

## Source connection

Seed: Milsted, Haegeman and Osborne, arXiv:1302.5582v3, *Matrix product states
and variational methods applied to critical quantum field theory*. The seed
studies lattice phi4, local oscillator truncation, and excitation masses. This
benchmark uses its lattice-Hamiltonian setting, specialized to small open chains
with variable bond strength. It implements finite-space exact diagonalization,
not the paper's infinite uniform-MPS optimization, and does not reuse published
mass tables as labels. The finite Hamiltonian above is the complete definition.
