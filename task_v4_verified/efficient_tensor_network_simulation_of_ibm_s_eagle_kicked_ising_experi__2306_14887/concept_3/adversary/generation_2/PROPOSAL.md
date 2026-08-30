# Proposed matching-dependent ratchet: HOLD

This is a private, unfrozen design review, not a task or evaluator update.

## Candidate physical change

Retain the 12-cycle, 24 alternating matching layers, two RX groups, original calibration ranges, bounded pulses, and GHZ fidelity target 0.95. Replace the single static 12-site RZ-angle vector with two independently bounded vectors, one per matching. Every component remains within +/-0.01 radians/site/layer. The appropriate RZ vector follows that layer's RX gates, including the final layer; the equal-vector subcase preserves every old scenario. Both vectors remain fixed throughout an experimental run.

## Decision gate

The archived v2 champion passes all independently tested cases in this enlarged model. No admissible fidelity-below-0.95 counterexample has been found. Therefore this extension is physically interpretable but does not currently separate the existing champion. Do not spend the final generation on a finite suite that this champion already passes, and do not increase the threshold or angle bound just to force a failure.

If a genuinely new failure is subsequently found, preserve its exact two vectors and all calibration coordinates, confirm it using independent full-state dynamics, and distinguish uniform temporal, structured spatial, and local matching-dependent failures. A prospective suite should retain all old cases and add predeclared examples from each genuinely failing family plus seeded held-out cases. Freeze the suite before a fresh attempt. Apply global-X parity assertions only where both vectors vanish.

## Feasibility and privacy

Current finite-test feasibility is witnessed by the unchanged champion, not UNKNOWN. Whole-box robustness remains unproved. The bounded branch and continuous-control comparisons are recorded separately and must not be represented as impossibility results or prescribed participant algorithms. All previous fresh sources, pulses, and private variants stay private; the participant must keep only the original weak baseline.

No alternative extension is authorized or frozen by this document. Additional physical changes require a separate scientifically justified model and measured champion failure, rather than an arbitrary numerical target change. All participant, evaluator, status, freeze, original submissions, and logs are left unchanged.
