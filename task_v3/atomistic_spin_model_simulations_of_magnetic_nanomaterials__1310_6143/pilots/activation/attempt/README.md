# Finite-chain transition-state solver

## Run

```sh
python solve.py CASE.json OUTPUT.npz
```

NumPy and SciPy must be importable (use the supplied vendor directory on
`PYTHONPATH` in the pilot environment). The solver needs no other files, no
network access, and no compiled extension of its own. It limits numerical
libraries to one thread. All five required fields are written as numerical
arrays/scalars in a compressed NPZ archive.

## Method

1. Infer a common invariant spin plane from the supplied minima and field,
   and verify that every anisotropy tensor preserves it. When this symmetry
   exists, spin angles give nonsingular, exact coordinates on that plane;
   the algorithm does not assume any particular Cartesian easy axis.
2. Relax three discretized strings joining A and B: collective rotation,
   left-end nucleation, and right-end nucleation. Each string undergoes
   downhill evolution and equal-arclength redistribution. Its highest-energy
   images initialize trust-limited eigenvector-following searches, using
   analytic tridiagonal angular Hessians.
3. Retain stationary points with exactly one negative eigenvalue of the
   **full 2N-dimensional** constrained Hessian, including out-of-plane modes.
   Relax perturbations in both signs of the unstable mode and require that
   they reach the supplied A and B basins. Choose the lowest-energy verified
   transition among the different searches.
4. If the plane reduction is unavailable or yields no verified transition,
   use geodesic strings and eigenvector following on the product of spin
   spheres, with additional perturbed paths if necessary. This fallback
   also checks unstable-mode basin connectivity.
5. Assemble the exact Cartesian Hessian projected into independent
   orthonormal tangent frames, including the spin-constraint multipliers.
   Diagonalize at the supplied A and the converged saddle. The barrier is
   the total forward energy difference. The logarithmic determinant ratio
   includes all minimum modes and every positive saddle mode, without
   clipping, absolute-value substitutions, or zero-mode removal.

## Validation

```sh
python validate.py --rotate --full --perturb /path/to/input/initial_*.json
```

The validation program independently assembles the full Cartesian Hessian
using a different tangent basis. It checks energies, stationarity, inertia,
both spectra, the logarithmic factor, finite-difference curvature, unstable
mode connectivity, and invariance under a rigid three-dimensional rotation.
It also runs the full-sphere fallback independently and constructs perturbed
cases with site-dependent anisotropy rotations and a nonplanar field.

All six supplied cases pass. Original-case maximum spinwise residuals are
below `2e-11` meV. Observed solver times are approximately 0.1–0.3 seconds per
case, excluding interpreter startup, on the supplied environment.
The full-sphere and nonplanar tests also pass, taking less than one second per
search in this environment.

| Supplied case | Forward barrier (meV) | log_omega0 |
|---|---:|---:|
| coherent 00 | 1.405127027253 | 0.636583641642 |
| coherent 01 | 2.345870670099 | 1.444660676397 |
| domain wall 00 | 1.556608381613 | 1.669860803456 |
| domain wall 01 | 1.478760115151 | 1.644208047553 |
| exchange spring 00 | 0.963368255330 | 1.377043727320 |
| exchange spring 01 | 0.912076665151 | 1.347922692781 |

These are computed results, not comparisons against unavailable reference
data.

## Scientific limitations

Multistart string searches provide numerical transition states, not a proof
of the global mountain-pass minimum. The invariant-plane search is efficient
for the supplied hard-axis mechanisms; a more general Hamiltonian could have
a lower nonplanar transition even when a planar index-one saddle exists.
Complicated landscapes with multiple intermediate metastable basins can also
need more paths than the bounded search used here. The output is the
temperature-independent harmonic fluctuation factor in the contract, not a
magnetic dynamical attempt frequency or a finite-temperature anharmonic rate.
