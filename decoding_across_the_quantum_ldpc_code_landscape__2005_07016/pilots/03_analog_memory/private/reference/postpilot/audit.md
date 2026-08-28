# Pilot03 post-pilot audit: discard

**Recommendation:** do not retain this candidate among the best two real solution
gaps. The submitted solution generalizes to the original independent challenge
without edits. The strong official reference does not outperform it in any of
the observed logical/history comparisons. No extra regime or final holdout was
generated, and no threshold, distribution, participant, attempt or scorer changed.

## Unchanged original-challenge replay

The complete six-file attempt was copied with preserved mtimes into
`submission_snapshot/`. Every file, including `decoder.so`, matched the original
SHA256 inventory before and after evaluation. The original evaluator ran against
the original challenge manifest through the existing bwrap helper. All files in
the pilot outside the two authorized postpilot directories remained byte-identical;
`before.json` and `after.json` contain the inventories.

| Case | Qubits / rounds | Logical successes, submission / reference | History balanced accuracy, submission / reference | Submission CPU seconds |
|---|---|---|---|---|
| 3D toric L=3 | 81 / 4 | 128/128 / 128/128 | 0.995589439 / 0.993516516 | 3.44 |
| 3D toric L=4 | 192 / 6 | 128/128 / 128/128 | 0.994471061 / 0.992282050 | 18.81 |
| Lifted product, lift=16 | 544 / 3 | 128/128 / 128/128 | 0.999471476 / 0.999434859 | 9.51 |
| Lifted product, lift=16 | 544 / 5 | 128/128 / 128/128 | 0.999785917 / 0.999755144 | 19.03 |

- `mean_core = 1.0010976939025424`; `worst_family = 1.0000337223485225`.
- All 512 shots satisfy history, metacheck and exact-terminal consistency.
- Total CPU: 50.79 seconds; total wall: 64.9484 seconds; peak RSS: 51,492 KiB
  (about 50.3 MiB). Every case is comfortably inside the unchanged 120 CPU
  seconds / 1536 MiB limit; the maximum case uses 19.03 CPU seconds.
- Both submission and reference genuinely achieve 128/128 logical successes in
  each case, with the same approximately 0.9709 Wilson lower endpoint. This is
  raw-reference-quality evidence, not an inference from normalized score one.
- History differences are observed point estimates, not a claimed significance
  result. The submission's history estimate is higher in all four cases. No
  meaningful observed reference advantage was established.
- The source-native reference decoder times sum to about 1.94 CPU seconds, while
  submission CPU is end-to-end. The reference is faster, but the present task
  grants 120 CPU seconds per case. Tightening that limit would be a new benchmark,
  not a valid rescue of this one.

Exact values, existing noise configurations, resource accounting and raw weak /
reference metrics are in `original_challenge_summary.json`. The untouched
scorer's complete output is `original_challenge_report.json`.

## Actual algorithm, not a presumed weak solver

Source locations below are relative to the pilot root; identical copies are in
`submission_snapshot/`.

- `attempt/solve.py:115`: computes the calibrated Gaussian log-likelihood ratio
  using both means and the supplied, check/round-dependent variance. It is not
  sign-only decoding, a fixed global sigma, or a learned calibration table.
- `attempt/solve.py:16`: constructs a generic binary space-time model from the
  supplied matrices. Every round has separate data-increment variables; every
  nonterminal round has readout-flip variables. The final hard syndrome is replaced
  by the exact terminal value at `attempt/solve.py:117`, so the last analog sample
  is correctly redundant and no finite-prior approximation to the boundary is used.
- `attempt/solve.py:34` and `attempt/solve.py:120`: append the supplied metacheck
  equations and their right-hand sides. These relations are not ignored.
- `attempt/solve.py:47`: enumerates a cancelling-error move for **every pair of
  rounds and every qubit**, including the intervening syndrome-flip support.
  Stabilizer moves are also included. Temporal cancellation is explicitly modeled,
  not an untested blind spot inferred from a generic decoder name.
- `attempt/decoder.cpp:260`: uses a CPU-bounded, family-agnostic BP ensemble,
  ordered-statistics repair, and likelihood-improving local moves. This is stronger
  than a bare single-run BP+OSD implementation; the audit does not claim otherwise.
- `attempt/solve.py:146` and `attempt/decoder.cpp:308`: class-conditional Gibbs /
  Rao-Blackwellized history refinement uses the known parity prevalence to target
  balanced accuracy. It operates through constraint-preserving moves and does not
  change the selected final recovery during the output-history decision step.
- `attempt/solve.py:159`: outputs are obtained from cumulative data increments,
  followed by matrix multiplication and explicit consistency checks. No case-ID
  lookup, code-family-specific solution, training labels, or private-file access
  was found in the submitted inference path.

## Universal reduction and why zero extra regimes

Writing `b_t` for the hard readout, `e_t` for a fresh data increment, and `q_t`
for a readout flip, the common augmented equations are
`H e_t XOR q_t XOR q_(t-1) = b_t XOR b_(t-1)`, with exact initial/final boundary
conditions. Metachecks add `M q_t = M b_t`. Known Bernoulli priors supply data
weights, and the absolute Gaussian log-likelihood ratios supply readout weights.
Both metrics are then derived from the same inferred space-time state.

This is a reusable reduction for the declared model, rather than independent
code-family-specific scientific solutions. Metacheck consistency is algebraically
implied once a physical history is reconstructed; redundant metacheck equations
can additionally help BP. Temporal pair moves preserve the final state and every
augmented equation because `M H = 0`. The submission implements these mechanisms
directly and adds generic posterior refinement for the history loss.

**Universal reduction is not universal correctness:** BP/OSD and finite Gibbs
sampling remain heuristic, and extreme noise could cause errors. But this bounded
audit found no absent Gaussian or temporal-cancellation mechanism warranting a
new regime. Raising noise blindly would probe generic decoder strength/runtime;
it would not establish a separate missed capability, and reference outperformance
must not be presumed. Therefore **zero** of the allowed two additional regimes
were used. No distribution change, tighter resource gate, new holdout, ratchet,
or fresh model call was made. Record this as a legitimate universal-augmentation
shortcut and discard the candidate rather than force hardness.
