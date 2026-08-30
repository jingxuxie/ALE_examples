# Bounded competing-locality search

This private search owns only this directory. The original participant, evaluator,
champion, generator, and portfolio optimizer are unchanged. It creates 24 cases
with 10–16 orbitals and 8–14 factors, using two independently seeded instances of
the trusted original localized PSD charge generator in independent orbital bases.
The observed factors mix the combined roots orthogonally. The three physical
strata vary relative strengths, near-block auxiliary presentation, and positive
diffuse charge components. These cases extend the original single-localizing-basis
distribution; numerical contract compliance does not make them original tests.

`search.py all --seconds 4` generates cases and provenance, validates three planted
starts, runs the trusted two-gauge portfolio, then evaluates the frozen champion
in two serialized 12-case batches using `capture_evaluate.py` through the required
task-level `private/affinity.py` on CPU 188. Champion code is never imported into
this process. All measured and private values use `evaluator.validate_solution`.

Seeds, independent prospective public/hidden assignments, PSD/symmetry checks,
auxiliary tensor-invariance checks, starting witnesses, optimized witnesses,
per-start records, sandbox reports, and responses are retained locally. The gap
is `1 - private_cost / champion_cost`; failures never count. Candidate artifacts
are private recommendations, not a new participant generation or fresh launch.
Private optimization time is not evidence of an unprivileged runtime-valid solver.

`audit.py prepare` verifies that each unmixed charge family prefers its own
planted basis and assigns dimension-balanced independent prospective splits.
`audit.py refine --seconds 150` spends a bounded extra budget on six candidates,
using only validated JSON witnesses, never imported champion code. Run refinement
through the affinity wrapper to hold the global evaluation mutex.
`audit.py repeat` preserves initial sandbox outputs and repeats both full batches
through the new mutex; do not wrap this parent itself, because its children acquire
the lock. `audit.py finish` checks frozen-source hashes and annotates any qualifying
gaps with gauge-crossover and sampled-local-rotation evidence. Run finish through
the wrapper as well. `report.json` is authoritative after refinement;
`private_score.json` records only the initial private-optimization pass.
