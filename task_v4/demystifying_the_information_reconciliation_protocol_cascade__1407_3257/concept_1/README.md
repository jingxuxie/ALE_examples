# Generation-side handoff: concept_1

Mode A baseline improvement, not simulator implementation. Only this concept
directory is authored. The participant deliverable is a JSON policy.

## Layout and exposure

- `participant/`: the **only** directory to copy into the fresh public workspace.
- `evaluator/evaluate.py`: trusted parent-side scoring entry point.
- `evaluator/hidden/cases.json`: fixed private case tuples, frame seeds, and conditional stress errors.
- `evaluator/frozen.json`: post-calibration integrity manifest and fixed target.
- `evaluator/test_validation.py`: generation-side simulator and contract validation.
- `champions/baseline/`: paper-inspired reference policy and measured reports.
- `adversary/calibration/`: author-only ablations, never fresh attempts.
- `adversary/`: validation and risk audit.
- `attempts/`: fresh-attempt ledger, initially empty of actual attempts.
- `status.json`: machine-readable handoff and honest challenge status.

Keep the reference root inaccessible to a fresh worker. Run evaluation from
the parent with Python isolated mode; the candidate path is data, not code:

```sh
python3 -I evaluator/evaluate.py --policy /absolute/path/to/policy.json --split hidden --jobs 8 --output /absolute/path/to/report.json
python3 -I evaluator/test_validation.py
```

Run these commands with this concept directory as the working directory.
The parent owns fresh-worker launch/isolation and tournament orchestration.
No fresh agent was launched during generation. Do not mount `evaluator/`,
`champions/`, `adversary/`, or this handoff directory into that worker.

The evaluator imports only trusted reference modules and checks source/case
hashes before scoring. It never imports candidate Python, starts candidate
commands, or accepts candidate-generated metrics. JSON has strict key,
size, numeric, nesting-shape, and vocabulary limits. The main remaining
isolation requirement is preventing the fresh worker from reading the
private source tree or modifying trusted files; that belongs to the parent.

`evaluator/build_cases.py` is generation-only; do not regenerate fixtures after
freeze. `evaluator/calibrate.py` is author calibration on training only; its
outputs do not establish fresh-worker success. The hidden suite is a fixed
benchmark, not a proof of physical security or rare-event population FER.
