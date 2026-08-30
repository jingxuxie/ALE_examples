# Finite-chain phi4 MPS solver

The submission entry point is `solve.py`. It needs only Python, NumPy, and SciPy.

```sh
python solve.py --request REQUEST.json --output STATE.npz
```

The output is an uncompressed NPZ containing only `A0`, ..., `A{n_sites-1}`.
The solver does not read saved states, launch subprocesses, or access the network.
`contractor.py` is copied from the participant assets and retains the specified
padded-oscillator Hamiltonian and output validation routines.

## Optimization

- Transform each site's complete finite basis to onsite eigenvectors; do not
  truncate the physical space or replace projected powers by truncated powers.
- Use explicit virtual parity labels and blockwise Schmidt truncation for
  constrained requests, so the entire requested bond cap is available without
  doubling bonds for a final projection.
- Initialize with parity-compatible onsite products or Hartree superpositions.
  Opposite orientations and field-aligned Hartree starts address ordered and
  inhomogeneous chains. Long-budget unrestricted requests compare independently
  optimized small-bond starts. Unrestricted solutions also undergo a global
  reflection energy check.
- Optimize two-site effective Hamiltonians using specialized dense contractions
  and a restarted, diagonally preconditioned Davidson solver. Grow from a small
  preliminary bond to the requested cap.
- Finish with variational one-site sweeps at fixed bond dimension, avoiding the
  residual energy penalty of repeated two-site truncations.
- Check CPU and wall deadlines inside local solves and between updates. CPU
  accounting includes imports; wall accounting begins before numerical imports.

## Local validation

All validation uses participant assets or independently generated requests.
No hidden cases, reference energies, or evaluator files are available here.

- Nine four-site checks against full Hamiltonian diagonalization agree to about
  machine precision, covering all sectors and three potential regimes.
- Twelve decoupled nine-site checks cover even and odd physical dimensions,
  nontrivial lowest local parity, zero couplings, and all requested sectors.
- Nineteen public/synthetic chains were each run in independent cold-start
  processes at 6- and 40-second CPU limits and a 2-GiB address-space limit.
  All 38 outputs pass the public contractor, including parity and bond checks.
- The synthetic tests include 22 sites, physical dimension 14, bond caps 6 and
  12, weak links, separated ordered regions, mixed fields, and odd excitations.
  The largest observed short-versus-long energy difference was approximately
  `5.1e-8`; this comparison is not a claim about hidden reference quality.

Reproducible checks and logs are in `experiments/`. In particular:

```sh
python experiments/check_exact.py
python experiments/edge_checks.py
bash experiments/resource_checks.sh
```

The hidden score cannot be calculated from the released assets.
