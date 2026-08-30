# Archipelago hardness-discovery package

The participant missions are in `concept_1/participant/TASK.md`,
`concept_2/participant/TASK.md`, and `concept_3/participant/TASK.md`.
These are explicitly reduced numerical models seeded by arXiv:1504.07997,
not certified solutions of the full three-dimensional conformal bootstrap.
Only a concept's `participant/` directory belongs in the solving allowlist.
The rest of this package contains privileged generation and evaluation evidence.

## Environment and evaluation

The recorded environment is Linux with Python 3.10.12, NumPy 1.21.5,
SciPy 1.8.0, and mpmath 1.3.0. Run the following from this directory.
Replace the submission paths as needed; leave the hidden evaluator assets intact.

```sh
python concept_1/evaluator/evaluate.py \
  --submission concept_1/attempts/v_1.frozen \
  --report concept_1/evaluator/hidden/reproduced.json

python concept_2/evaluator/evaluate.py \
  concept_2/attempts/v_3.frozen \
  --output concept_2/attempts/reproduced.json

OPENBLAS_NUM_THREADS=1 python concept_3/evaluator/evaluate.py \
  --submission concept_3/attempts/v_1.frozen \
  --report concept_3/attempts/reproduced.json \
  --split tournament-v1 --per-family 8 \
  --scratch concept_3/attempts/reproduction_scratch
```

The executable evaluators use `authoring/sandbox.py`, which requires Linux
Landlock and seccomp and fails closed when isolation is unavailable.
Concept 2 verifies static JSON certificates without executing submitted code.
Never use the active-design evaluator's trusted-only unsandboxed option on an
untrusted submission. Baseline commands and protocols are documented inside
each participant package. The latest witness baseline is the generalized
previous-generation champion; archived generations preserve earlier baselines.

## Evidence

`authoring/discovery.md` records the ten considered concepts, and
`authoring/sources.json` records the paper and follow-up sources.
`attempts/*.metadata.json` records the model, one-hour limit, isolation, timings,
and frozen input/output hashes for every fresh trial. The original
`run_allowlisted_codex.sh` is invoked unchanged, using clean runtime homes and
the private-root isolation launcher documented under `authoring/`.
`champions/` preserves successful submissions; `adversary/` records private
searches, independently checked certificates, controls, and generation history.

`python authoring/audit.py` verifies the package and trial invariants.
The final decision and measured scores are recorded in `REPORT.md`,
`report.json`, `status.json`, and the individual concept status files.
The evidence supports an empirical, model-and-budget-specific decision,
not an intrinsic complexity claim.
