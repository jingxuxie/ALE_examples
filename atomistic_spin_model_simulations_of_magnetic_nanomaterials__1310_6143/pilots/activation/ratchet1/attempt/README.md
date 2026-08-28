# Magnetic-chain transition solver

Run with the supplied NumPy/SciPy environment:

```sh
python solve.py CASE.json OUTPUT.npz
```

`solve.py` is self-contained and does not need the baseline or `energy.py`.
It limits numerical libraries to one thread. Set `SPIN_VERBOSE=1` to print
candidate barriers, basin classifications, and timing to standard error.
It does not use case identifiers, family labels, seeds, or stored answers.

## Method

- Detect a common invariant spin plane from the actual minima, field, and
  anisotropy tensors. Use angular coordinates only when that invariance is
  verified. Otherwise, use the full product of spin spheres.
- Search coherent rotation, both open boundaries, and weak regions/interfaces
  identified from the spatial stiffness profile. Localized nuclei and short
  strings initialize minimum-mode eigenvector following. Fixed exterior
  neighbors enter local searches as exact exchange fields.
- Refine every candidate against the full chain's stationary equations. Check
  its full tangent-space index, including out-of-plane fluctuations. Perturbed
  nonplanar searches also handle saddles outside an invariant endpoint plane.
- Follow both unstable directions by capped, energy-decreasing relaxation.
  Moving, overlapping windows let a domain wall traverse a long chain without
  optimizing thousands of inactive spins on every iteration. Only candidates
  whose two relaxed branches reach the supplied minima are accepted; choose
  the lowest energy of those found.
- Form the exact constrained Hessian as a symmetric block-tridiagonal matrix.
  Compute all eigenvalues with banded LAPACK, or the union of two scalar
  tridiagonal spectra in the invariant-plane case. No dense whole-chain
  Hessian, approximate density of states, eigenvalue clipping, or zero-mode
  removal is used. The reported logarithmic factor excludes exactly the one
  negative saddle eigenvalue, as required by the input contract.

## Validation

The supplied coherent example agrees with the public baseline in barrier and
logarithmic factor to better than `1e-11`. The supplied 2,048-spin example
converges to a connecting saddle with barrier `1.478760115148908 meV`, a maximum
tangent-gradient residual below `2e-14 meV`, and exactly one negative mode.
Its end-to-end execution takes approximately 1.7 seconds in this environment.

The scratch validation programs exercise coherent reversal, boundary
nucleation, soft interior nucleation, and interface depinning, including
nonuniform, nonplanar, and 4,096-spin cases:

```sh
python scratch/validate.py small
python scratch/validate.py long
python scratch/stress.py
```

Small-system spectra are checked against an independently assembled dense
Cartesian constrained Hessian and finite-difference energy curvatures. Basin
connectivity is checked separately. Additional checks cover global rotations,
reversed site order, low bias, near-spinodal fields, stiff exchange, and
out-of-plane saddles. Tested 4,096-spin cases take approximately 2.5–9 seconds;
the measured process peak memory is below 100 MiB. These are local validation
measurements, not guarantees for every possible Hamiltonian.

## Scientific limitations

This is a deterministic, finite multistart search, not a proof of the global
mountain-pass minimum. Unusually complicated disorder, many competing weak
regions, nearly singular modes, or paths involving additional metastable
basins can require more search branches than the time budget permits. The
solver rejects results when it cannot establish a connecting index-one
transition. Block relaxation establishes a downhill connection, not a
physical-time Landau–Lifshitz trajectory. The output is the static harmonic
factor specified in the contract, not a dynamical attempt frequency or rate.
