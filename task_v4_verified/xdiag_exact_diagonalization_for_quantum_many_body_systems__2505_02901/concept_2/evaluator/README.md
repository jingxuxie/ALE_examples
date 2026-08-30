# Private witness evaluator

Run from concept_2:

```sh
/usr/bin/python3 -B participant/baseline/solve.py --input participant/input --output adversary/baseline_submission
/usr/bin/python3 -B evaluator/evaluate.py --submission adversary/baseline_submission --output adversary/baseline_evaluation.json
/usr/bin/python3 -B evaluator/evaluate.py --submission evaluator/hidden/witness.json --output adversary/witness_report.json
/usr/bin/python3 -B adversary/validate.py
```

`--submission` accepts either a directory containing `pulse.json` or a JSON file.
The evaluator reads no submitted executable, does not require `solve.py`, and
does not compare submitted amplitudes against the known witness. Read `passed`
in the JSON report; process success means the evaluator completed, not that the
witness passed. `valid` means a well-formed, physically admissible pulse.
`evaluator_valid` distinguishes checker/asset failures from ordinary failure.

The immutable evaluator model, specification, and targets are independently
hashed. They are byte-identical to the public instance at freeze time. The
checker rebuilds operators using full tensor products followed by sector
projection; generation uses direct bit flips. Target generation uses SciPy
`expm`; scoring uses Hermitian eigendecomposition of each pulse segment. The
validation script checks assembly, propagation, global/relative phase behavior,
numerical score agreement, and malformed or physically invalid submissions.

Only `participant/` and a fresh empty output directory may be exposed to a fresh
agent. Do not expose this directory, `adversary/`, `status.json`, sibling attempts,
champions, or source-authoring directories. The known pulse, generator seed,
nearby passing witness, and validation artifacts are privileged. No private
calibration point or target is used. Construction time/memory enforcement belongs
to the parent runner; evaluator time/memory are separately reported.

Targets were fixed before any fresh attempt. Baseline and privileged evaluations
are not fresh-agent attempts. A passing private witness proves feasibility, not
empirical hardness. Parent should classify only after its independent trials.
