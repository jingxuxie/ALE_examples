# Author-only pilot operations

Run from `pilots/01_covariant_pipeline`. Do not mount this directory or
`authoring/` in a participant run. Submitted code now runs through the shared
`authoring/sandbox_exec.py` helper with bwrap, `/usr/bin/python3`, a 90-second
timeout and 4 GiB address-space limit. Only participant, submission, case and
output trees are mounted, without private references or network. Scratch output
directories are outside `/tmp`, which the helper replaces with a fresh tmpfs.
The exact `private/strong` author-reference path retains its existing process
execution and dependency environment; no reference generation or scoring changes.
`attempt/` is delivered empty. Populate it from `participant/workspace/` only
when the parent launches the participant, not during this preparation step.

The participant needs only Python, NumPy and SciPy. Author reference generation
imports the pinned local TBmodels source before `authoring/vendor`; it does not
write either shared location. The reference engine is never imported by scoring.
Nearest-atom import uses the exact official `84cdd38` fixed method with the
current model infrastructure. Later TBmodels adds periodic-image search, which
is a different API semantic from this pilot's explicit-atom contract. Independent
text checks enforce that distinction; no custom repair is substituted.

## Reproduce

```
PYTHONDONTWRITEBYTECODE=1 python private/extract_history.py
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python private/build_cases.py --split all
python participant/workspace/solve.py --input participant/input/smoke --output private/validation/smoke_weak.npz
python participant/workspace/smoke_check.py --input participant/input/smoke --output private/validation/smoke_weak.npz
python private/evaluator.py --submission participant/workspace --split test --output private/validation/weak_test.json
python private/evaluator.py --submission private/strong --split test --output private/validation/strong_test.json
python private/evaluator.py --submission private/strong --split challenge --output private/validation/strong_challenge.json
python private/evaluator.py --submission private/strong --split confirmation --output private/validation/strong_confirmation.json
python private/evaluator.py --submission participant/workspace --split challenge --output private/validation/weak_challenge.json
python private/evaluator.py --submission participant/workspace --split confirmation --output private/validation/weak_confirmation.json
PYTHONDONTWRITEBYTECODE=1 python private/validate.py
```

The challenge pool is already materialized. Confirmation uses a disjoint seed
bank, inverse cell shears, different embedding stretches and supercell axes;
its labels are independently frozen before evaluation. Rebuilding is an
authoring action, never part of scoring. Do not tune on confirmation after
participant attempts. To launch a participant, expose `participant/` and a
writable `attempt/`, initialize the latter from `participant/workspace/`, and
instruct it to repair the entrypoint. No agent runner is launched here.

`reference/extraction.json` records exact method lines/hashes. The split
manifests record source-file hashes, all transformations, weak errors, label
and input hashes, independent residuals, and shortcut ablations. Reference
NPZs contain complete complex matrices, not just eigenvalues. Validation reports
are disposable outputs; NPZ labels and manifests are the scoring inputs.

If the central isolation wrapper cannot create its network/mount namespace,
that is an infrastructure failure, not a solver score. Run the evaluator with
the required outer execution approval while retaining the wrapper's isolation.
This pilot's local numerical validation does not claim to validate that wrapper.
