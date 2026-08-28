# Finite Wannier-device transport

Run with the supplied NumPy/SciPy environment:

```sh
python solve.py --input CASE.npz --output RESULT.npz
```

The output contains all required schema fields, including one ordered `sigma_j`
array per contact. `example_result.npz` is the result for the supplied smoke
input. The original bulk interpolator and its provenance/license are retained.

## Numerical method

- Assemble the finite Hamiltonian sparsely from every nonzero entry of every
  full directed hopping block. Add the supplied orbital-resolved potential;
  do not add conjugate blocks or embedding-dependent phases.
- Construct the principal-layer onsite and outward-to-inward coupling exactly
  in the specified interface order. No inverse of the coupling is used.
- Factor the coupling as `B = U V†`. Exactly zero rows/columns are removed.
  When the sparsity pattern proves additional rank deficiency, an SVD retains
  the full structural-rank bound, including arbitrarily small nonzero singular
  values. There is no hopping-magnitude cutoff or fitted Hamiltonian.
- At each real energy, solve a reduced generalized-Schur pencil. Keep its
  complete decaying invariant subspace, including zero-eigenvalue Jordan
  structure. Resolve propagating modes by their outward current; diagonalize
  the current form within degenerate momentum subspaces. Recover
  `Sigma = V (U† g U) V†`. A full unreduced pencil is the fallback when the
  isolated-layer resolvent is singular or the reduced Dyson residual is large.
- Factor the positive, propagating part of `Gamma` as `W W†`, removing only
  numerical anti-Hermitian residuals outside the independently counted channel
  subspace. The selfenergy and device resolvent use real energy throughout:
  there is no artificial imaginary onsite potential or finite broadening.
- Factor the sparse open-device operator with SuperLU. Solve only for channel
  source vectors, in bounded batches. Form `S = I - i W† G W`, its complete
  terminal blocks, singular-value spectra, pair partition factors, and
  Landauer–Büttiker matrix. The full device inverse is never formed.

## Validation and scope

The supplied smoke input gives three channels in each lead, transmission
`1.95084952`, and partition factor `0.04679127`. Independent dense
device calculations reproduce the transmission eigenvalues; an independently
implemented surface-decimation extrapolation reproduces the selfenergies.
Additional checks cover analytic scalar barriers, a three-terminal junction,
singular and nonminimal principal layers, degenerate opposite-current modes,
closed contacts, complex random leads, Bloch-band channel counting, and
arbitrary device/interface ordering and lattice-origin changes. Current and
Dyson residuals are generally around `1e-13` or smaller in these checks.

Resource checks use larger finite cuts of the supplied Hamiltonian, including
12,000 orbitals and a 7,440-orbital three-terminal device at three energies,
under a 1,024 MiB address-space limit. A further 11,520-orbital gated device
with 768-orbital interfaces and three energies completed in 75.0 seconds with
538.3 MiB peak resident memory, under both a 90-second timeout and the address
limit; its largest current-conservation defect was `1.4e-12`. These are
self-consistency and analytic checks, not comparisons with unavailable labeled
transport answers. No actual InAs input is supplied, so that material has not
been independently validated.

The model remains the specified coherent, ideal finite bulk cut, not a
calibrated surface/device model. Exact mode thresholds, singular flat-band
pencils, and exact surface-state poles can require separate limiting
procedures; the implementation does not replace such singularities with a
phenomenological broadening. Runtime and memory depend on interface size and
sparse-factor fill, not only the total orbital count.
