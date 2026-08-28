# Pre-implementation anti-compression commitment

Written before any c04 solver, generator, labels, or evaluator (2026-08-27 local).

The scientific task is **calibrate -> resolve the bath -> choose protection**,
not a supplied-matrix exponential benchmark. Three separately measured abilities
are required:

1. Select white, softened 1/f, or softened 1/f² spectra from noisy finite-band
   single/pair-probe calibration, and estimate the spatial correlation fraction.
2. Reconstruct the Hamiltonian, group equal Bohr frequencies without splitting
   degenerate eigenspaces, and distinguish independent from collective channels.
   A supplied audit bath makes this component independent of calibration errors.
3. Propagate the fitted bath for a finite menu of realizable protection settings,
   comparing both Gauss-law leakage and fidelity to the intended dynamics.
   Select within a quadratic actuator budget, including known actuator crosstalk.

No universal dense numerical kernel, scalar 1/V law, largest-V rule, population-only
master equation, or isolated-transition jump prescription is the task definition.
All scored outputs are invariant under rotations inside exact energy eigenspaces.
The Hilbert dimension is 64; system-size scaling is not the source contribution.

Before participant attempts, freeze nine screening cases (three per family), six
separate challenge cases, and three reserved confirmation cases. The families are
white/coherent-error competition; 1/f/local-to-collective crossover; and 1/f² with
exact degeneracies. Challenge varies physical regimes, not malformed inputs or
floating-point tie traps. Confirmation labels may be computed for author checks
but cases must not be used for participant tuning or released before confirmation.

Only one unlabeled interface example is public. No large labeled development
corpus or parameter-to-answer lookup table is supplied. Case identifiers carry no
model-family label to the participant. Families are evaluator-side metadata.

Scores are smooth error ratios normalized to an actually executed, documented
weak white/local baseline, with positive floors; exact reference has score one.
Report component scores, family means, overall mean, and worst-family mean.
Do not invent measurements, claim official author code, or hide numerical
conventions in the evaluator. Run independent invariant/analytical checks and
physics ablations before declaring the pilot valid. No Codex agents are run here.
