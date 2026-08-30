# Pending generation-1 evaluator

Run `python evaluator/evaluate.py --submission participant/baseline --report attempts/baseline_report.json`.
The sibling `../authoring/sandbox_runner.py` is bundled at the unchanged expected
location. Numerical quality gates and 12-CPU-second/2048-MiB/one-thread resources
are unchanged; output parsing permits 32 MiB for the declared larger arrays.
The independent full-frequency verifier never imports submitted code. All
candidate execution still uses the shared Landlock/seccomp runner and local
clone guard. Previous fresh submissions are private and are not shipped in the
participant directory. Baseline improvement is anchored to the supplied public
damped solver, not the privileged previous fresh solver.
