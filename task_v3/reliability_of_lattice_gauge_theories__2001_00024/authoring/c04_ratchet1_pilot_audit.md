# c04 ratchet1 final pilot audit: reject as solved

**Disposition: reject c04 as solved, per the precommitted stopping rule.** The
second fresh agent solves all six screening and all three reserved confirmation
cases. Do not increase T, introduce arbitrary dimensions, or prepare ratchet2.
This bounded audit only reads the completed solver/reports and verifies hashes;
it performs no reevaluation, new probe, model call, or change to frozen artifacts.

## Exact evidence and integrity

- Run: `authoring/runs/c04_colored_noise/ratchet1/result.json`. Exit code 0,
  no timeout, elapsed authoring time 724.7085461616516 seconds. This is distinct
  from the sub-three-second per-case numerical worker times below.
- Scores: `authoring/runs/c04_colored_noise/ratchet1/screening_evaluation.json`
  and `authoring/runs/c04_colored_noise/ratchet1/confirmation_evaluation.json`.
  Both mean core, worst family, aggregate, every family, every component and
  every case report 1.0; all nine executions are ok, with no validation errors,
  timeouts, execution errors or stderr.
- Read-only verification of all **44** entries in
  `pilots/c04_colored_noise/ratchet1/private/freeze.json`: zero mismatches.
  Manifest SHA256 remains
  `fc8749db8e32ce0bbb9db6118923cdd123af9758e45c893236f618a19e4abb9e`.
  All four participant-file hashes agree before/after the run and with current
  files. Current submitted solver SHA256 matches the completion record:
  `f36fa9f5fe2e0799ff45aa2fdf26b3cd0b72e56d714992d745c2e05760bd7509`.

## Generic specialist mechanism and completeness

The self-contained 376-line submission is
`pilots/c04_colored_noise/ratchet1/attempt/solver.py`:

- `:23` fits beta=0/1/2 using bounded weighted least squares, analytic Jacobians,
  multistart colored fits and the specified BIC penalties. Finite-band filters,
  calibration uncertainty, floor/cutoff and spatial eta are inferred from inputs.
- `:124` constructs the full public dimension-64 Hamiltonian, charges and
  observables from the supplied parameters/initial state. `:169` clusters energies
  at 1e-9 and frequency gaps at 1e-8. `:187` builds distinct matter/link local and
  collective channels, coherently retains equal-frequency transition cross terms
  via channel Gram matrices, and constructs gain/loss and three activity bands.
  `:243` computes the independent supplied-bath full-matrix audit, not a derivative
  inferred from the fitted bath or a scalar activity substitute.
- `:258` finds connected dissipator blocks, analytically evolves singletons and
  removes each block's mean coherent frequency. Near-constant-frequency Hermitian
  blocks use `eigh`; otherwise `:290` retains the centered coherent diagonal and
  uses general `eig` plus a linear solve. This handles clustered noncommuting
  blocks instead of blindly assuming exact commutation. Spectral exponentials
  evaluate the requested times directly, avoiding full oscillatory Liouvillian
  time stepping and its late-time runtime growth.
- `:305` evaluates every feasible action under the full protected Hamiltonian,
  including actuator detuning, computes all observable curves and fidelity to
  H0 dynamics, integrates the prescribed risk, and selects the minimum. Caches
  at `:301`/`:312` use physical strength/coefficient tuples, not case identity.

The reviewed runtime imports only json, sys, NumPy and SciPy. It contains no
case_id lookups, seed/answer tables, private paths, filesystem/network calls,
dynamic imports or external reference imports. Action IDs only label outputs and
the selected action. Its only explicit I/O is JSON stdin/stdout (`:374`). Fixed
dimension 64 and three sites are the public contract, not hidden-case detection.
Static inspection plus existing isolated reports supports a genuine complete
input-driven solution, not answer retrieval. This is not an audit of unreviewed
authoring logs or a proof for every possible ill-conditioned numerical system.

## Numerical and resource evidence

| Split | Maximum calibration raw error | Maximum audit raw error | Maximum dynamics raw error | Decision regret |
| --- | ---: | ---: | ---: | ---: |
| Screening (6) | 3.456694384016698e-19 | 1.0146571992781016e-26 | 2.0798086396943282e-22 | 0 on all |
| Confirmation (3) | 1.1033245786806774e-19 | 1.0715606982919878e-26 | 2.3081216059771216e-22 | 0 on all |

These are the evaluator's defined raw errors, not absolute state-entry errors.
Printed scores of 1.0 coexist with tiny nonzero errors through floating-point
rounding of the continuous score; they do not imply symbolic equality. Small
channel/gain/initial-block truncations and a near-commuting branch are visible in
the code, but no substantive physics, schema or component failure is observed.

| Split | Worker wall seconds | Parent wall seconds | CPU seconds | Peak RSS KiB |
| --- | ---: | ---: | ---: | ---: |
| Screening | 0.633933--0.885481 | 0.899412--1.157264 | 0.655818--0.906139 | 75,592 |
| Confirmation | 0.676551--2.555925 | 0.909953--2.846465 | 0.698632--0.876545 | 77,472 |

Reports record strict 60-second worker wall / 61--62-second CPU limits, 30-second
startup grace, 90-second parent watchdog and 6 GiB memory. The maximum worker
wall case is confirmation `4b4c0153be25` (2.555925 s, CPU 0.876545 s); no claim
about the unmeasured reason for that wall/CPU difference is needed.

The source-motivated late-time lead defeated the initial generic full-exponential
implementation, but not this generic secular specialist. Independent inference,
degenerate/spatial generator correctness and late-time decision making are all
solved on both frozen splits. The promised rejection condition is therefore met;
there is no justified further tightening or counterexample search in this pilot.
