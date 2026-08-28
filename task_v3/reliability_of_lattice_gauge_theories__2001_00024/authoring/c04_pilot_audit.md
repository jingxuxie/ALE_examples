# c04: bounded post-pilot audit

**Conclusion:** one general, contract-faithful solver handles every evaluated
screening/challenge case. No substantive physics/component failure or clerical
failure is demonstrated. This is genuine numerical agreement, not just coarse
score thresholds. No in-contract counterexample is currently justified.

Paths below are relative to
`tasks_v3/reliability_of_lattice_gauge_theories__2001_00024/`.
Only existing artifacts were inspected; no evaluations or agents were rerun.

## Actual agent evidence

These are the initial **ultima-alpha submission** results, not author-reference
self-scores. Main's completed reports and their matching `.log` files are:

- `authoring/runs/c04_colored_noise/screening/screening_evaluation.json:2`
- `authoring/runs/c04_colored_noise/screening/challenge_evaluation.json:2`

| Split | Successful cases | Mean / worst family | All four component means | Worker seconds mean / max |
| --- | ---: | --- | --- | --- |
| Screening | 9/9 | 1.000 / 1.000 | 1.000 each | 1.082 / 1.970 |
| Challenge | 6/6 | 1.000 / 1.000 | 1.000 each | 0.881 / 1.185 |

All three family means are 1.0 in both splits; all `validation_errors` are empty
and all execution `error` fields null. Across the 15 cases, maximum raw errors are
calibration **2.526e-19**, audit **1.571e-27**, dynamics **4.629e-22**, decision
**0**. For audit, the largest value is challenge case `0833ee933dae`, recorded at
`authoring/runs/c04_colored_noise/screening/challenge_evaluation.json:16`.
Scores rounding to 1.0 do not imply bit-identical outputs, but these residuals
are far below the public numerical targets.

`authoring/runs/c04_colored_noise/screening/result.json:34` records 834.768 seconds
for agent completion. The current solver hash matches its recorded submission
hash at `result.json:42`; `result.json:47` records the participant tree unchanged.
Reserved confirmation is not assessed here.

## Why one solver covers the families

- **Inference:** `pilots/c04_colored_noise/attempt/solver.py:33` enumerates all
  three spectral models, fits bounded parameters with analytic Jacobians and
  multiple cutoff starts, and applies the prescribed parameter-count penalty.
  It does not copy the supplied independent audit bath into the calibration fit.
- **Hamiltonian and rates:** `pilots/c04_colored_noise/attempt/solver.py:127`
  constructs the gauge/matter model; `solver.py:166` clusters all energy/gap pairs;
  `solver.py:181` builds separate local/collective species channels. The within-gap
  Gram matrix at `solver.py:204` retains degenerate-transition interference,
  including zero frequency. Row-major vectorization is internally consistent,
  not a mismatch with the reference's column-major implementation.
- **Dynamics and decisions:** `pilots/c04_colored_noise/attempt/solver.py:242`
  propagates the sparse Liouvillian with `expm_multiply` and compares against the
  ideal trajectory. `solver.py:268` includes coherent errors and actuator
  crosstalk; `solver.py:290` evaluates every feasible action and minimizes the
  stated risk rather than always taking maximum protection.

There are no case-ID/family branches or reference-output reads in the submitted
solver. Hard-coded dimension 64 and uniform time sampling are public requirements,
not failures (`pilots/c04_colored_noise/participant/input/protocol.md:89` and
`protocol.md:198`). It is a general **fitter + frequency-resolved generator +
finite-menu optimizer**, not merely a supplied-matrix exponential. Nevertheless,
the entire frozen challenge is solved by that single implementation: the pilot
does not demonstrate a remaining hard family for this agent.

Existing agent-local checks also cover explicit degenerate jumps, invariants,
and fully degenerate raw-channel limits; see
`authoring/runs/c04_colored_noise/screening/agent.log:6123` and
`pilots/c04_colored_noise/attempt/validate.py:114`. These are logged agent checks,
not independently rerun audit tests. No clerical repair or physics fix is indicated.

## Source-grounded counterexample disposition

**No demonstrated in-contract counterexample; no ratchet proposed.** One conditional
coverage question is scientifically motivated: late-time observable drift while
gauge leakage stays small. The main paper distinguishes persistent leakage
suppression from observable deviations around times proportional to V/lambda²
(arXiv:2001.00024, Fig. 3 and the following energy-protection discussion, PDF p. 4).
The follow-up derives early incoherent growth proportional to gamma*t/V^beta
(arXiv:2210.06489, Appendix B, Eqs. B4 and its protected-limit discussion, PDF p. 9).
Together these motivate examining a weak-noise, long-time coherent/incoherent
crossover **if later selected**, not arbitrary parameter edges or size inflation.
These scalings are source-model guides, not guaranteed quantitative laws for this
modified pilot. The submitted solver makes no short-time approximation, so there
is presently no evidence that such a region would defeat it. No cases were made.

Conversely, non-Markovian memory or an alternative nonsecular generator cannot be
silently introduced as a counterexample: the follow-up's Sec. III and Appendix A
state weak-coupling/short-bath-correlation assumptions, while the public contract
explicitly fixes a Markov/secular model (`participant/input/protocol.md:173`, under
the c04 pilot). Changing that model would require a new public contract and
independent validation, not a post-hoc failure label.

Primary sources checked: `https://arxiv.org/pdf/2001.00024` and the **full 12-page**
`https://arxiv.org/pdf/2210.06489`. No official-author-code claim is made.

**Disposition:** retain the perfect actual pilot result as evidence of current
task saturation; defer selection. This audit changes only this note, not the
participant, attempt, reference, evaluator, pools, or the independent c02 work.
