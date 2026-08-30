# ALF hardness-discovery package

Only a concept's `participant/` directory is task input. Never expose its
`evaluator/`, `adversary/`, `champions/`, `attempts/`, or the root `research/`
directory to a participant. The latter contain privileged data and evidence.
Each concept's `status.json` records the current task generation; previous
generation contracts and evaluators are preserved under `adversary/generations/`.

Tested environment: Linux, Python 3.10, NumPy 1.21.5, SciPy 1.8.0, and mpmath
1.3.0. Concept 3 additionally requires Bubblewrap and enabled user namespaces.
Its evaluator must be launched outside a restrictive nested sandbox on this
host; it creates its own network-disabled filesystem-allowlisted sandbox.
Evaluation never executes submitted code for concepts 1 and 2.

Run from this package root, with an existing writable scratch directory:

```sh
python3 concept_1/participant/baseline/search.py --output /tmp/alf_baseline_witness.json
python3 concept_1/evaluator/evaluate.py --submission /tmp/alf_baseline_witness.json

python3 concept_2/participant/baseline/build.py --output /tmp/alf_baseline_schedule.json
OPENBLAS_NUM_THREADS=1 python3 concept_2/evaluator/evaluate.py --submission /tmp/alf_baseline_schedule.json

python3 concept_3/evaluator/evaluate.py --submission concept_3/participant/baseline
```

Replace the baseline path with the desired submission to score another artifact.
All evaluators accept `--output REPORT.json`; their JSON includes score, validity,
pass decision, reason, and measured runtime. The design score also reports the
worst-family score and maximum pointwise error ratio. Its frozen pointwise gate
is a separate requirement, not implied by its aggregate improvement score.

`research/run_tournament.py` invokes the supplied allowlisted runner with the
exact `ultima-alpha` model and a 3,600-second deadline. It requires an unused
attempt index and an empty output directory, logs outside the agent boundary,
and records participant hashes before and after execution. Attempt indices are
not task-generation numbers: sign attempt `v_2` is an excluded champion-assisted
control; clean sign attempt `v_3` tests task generation 2. See
`research/isolation.md` and the per-attempt qualification records.

Historical champion scores can be reproduced with the evaluator inside the
matching `adversary/generations/generation_N/` snapshot. Do not use the current
generation's evaluator to reproduce an earlier generation's target score.
