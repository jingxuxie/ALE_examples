# Generation four staging readiness

This is the final mode-B ratchet, count three. Install only this packet's
`participant/` and `evaluator/` when ready; the active generation-three packet,
its snapshots, champions, and attempt scores have not been edited. Expose only
`participant/` to a fresh solver. No fresh agents are launched by this worker.

## Frozen target

Keep every original physical gate, the population target 0.02, DAD ceiling 0.001,
and Frobenius radius 0.001. Preserve all 241 coordinate points, then append both
signs of the normalized base signed CCSD-minus-FCI energy-error gradient in the
same 120 orthonormal pair coordinates. The derivative includes the one-body
counterterm. At gradient norm at most 1e-12 use the first diagonal coordinate.
All 243 labeled points require actual neighboring roots and full independent
65-point path certificates; no derivative proxy or continuum-ball claim applies.
Artifacts remain the original four-key JSON. The trusted timeout remains 900 s.

## Calibration and feasibility

The completed first generation-three champion passes all 512 valid isotropic
probes but fails both adaptive energy checks: 0.0003411934157 and 0.0003352809918.
The completed second champion passes all 256 valid isotropic probes but fails
both adaptive energy checks at about 0.000234; its DAD also exceeds 0.0021.
Both fail the staged independent evaluator on precisely these valid new points.
There were no out-of-domain probes in these audits.

**Achievability remains unverified: hard_open_candidate, not demonstrated hardness
or proven feasibility.** Private stationary-CC optimization has not produced a
passing 243-point witness. `authoring/obstruction_audit.json` explicitly tests the
proposed purely density-versus-gradient obstruction: a Hermitian fixed-particle
linear response can have occupation violation 0.02 with zero measured gradient,
because the fixed-Fock derivatives are Brillouin-silent. This is a relaxation,
**not** a stationary CCSD witness. It rules out that simple kinematic argument;
stronger restrictions from full CC stationarity and the path remain unresolved.
Neither an impossibility proof nor an achievability guarantee is asserted.

## Audits and isolation

`authoring/oracle_audit.json` checks two-electron CCSD=FCI, lambda derivatives,
HF Hessians, nilpotent exponentials, and exact density positivity.
`authoring/packet_audit.json` checks public/independent response agreement,
all 120 finite-difference coordinates, the unchanged coordinate subset, radius,
fallback, strict parser, symlinks, malformed artifacts, and historical hashes.
`authoring/zero_staged_evaluation.json` records complete 243-path coverage on the
physical zero-interaction example, which correctly earns no witness pass.
`authoring/baseline/submission.search.json` records the unchanged 1,000-trial
public random search. Private calibration artifacts are confined to `authoring/`.

`freeze.json` and `evaluator_freeze.json` pin the exposed and trusted packets;
`status.json` records the readiness decision. Private feasibility searches may
continue after freezing without modifying either pinned directory or its rules.
