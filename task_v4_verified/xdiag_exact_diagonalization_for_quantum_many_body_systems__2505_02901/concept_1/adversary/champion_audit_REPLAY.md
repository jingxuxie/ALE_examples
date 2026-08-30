# Reusing the private stress audit

The twelve generated input directories are standalone participant-schema fleets
under `adversary/champion_audit/inputs/`. Their exact source-ring identities,
priors, calibration changes, capacities, seeds and provenance are recorded in
`adversary/champion_audit/stress_specs.json` and `provenance.json`. These assets
are private and must never be allowlisted to a fresh agent.

After a different fresh submission is complete and explicitly authorized for
inspection, rerun the same stress cases from the concept directory:

```
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B adversary/champion_audit.py \
  --submission SUBMISSION_DIRECTORY --reuse-inputs --output-tag new_best
```

Run this command escalated so the existing bwrap isolator can establish its
namespaces. Every baseline and candidate invocation retains the exact 60-second,
one-logical-CPU, 2-GiB limits. New scoring reuses input data, not previous solver
outputs or claimed losses; policies are independently checked by direct quantum
evolution. The same per-instance baseline and conservative relaxed bound are
recomputed. No new passing threshold is introduced.

The new principal summary is `adversary/champion_audit_new_best_summary.json`;
detail reports and policies go in `adversary/champion_audit_new_best/`. Original
inputs and the current principal summary remain unchanged. Select a previously
unused output tag for every run. The audit does not inspect any submission other
than the directory explicitly passed to `--submission`.

The audit has a bounded global runtime and writes intermediate results after
each fleet. Summary counters distinguish generated fleets from completed valid
comparisons. Residual optimistic-bound gaps and resource/protocol-only failures
are not counted as scientific failures.
