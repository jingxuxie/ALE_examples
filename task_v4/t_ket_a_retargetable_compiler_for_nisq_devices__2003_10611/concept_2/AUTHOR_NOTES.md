# concept_2 handoff

Ready as a **hard_open_candidate**. The fixed target is 2.5x SWAP overhead,
1.35x total native two-qubit operations, and 16 extra SWAPs, simultaneously in
all six relabeling families against the minimum of all 18 settings in each family.
No target changes, known passing witness, or fresh-agent outcome are claimed.
Private search is paused to unblock main's launch.

Expose only `participant/`, read-only. Give the agent a separate writable output
directory. It submits `OUTPUT_DIR/witness.json`; no submission Python is executed.
The supplied source is the method under test, not a claim about current tket or
a paper approximation theorem. Every comparison uses identical initial placement
and permissible routing operations. All scoring rules and relabelings are public.

Evaluator: `python -I -B evaluator/evaluate.py --solution-dir OUTPUT_DIR`.
It also supports a positional solution directory, an optional `--output-dir`, and
`evaluate(solution_dir, output_dir=None)`. Static artifact evaluation deliberately
does not call the shared `run_python` sandbox for submission code.

Baseline: `participant/baseline/witness.json`, seed 0, grid16, 96 demands,
24 certified SWAPs, 168 native two-qubit operations. It is valid and does not pass;
core score is approximately 0.05556. Generator requires an explicit output path.

Run author checks with `python -B evaluator/hidden/test_validation.py`.
The 47 checks include malformed/duplicate/nonfinite JSON, negative and boolean
indices, forged costs and mapping, both per-wire dependencies, missing/duplicate
gates, physical orientation/adjacency, SWAP state updates, symlinks, FIFOs,
directories, oversized/deeply nested inputs, and submission-module poisoning.
All 108 baseline portfolio routes and 108 randomized routes replay successfully.
Reports and SHA-256 frozen asset manifest are in `adversary/`.

Main owns every fresh ultima-alpha one-hour launch. This worker launched none.
No source or output files were intentionally written outside concept_2.
