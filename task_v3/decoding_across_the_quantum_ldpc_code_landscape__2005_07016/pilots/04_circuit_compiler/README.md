# Pilot 04: circuit compiler

Expose only `participant/` to the agent. Its editable entry point is
`participant/workspace/solve.py`. Keep all `private/` assets and the vendor
directory inaccessible. No external agent is launched by this pilot.

From this directory, with the main task's pinned private vendor and isolation
helper present:

```
python3 private/reference/build.py
python3 private/evaluator.py --calibrate
python3 private/evaluator.py --submission /absolute/path/to/submission --split pilot --report report.json
```

Run evaluation/calibration outside the outer sandbox: participant execution
uses the shared bwrap `research/isolation.py` helper. A submission directory
contains `solve.py`; `protocol.py` and `weak.py` remain available from the
read-only `/task/workspace` mount. `PILOT04_VENDOR` may override the private
vendor location. Reference generation requires Stim 1.16.0, NumPy 1.26.4,
SciPy 1.13.1, and the installed bposd/ldpc CSS constructor.

The pre-implementation rationale and anti-compression criteria are in
`private/reference/design.md`. Actual validation is stored in
`private/reference/validation.json`; measured baseline/reference runtimes and
scale counts are in `private/reference/calibration.json`. Inputs, exact JSON
answers, and official `.stim`/`.dem` artifacts are in `private/challenge_pool/`.
The initial `pilot`, `challenge`, and `holdout` split names share that pool.
`--report` and `--output` are aliases. `attempt/` is intentionally empty.
