# Screening and grading audit

The fresh ultima-alpha session completed normally in 2020.162851613015 seconds.
It received no evaluator feedback. It left all participant files unchanged.
The exact launcher command and isolated-session ID are retained in launch.json
and transcript.txt. The paper, historical source, reference and hidden labels
were outside its allowlist. No second agent or resumed session was used.

Initial held-out core score: 0.9999864155670366. All six family scores exceed
0.99997. The full suite used 5.315789072948974 solver wall seconds and no case
timed out. Its maximum full-state/channel error is 2.660642323693621e-10. This already
requires rejection under the predeclared >=0.90 rule.

The first evidence check passed 359 of 360 checks. The one failure was a grader
compatibility bug: it assumed every scaling row used configuration 'production'
and an original public manifest. The task permits additional meaningful scaling
experiments. The submission supplied dense/structured/basis-rotated resource
experiments with per-run input.json/input.npz/options.json, and correctly used
their configuration labels as directories. The grader now honors each recorded
configuration and loads the saved input arrays when present. This is an evidence
grader fix, not a task redesign or hidden-test change. The corrected evidence
check passes all 426 checks after regeneration (47.182409110013396 seconds).
No accuracy thresholds, hidden cases, family definitions,
resource envelope, reference arrays, or submitted files are changed.

The participant observed that pytest was unavailable in its isolated interpreter,
despite being importable in the parent's environment. It ran the supplied tiny
checks with unittest and added 18 further tests. This did not cause an attempt
failure, consume the time limit, or affect the scientific score; it provides no
evidence of hardness. No missing-dependency failure is counted as a hard attempt.

## Decision rationale

The agent derived conventional Redfield and Floquet generators, corrected
collapse-amplitude and vectorization conventions, used sparse/block propagation,
and tested analytic limits, degeneracies, branch invariance, complex basis
covariance, harmonic refinement and dimension-112 resource behavior. It produced
an actual run/inspect/revise/rerun cycle, not merely a formatted answer. Even this
connected workflow is within the frontier agent's ordinary scientific-software
capabilities. Multistage packaging did not make it frontier-hard.

Reject concept 1; do not add harder rows, tighter tolerances or edge cases.
No fundamental redesign is performed. The four alternative preflight concepts
were already rejected for credible standard-algorithm shortcuts or lack of real
paper-central artifacts. They are not relabeled and built solely to exhaust the
concept budget. No paper-derived frontier-hard task is retained.
