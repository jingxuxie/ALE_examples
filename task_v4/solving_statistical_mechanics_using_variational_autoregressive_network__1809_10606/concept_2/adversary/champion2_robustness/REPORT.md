# Completed Generation 2 champion: exploration-floor audit

Generation 2 is solved and its champion remains valid under its original contract.
All eight completed submission files were copied byte-for-byte into
`champions/generation_2`, with official score and hash provenance. No ongoing
fresh attempt was read. The stale private search was interrupted and preserved;
its failure is not evidence against the successful fresh champion.

The exact champion has beta=1.4297178597693243, 106 nonzero triangular weights,
variance 0.00844491733 and gradient infinity 0.000812040078. The audit crosschecks
the archived official score and uses all spin states for retained reports. The
optimizer uses the exact spin-flip quotient, never Monte Carlo.

## Scalar controls and coupled optimization

Scaling rows to each floor gives these minimum variances over continuous beta
in [1,3]: 0.003 -> 0.03050962; 0.01 -> 0.15669736; 0.03 -> 1.37530022;
0.05 -> 3.31068508. These are clipped minima of the exact quadratic
Var(beta E + log q), not grid estimates. Other gates can fail at those minima.

At floor 0.003, full coupled reoptimization quickly restores every original
physical gate: variance 0.03070464, gradient 0.00237215, target sector mass
0.44689513 and proposal mass 0.0009998923. Thus 0.003 is not a useful next
obstruction to this actual champion.

At floor 0.01, three bounded controls optimize the full triangular network and
continuous beta with original entropy, KL, energy and sector constraints:
variance minimization from the scalar-beta optimum, a gradient-penalized run
from the original beta, and continuation from the repaired 0.003 witness.
Two runs reported local SLSQP convergence; the gradient-penalized run reached
its local time bound. None produced a passing witness. The best retained
gate-score candidate has variance 0.13945199, gradient 0.00729245, energy error
per spin 0.00615297, target sector mass 0.43467078 and proposal mass 0.0009998965.
It fails variance and gradient, NOT the sector gate. Scores are best gate-score
iterates; they must not be described as certified global minima or necessarily
the optimizer's terminal minimum-variance iterate. Higher floors were also
tested; no passing candidate was found in this bounded audit.

The five-coordinate finite-difference check covers the beta derivative and the
optional exact Hessian-vector gradient penalty. See `gradient_checks.json`.
Total computation was about 123 seconds using at most four CPU cores.

## Scientific interpretation

A 0.01 local exploration floor is a natural stronger deployment condition,
implemented solely by row L1 <= ln(99). It does not imply 0.01 probability for
an arbitrary many-spin sector. Keep all seven physical gates, beta interval,
binary couplings, architecture and witness freedom unchanged. No degeneracy,
entropy, correlation or narrow-beta exclusion is justified by this audit.

The observed local failures motivate a new test, not an impossibility theorem,
proof of hardness, or claim that the original champion was invalid. Attainability
of the strengthened mission is UNKNOWN. A newly built generation is
`built_not_tested`; empirical hardness requires its own fresh attempt.

## Evidence

- `original_crosscheck.json`: actual champion versus original official metrics.
- `scalar_floor_profiles.json`: all four floors and continuous-beta quadratics.
- `optimization_0/`: passing 0.003-floor repair.
- `optimization_4/`: best retained 0.01-floor coupled candidate.
- `optimization_summary.json`, `summary.json`: all local outcomes and timings.
- `audit.py`: reproducible standalone audit orchestration and exact optimizer.

No previous participant, evaluator, target, or status was changed.
