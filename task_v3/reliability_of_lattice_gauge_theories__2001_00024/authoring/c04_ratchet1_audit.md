# c04 ratchet1 readiness audit

Ready for the planned single fresh one-hour attempt; none has been launched here.
Stage root: `pilots/c04_colored_noise/ratchet1/` (paths below are relative to the
task root unless explicitly stage-relative). Original pilot, initial attempt and
long-time probe are preserved; 111 original/probe file hashes compare unchanged.

## Scope and public completeness

- Public release is only stage `participant/TASK.md`, `input/protocol.md`, one
  unlabeled `input/example_case.json`, and `workspace/solver.py` starter stub.
  TASK still requires root `attempt/solver.py`; attempt is strictly empty.
- Six fresh screening cases across white/coherent, correlated 1/f, and exact
  degeneracy/1/f² families; three separately reserved confirmation seeds. No old
  probe case or labeled public development set; no additional challenge split.
- Dimension 64 is unchanged. Explicit positive-time grid endpoint range is
  8000--20000 (private endpoints 9000--20000), seven uniform samples including zero.
  Independent noisy bath inference, supplied-bath generator audit, and late-time
  dynamics/finite-budget choice all remain scored. No initial complete solver,
  propagation tutorial or paper reference is published to participants.
- `private/evaluator.py` resolves `RATCHET.parents[2]` to the actual task root and
  calls only common `run_solver(..., timeout=60, memory_gib=6, startup_grace=30)`.
  It supports `--participant`; submission is never imported by evaluator main.
  No shared helper was changed. Strict worker wall/CPU limits are 60/61--62 s.

## Actual isolated evidence

| Implementation/split | Mean core | Worst family | Aggregate | Worker range (s) |
| --- | ---: | ---: | ---: | ---: |
| Reference/screening | 1.000000 | 1.000000 | 1.000000 | 1.105--3.581 |
| Reference/confirmation | 1.000000 | 1.000000 | 1.000000 | 0.991--2.002 |
| Weak/screening | 0.629680 | 0.575000 | 0.613276 | 1.184--3.261 |
| Weak/confirmation | 0.643503 | 0.500000 | 0.600452 | 0.902--2.419 |

All 18 executions succeeded; all nine reference case/component scores are 1.0.
Exact evidence: stage `private/validation/reference_screening.json`,
`reference_confirmation.json`, `weak_screening.json`, `weak_confirmation.json`.
Reference CPU range is 1.055--3.607 s; peak RSS 90,860 KiB. Variable namespace
startup reached parent wall 23.651 s (reference), 24.677 s (weak), not worker
timeouts. Reports record common API/worker hashes and affinity.

The fixed anchor is deliberately stronger than the old baseline: median white
spectrum, eta=0, local fully secular dynamics under the correct Hs; constant
supplied S(1) audit; maximum-cost selection. Its actual errors are frozen per case
in `private/reference/outputs/{screening,confirmation}/*.json`. Public protocol
and pre-build `ANTI_COMPRESSION.md` disclose the change. Original scoring source
is byte-identical: weights .25/.30/.30/.15, floors .01/.01/.0001/.002, smooth
1/(1+error/anchor), aggregate .7 mean + .3 worst. No threshold was tightened.
Weak screening component means are calibration .500000, audit .559715, dynamics
.664218, decision .916667; confirmation .500000/.655899/.655778/.833333.

## Scientific checks and limitations

Stage `private/reference/precompute.py` and
`private/validation/scientific_checks.json` independently compare centered dense
block exponentials with dissipator-eigh/commuting evolution, with controlled
product subdivision for finite clustering. Max observable discrepancy is
2.037e-13; full-density entry discrepancy 4.580e-13. Six short-time comparisons
against the original full-Liouvillian engine have maximum error 5.940e-15.
No dissipator entries are discarded; largest block is 240, not dimension
reduction of the physical Hilbert space. Across both algorithms: trace defect
<=2.665e-15, state Hermiticity <=4.463e-13, minimum density eigenvalue >=-7.344e-15.
Audit rotations within eigenspaces agree to 1.021e-16; brown audit degeneracy is
six. Generator trace/unital residuals are <=1.617e-16; H0 Gauss commutators and
initial-sector residuals are zero.

One reserved signed action legitimately has near-degenerate grouped frequencies:
||[D,C]||F=8.124e-15 but T²||[D,C]||F/2=9.758e-7. We retained the seed, public
grouping and exact centered target; controlled subdivision fixes only the
independent commuting check (refined aggregate indicator <=6.044e-10). The case
was not discarded and the numerical/scoring tolerances were not relaxed.

Closed-system final fidelity is 0.117--0.635 at strongest feasible protection,
demonstrating nontrivial coherent drift. Optimal actions span flat-high, flat-low
and graded-high; the weak maximum-cost rule nevertheless often selects correctly.
The public discrete trapezoidal objective is not a resolved continuous-time
average. This remains an explicit weak-coupling Markov/secular effective model,
not exact non-Markovian 1/f simulation. Source basis and author extensions are in
stage `PROVENANCE.md`; private code is not official paper-author code.

## Freeze and launch boundary

Stage `README.md` gives ready paths and exact reproduction commands; stage
`private/freeze.json` fixes public/private hashes, this audit hash, cases and
weights. `private/original_integrity.json` records preservation. The original
generic full-exponential solver was defeated by the earlier fair long-time probe,
not rerun or modified here. That is a runtime-mechanism result, not proof against
a specialist. If this second fresh agent solves screening and confirmation,
reject c04 rather than invent another tighter ratchet.
