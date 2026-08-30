# Trusted static-witness evaluator

Run `python3 evaluator/evaluate.py PATH` where PATH is a solution directory
containing `submission/witness.json`, a directory containing `witness.json`, or
an explicit witness JSON file. `--solution-dir` and `--output REPORT.json` are
also supported. The importable entry point is `evaluate(solution_dir) -> dict`.
It always emits the requested score, validity, pass, and reason fields for a
participant error; trusted-asset failures are infrastructure errors.

No subprocess or submitted Python is run, so shared `authoring/sandbox.py` is
not required. The sole runtime target dependency is `hidden/frozen_instances.json`
plus its integrity manifest. The planted witness and generation script are not
imported, executed, compared, or needed at grading time. All semantic acceptance
comes from edge checks and exact integer replay against the frozen **public**
constraints; phase visits are observed rather than trusted annotations.

Expose only `participant/` to the fresh agent. Keep `evaluator/`, `adversary/`,
`attempts/`, `champions/`, and `status.json` private. In particular, neither
`hidden/planted_witness.json` nor the generation seeds/obligation locations in
`hidden/freeze.json` may enter the participant sandbox. The public baseline has
no access to those files. Publish only the target suite, not generator artifacts.

`hidden/build_instances.py` is the one-shot authoring constructor. It emits an
apply_patch patch, uses private independent entropy, and refuses to regenerate
once frozen. Fixed recipes use native disjoint matching layers without immediate
inverse repeats. Required masks are sampled from several internal time bands,
exclude unit masks and final rows, and are published sorted, without their
locations. The targets have 12% count and 15% depth headroom over the private
walk. This proves a resource-feasible joint construction, not optimality or a
complexity lower bound. Six cases, three families, and simultaneous resource
budgets prevent a pure all-to-all elimination task. No private feasibility
witness is a solver result or a champion submission.

Run `python3 adversary/validate.py` for author checks; it saves reports in
`attempts/`. This includes the baseline, planted witness, mutated negatives,
independent bit-matrix replay, parser hardening, and separate count/depth tests.
The evaluator supports ordinary Linux regular files and rejects symlink, FIFO,
nonfinite, duplicate-key, oversized, malformed, and incomplete submissions.
