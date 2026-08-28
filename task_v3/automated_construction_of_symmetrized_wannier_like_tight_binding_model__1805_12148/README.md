# Mining result: rejected

No frontier-hard task is accepted from this four-concept tournament. Read `FINAL_REPORT.md` for the candidate ledger, source gaps, valid fresh-agent scores, counterexample audits, orchestration disclosure, and rejection reasons. `manifest.json` is the machine-readable disposition.

The four `pilots/` directories retain their participant artifacts, privileged references/evaluators, valid submissions and private audit material. `authoring/` contains pinned source checkouts, reproducibility environments, research, validation and tournament logs. These are authoring/evaluation artifacts, not an accepted benchmark release.

**Do not expose this root, `private/`, or `authoring/` to a participant.** Only a pilot's `participant/` and a separate empty attempt directory belong in an agent allowlist. Archived interrupted attempts are expressly excluded from the reported tournament.

To recheck a stored valid submission, run from this directory:

```bash
OPENBLAS_NUM_THREADS=1 python pilots/03_device_transport/private/evaluator.py \
  --submission pilots/03_device_transport/attempt \
  --split test --output transport_recheck.json
```

Submitted evaluation keeps its inner bubblewrap sandbox enabled. An outer sandbox that prohibits nested namespaces requires the normal approval path; do not disable inner isolation or score namespace failures as scientific failures. Each pilot's authoring note documents its reference setup and additional checks.

No ratcheted candidate survived the fairness/reference-validity gates, so no fresh ratchet-confirmation score is claimed. The existing reserved confirmation files are not evidence of such a model run.
