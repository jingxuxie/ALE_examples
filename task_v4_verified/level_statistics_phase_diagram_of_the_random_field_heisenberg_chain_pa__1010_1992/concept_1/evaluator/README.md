# Trusted generation-two evaluator

After main freezes `targets.json`, run from this generation directory:

`python3 evaluator/evaluate.py --submission participant/baseline --output attempts/baseline_official.json`

Only L14 is graded: 320 records and 80 per family. Hidden labels and
commitments are under `evaluator/hidden/`, never under participant.
The evaluator and seccomp sandbox derive from the final generation-one
trusted implementation, including explicit resource gating and metric
aliases. Only IDs, lengths and exact fields enter the isolated process,
after READY. No submission code or learned assets are imported in the
parent. Limits are 3 seconds inference, 60 seconds startup, four enforced
cores and 2,048 MiB address space. Isolation failures fail closed.

Main owns commitments, target freezing, official sandbox checks and all
fresh launches. This package does not launch a solving agent. Its
baseline is refitted solely from original public code and public labels;
no previously tested agent artifact is made available to participants.
