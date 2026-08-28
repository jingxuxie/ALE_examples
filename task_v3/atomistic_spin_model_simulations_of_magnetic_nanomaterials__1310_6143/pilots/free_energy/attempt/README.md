# Direction-constrained thermal free energy

Run `python solve.py CASE.json OUTPUT.json`. The implementation uses NumPy and
compiles its self-contained C++17 sampler with `g++`. It uses one computational
thread, no network, and no case-specific predictions or stored reference data.
Temporary compilation and sampling files are placed beside the output and
removed on success or failure. The default time budget is 550 seconds, including
startup, with time reserved for statistical postprocessing.

## Ensemble and moves

Spins are represented in a frame whose positive z axis is the requested total
magnetization direction. Write the Hamiltonian as isotropic exchange `H0` plus
all supplied onsite and axial-bond anisotropies `A`.

Each proposal first uses a reversible, rotationally covariant exchange-only
kernel: heat-bath updates, stochastic overrelaxation, or an embedded Wolff
cluster reflection. Its resulting magnetization is then rotated to positive z
by the shortest proper rotation. An ordinary Metropolis decision using the
change in `A` completes the proposal. Rejections are retained in the averages.
The magnetization magnitude is never fixed. Initialization first thermalizes
the exchange reference system; a separate, discarded target-ensemble warmup
is performed at each sampling angle.

This projection is not a Cartesian-delta approximation. To see why, disintegrate
the rotationally invariant exchange measure into its magnetization direction
and the conditional configuration measure. If `R(m)` is the shortest rotation
from the constrained direction `n` to `m`, the projected transition integrates
the exchange transition from `x` to `R(m)y` over solid angle `dm`. Reversibility
and rotational covariance convert this into the reverse transition from `y`
to `R(m)^(-1)x`. The change of variable
`m -> R(m)^(-1)n` preserves solid angle and replaces `R(m)` by its inverse.
Consequently the projected kernel is reversible for the *directional* exchange
measure. Metropolis reweighting by `exp(-A/T)` gives the stated full ensemble,
including the radial `|M|^2` factor implicit in a directional delta.

The independent `pairs` verification kernel instead changes two spins while
preserving the two transverse components of their sum. Its acceptance includes
`(M_new/M_old)^2 * abs(s_compensator,z,old/s_compensator,z,new)`. This explicitly
checks both the directional Jacobian and the projected algorithm.

## Observables and free energy

The microscopic torque is computed from the complete anisotropy Hamiltonian,
including off-diagonal onsite tensors, fourth-order cubic terms, and each
axial bond exactly once. Isotropic exchange cancels from the total torque.

Fifteen interior angular states cover the first quadrant. For diagonal onsite
tensors, each saved configuration supplies its exact second- and fourth-order
rotation-energy coefficients. A symmetry-folded multistate Bennett acceptance
ratio (MBAR) calculation combines the angular ensembles. Reflection-related
orientations are integrated analytically: if their anisotropy energies are
`C(theta) +/- S(theta)`, the effective reduced potential is
`C(theta)/T - log(cosh(S(theta)/T))`. This is an exact reflection average, not an
assumption that the free energy has only a few harmonics.

Free energies are logarithms of reweighted partition-function ratios, and
torques are derivatives of those same partition functions. Thus the reported
free energy is not a mean internal-energy difference, and the default method
has no angular integration-grid truncation. All four stated angular symmetries
are enforced. Eight delete-block-group reweightings estimate statistical errors.

For nondiagonal tensors, or if the multistate equations cannot be solved, the
fallback integrates a statistically selected multi-harmonic fit to measured
torques. Its fit and integral use the same coefficients. The raw angular means
and conservative batch errors are included as diagnostic output keys.

## Validation and diagnostics

`validate.py` checks projected, cluster, and explicit-Jacobian pair sampling
against deterministic two-spin angular quadrature, including cubic and
two-ion anisotropy. It also checks the exact isotropic two-spin directional
mean magnetization, `2/3`, and vanishing torque. `benchmark.py` compares mixing
kernels on a supplied large case; it is not needed by the entry point.
`validate_reweight.py` checks MBAR against analytic Gaussian partition functions
and verifies the torque/free-energy derivative and angular symmetries.
`check_native.cpp` checks the full-tensor microscopic torque and saved rotation
coefficients against finite energy differences; run `validate.py` first to
generate its small input model.

With the supplied numerical runtime on `PYTHONPATH`, the analytic checks can
be reproduced from this directory with:

```sh
export TMPDIR="$PWD"
g++ -O3 -std=c++17 sampler.cpp -o sampler
python validate.py
python validate_reweight.py
g++ -O3 -std=c++17 check_native.cpp -o check_native
./check_native
```

`VALIDATION.md` records the public-case, independent-seed, and resource checks.

Development controls are `SPIN_SECONDS`, `SPIN_NODES`, `SPIN_KERNEL`,
`SPIN_SAVE_BLOCKS`, and `SPIN_NO_MBAR`. They are optional; normal evaluation
needs none. `SPIN_SAVE_BLOCKS=1` retains block data and energy coefficients beside
the output. The supplied numerical dependencies must be on `PYTHONPATH` when
running development checks outside the evaluator.

## Scientific limitations

The Hamiltonian and directional ensemble are sampled without coherent-rotation,
fixed-magnetization, mean-field, or material-calibration assumptions. Finite
sampling and equilibration errors remain. Cluster moves and multiple angular
ensembles reduce, but do not eliminate, metastability or slow mixing. MBAR
requires overlap among sampled ensembles; its reported effective sample counts
describe importance weights, not autocorrelation-corrected independent counts.
Block errors can underestimate exceptionally slow modes and are themselves
noisy. Stronger anisotropy, much larger systems, or sharp angular transitions
can require longer runs and a denser state grid. The torque-fit fallback has
additional angular truncation error. No private-reference accuracy claim is
made.
