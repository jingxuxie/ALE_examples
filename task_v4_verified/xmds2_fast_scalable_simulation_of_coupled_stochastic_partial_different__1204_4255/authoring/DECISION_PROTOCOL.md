# Empirical decision protocol

The discovery considers ten paper-seeded ideas and builds exactly three concepts,
using modes A, B and C. `concept_selection.json` records the selection. Each
tested generation receives two independent `ultima-alpha` sessions with high
reasoning effort, a 3600-second wall deadline and a short process-teardown grace.
The supplied runner grants only read-only participant assets and an initially
empty writable attempt directory. Generation workers and numerical searches are
not fresh-agent attempts. No more than three total tested generations are allowed
for a concept, hence at most two champion-to-challenger ratchets here.

## Fixed criteria

- A: at least 20% geometric-mean cost reduction and at least 8% reduction in every
  family, with exact plan validity and the stated 120-second/one-CPU/1-GiB limits.
  These criteria, the hidden traces and their baseline costs predate both trials.
- B: every specified perturbation must satisfy the fixed admissibility,
  convergence-indicator, conservation, tail-mass, density-gap and independent
  reference checks. Later generations explicitly publish stronger perturbation
  coverage; they do not silently change the numerical thresholds.
- C: audited core fidelity at least .990, worst-family mean at least .985 and
  worst-case fidelity at least .980, with all control and numerical audits.
  Ratchets retain the physical model, full uncertainty box, control limits and
  fidelity thresholds, and add reference-validated coverage inside that box.

The task protocols, freeze manifests, publication records and run-start hashes
are the evidence for criteria fixed before each fresh generation. This document
summarizes that evidence; it does not introduce a new target.

## Avoiding false hardness

An agent reaching the time limit is not automatically a failure. Its saved final
artifact is evaluated if present at the cutoff. In particular, both generation-1
control attempts reached the limit but their canonical `control.json` artifacts
passed. They are recorded as solved and receive a ratchet.

The first organizer dispatch for B incorrectly looked for `witness.json` rather
than the submitted `submission.json`. The missing-file reports are preserved as
dispatcher errors, superseded by the correct evaluations, and never counted as
failed attempts. The generation-one A resource/parser amendment is documented
separately in `EVALUATOR_AMENDMENTS.md`; it changes neither traces nor cost targets.

Resource-calibration timeouts during evaluator development are not scientific
counterexamples or fresh-agent failures. Unresolved numerical references are not
accepted as proof of a violated scientific claim. Ratchet evidence distinguishes
coarse search leads, independently checked failures and numerical audit failures.
The outer orchestration watchdog allows up to 1800 seconds for C's trusted
artifact-only numerical grading, independently of the one-hour development
deadline. B retains its generation-specific internal CPU/wall limits, with an
outer watchdog at least 180 seconds longer. These watchdogs do not extend a
participant planner's execution budget or change any quality threshold.

## Final labels

An evaluated fresh submission meeting its generation's target makes that
generation solved. A failed final generation with a trustworthy evaluator but no
known passing artifact is `hard_open_candidate`: feasibility is unknown, not
disproved. `hard_verified_achievable` additionally requires a passing privileged
artifact under the same final evaluator. A per-case oracle assembled from saved
plans is not a runtime-compliant proof for A. Only the final tested generation
determines a concept's retained status; an earlier champion's success does not
demonstrate feasibility after a ratchet.
