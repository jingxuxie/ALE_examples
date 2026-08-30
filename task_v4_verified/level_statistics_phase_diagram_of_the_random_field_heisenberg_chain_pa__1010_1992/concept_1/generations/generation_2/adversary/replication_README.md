# Private generation-two champion replication

This bank is private sidecar evidence for existing Concept 1, generation
2, ratchet 1. It is not a new concept, changed task, or threshold update.
No live submission is inspected or scored while constructing the bank.

From the paper task root, build or resume:

`PYTHONDONTWRITEBYTECODE=1 python authoring/build_prediction_replication.py --workers 16`

The builder prefers CPUs 4-19, avoids inference CPUs 0-3, and uses one
BLAS thread per worker. It generates 640 new exact L14 outcomes from
the unchanged public sampling law. Each family has 160 cases in total.
Two independently seeded, stratified batches each contain 320 cases,
80 per family. A separate ordering seed globally shuffles the records
before neutral IDs are assigned. Both batches are disjoint from all
generation-two public and hidden field vectors, including translation,
reflection, global spin reversal, and uniform-field-shift equivalence.

Artifacts have the `replication_` prefix:

- `replication_seed.json`: independent seeds and source/exclusion hashes.
- `replication_plan.json`: private planned fields, neutral IDs, batch membership.
- `replication_checkpoint.jsonl`: resumable exact-simulation results.
- `replication_bank.jsonl`: completed immutable private outcomes.
- `replication_manifest.json`: completed-bank hash, counts, checks and provenance.
- `replication_checks.json`: final read-only verification report, when ready.

A nonblocking file lock prevents concurrent builders. An incomplete
last checkpoint line is recoverable. Completed artifacts are never
overwritten; invoking the builder again validates and reuses the bank.

Only after main explicitly authorizes a completed submission snapshot,
run the isolated scorer with the same outer privileges needed by the
trusted generation-two evaluator:

`PYTHONDONTWRITEBYTECODE=1 python authoring/score_prediction_replication.py --submission COMPLETED_SUBMISSION_DIR --output concept_1/generations/generation_2/adversary/replication_champion_run1.json`

The scorer never discovers live submissions and never imports submission
code or models in its parent. It sends only exact bare fields, length
and neutral ID after READY. It uses the frozen generation-two helper,
strict prediction schema, 3-second inference / 60-second startup limits,
four enforced CPU cores and 2,048 MiB address space. Each batch starts a
fresh isolated process. Original public participant assets are read-only;
the private bank, seeds, batch labels and reference targets are not mounted.

Outputs include immutable per-batch reports plus pooled 640-case and
per-family RMSE, MAE, signed bias and maximum absolute error. The usual
metric aliases are retained. Both 320-case batches must individually
meet the unchanged 0.035 overall / 0.050 worst-family RMSE and resource
gates to receive `passed=true`; pooled errors do not replace these gates.
The pooled runtime alias is the maximum reported batch inference time,
not an expanded shared time budget. If a batch cannot produce valid
predictions, pooled 640-case errors remain unavailable rather than being
silently computed from a subset.

Resource validity and numerical accuracy remain separate. A borderline
timing failure is recorded faithfully but is not, by itself, a hard-task
or model-insufficiency conclusion. No automatic hard/easy designation is
made. Main may use a new output name for any authorized later replication;
existing reports are never overwritten. No fresh agent is launched by
either sidecar script.
