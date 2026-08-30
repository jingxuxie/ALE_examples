# OpenFermion hardness-discovery package

Paper seed: *OpenFermion: The Electronic Structure Package for Quantum Computers*,
arXiv:1710.07629. Three concepts were built from nine privately considered
concepts, using verification modes A, C and D. Generation provenance is in
`private/source_manifest.json` and `private/concept_selection.md`.

## Package boundaries

Only the selected generation's `participant/` directory is participant-visible.
It is read-only. Each fresh attempt starts with a separate empty writable output
directory. Do **not** distribute this entire repository: evaluators, hidden data,
private witnesses, search traces and other submissions are privileged artifacts.
All recorded fresh attempts use the prescribed `run_allowlisted_codex.sh`, model
`ultima-alpha`, and a one-hour development deadline.

Each concept contains `participant/`, `evaluator/`, `attempts/`, `champions/`,
`adversary/` and `status.json`. Ratchets are independent frozen packages under
`generations/generation_N/`; they do not overwrite the initial tournament.
The concept's final status identifies its active participant and evaluator.

## Concepts and evaluation

- `concept_1`: mode A, exact joint orbital/auxiliary-gauge coefficient-cost
  compression. A submission is a directory containing `solver.py`.
- `concept_2`: mode C, native-graph Slater-state circuit witnesses under joint
  gate/depth caps. A submission directory contains `solution.json`.
- `concept_3`: mode D, held-out correlated Hubbard charge and spin-sector gaps.
  A submission is a directory containing `solver.py` and any model/native assets.

From this directory, set `EVALUATOR` to the active `evaluator/evaluate.py` and
`SUBMISSION` to a complete submission or supplied baseline, then run:

```bash
python3 private/affinity.py "$EVALUATOR" "$SUBMISSION" --report report.json
```

The trusted wrapper serializes timed evaluations and fixes one-CPU affinity and
numerical-library thread counts. Concept A and D evaluators sandbox untrusted
submission processes; concept C checks JSON without executing submission code.
Each evaluator reports core score, worst-family score, resource information,
validity, pass/fail and a reason. Targets are frozen before each fresh launch.
For concept C the supplied runnable baseline compiler first writes the artifact
as described in its participant task; the private planted witness is not a
participant asset.

## Evidence and isolation

`attempts/v_N.launch.json` records the runner command/hash, package hashes,
read-only policy and elapsed development time. `v_N.evaluation.json` is the
official report. Circuit cutoff records retain only the last valid artifact
captured before the one-hour deadline. Later ratchets score relocated frozen
submission snapshots. `private/package_audit.py` checks package boundaries,
canary isolation, unchanged frozen inputs and scoring-snapshot hashes.

`concept_2/status.json` records a completed `hard_verified_achievable` result:
neither independent fresh attempt satisfies all four witness conditions, whereas
a private witness does. The other concepts retain the initial solved scores and
their champion-search/ratchet lineage. Consult the final `status.json` and
`FINAL_REPORT.md` for the completed cross-concept decision.

Development CPU and memory descriptions in participant documentation are not
proofs of aggregate kernel accounting. The hard development deadline and
allowlist are enforced by the runner/controller; inference budgets are checked
by the scoring environments. Numerical source validation, malformed-output
tests, isolation probes and adversarial searches are retained with each concept.
