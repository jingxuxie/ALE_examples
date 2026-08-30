# Paper-seeded hardness discovery

Final outcome: **concept 1 is `hard_verified_achievable`**. Concept 2 is solved;
concept 3 is rejected because its fresh miss is marginal. See `FINAL_REPORT.md`
and `FINAL_REPORT.json` for scores, ratchets, search evidence, and solvability.

Three runnable concepts use distinct verification modes:

| Directory | Mode | Mission |
| --- | --- | --- |
| `concept_1` | A — baseline improvement | Branch-correct anisotropic imaginary-axis solutions under a fixed CPU budget |
| `concept_2` | B — counterexample | Matched normal-state kernels with different superconducting transition temperatures |
| `concept_3` | D — hidden prediction | Sheet-resolved finite-resolution spectra from noisy mixed Matsubara probes |

Each `participant/TASK.md` is the participant mission. Only that concept's
`participant/` directory and an initially empty output directory may be exposed
to a fresh participant. Evaluators, hidden data, champions, other attempts,
adversarial searches, source provenance, and this authoring directory are private.
In particular, previous fresh implementations are never part of a later public
baseline. The synthetic models' scientific scope and limitations are explicit
in each participant's mathematical contract.

## Evaluation

Run these commands from this task root. Reports are written to the named paths;
the supplied weak baselines are expected to fail their fixed targets.

```bash
python concept_1/evaluator/evaluate.py \
  --submission concept_1/participant/baseline --report /tmp/eliashberg_solver_baseline.json

python concept_2/participant/baseline/solve.py --output /tmp/matched_kernel_baseline.npz
python concept_2/evaluator/evaluate.py \
  --artifact /tmp/matched_kernel_baseline.npz \
  --output /tmp/matched_kernel_baseline.json \
  --audit-output /tmp/matched_kernel_baseline_audit.json

python concept_3/evaluator/evaluate.py \
  --candidate concept_3/participant/baseline --split hidden \
  --report /tmp/spectral_prediction_baseline.json
```

Replace the baseline directory with a submitted directory containing `solve.py`
for concepts 1 and 3. Concept 2 evaluates a static `witness.npz`; it does not run
participant code. Runtime-qualified program evaluation requires Linux Landlock,
libseccomp, Python, NumPy 1.21.5, and SciPy 1.8. Preserve the complete task-root
layout: the program evaluators use `authoring/sandbox_runner.py`. Hidden labels
and scoring code remain outside the submitted program's filesystem view.

## Evidence and generations

The active task for each concept is its top-level `participant/` and `evaluator/`.
Its `status.json` records the empirical decision, not a guarantee of solvability.
Previous-generation runnable snapshots and selection evidence are under
`adversary/`; archive manifests identify the matching numerical contract.
Do not score an earlier attempt against a newer active generation and report
that number as its original tournament result.

Prelaunch seals describe the at-launch state. Post-tournament `status.json`
records are updated separately; their originals remain in
`authoring/status_archive/` or the generation's activation backup. Participant
assets and scoring data stay fixed. The final report identifies these metadata
transitions rather than rewriting the historical prelaunch seals.

`authoring/runs/concept_N/v_M/` contains launch manifests, the private transcript,
deadline-frozen submission, scorer output, and completion metadata. Live
`attempts/v_M/` directories are not the scoring authority. A misplaced task file
made `concept_1/v_1` administratively noncompetitive; its adjudication is retained
and it is excluded from hardness evidence. All competitive launches use
`ultima-alpha`, independent allowlists, and a one-hour limit.

`authoring/protocol.json` fixes the decision rules. `authoring/concept_selection.json`
records ten considered ideas; exactly three were built. `authoring/sources.md`
records scientific and source-code provenance. `authoring/audit_tournament.py`
checks package completeness and recorded fresh-run isolation/integrity; numerical
and hostile-artifact audits live with the respective evaluators.

The orchestration entry point is
`python authoring/run_tournament.py concept_N v_M`, using the user-supplied
`run_allowlisted_codex.sh` in the repository root. It requires a previously unused
attempt name. `python authoring/score_finished.py` scores newly completed frozen
submissions without giving the participant hidden feedback.
