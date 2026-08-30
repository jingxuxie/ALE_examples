# Organizer evaluation

From concept_1:

```
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python evaluator/evaluate.py \
  --submission workspace/solve.py --report private/attempts/baseline.json
```

The JSON report contains core, worst_family, runtime_seconds, passed, reason,
family means and per-case diagnostics. The complete suite is loaded and checked
against private SHA-256 hashes before any candidate runs. Each case launches a
fresh copy of the submission's containing workspace, with capped resources and
no inherited Python path. Accuracy checking and fixture loading do not count
toward participant runtime; process startup does. No external runner is changed.

**Privacy boundary:** this local driver is a resource-limited trusted-code test
harness, NOT an OS security sandbox. A process running under the same host UID
can otherwise read organizer files. The external tournament must expose only
`TASK.md`, `inputs/`, and a writable `workspace/` to generator/participant agents,
and must conceal this evaluator and the entire `private/` tree from execution.
Use an external filesystem/container boundary for untrusted submissions. Do not
ship the whole concept directory to agents and call its fixtures hidden.

To rebuild deterministic data (organizer only), run `python private/generate.py`.
To run the evaluator validation, run `python private/validate.py`. Evidence is
written only under `private/`. The fixed contract is in `TASK.md`; do not tune its
thresholds after observing a fresh agent. The package does not start agents.
