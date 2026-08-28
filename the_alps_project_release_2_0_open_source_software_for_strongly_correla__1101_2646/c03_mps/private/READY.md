# Ready for main evaluation

Participant is frozen. No participant file has been edited since the frozen-ready signal. The sidecar has launched no agent runner and has not populated any attempt with a solution.

- Six core and six challenge references are complete, two cases per physical family in each split.
- Every reference passes chi 64 versus 128 convergence in energy, gap, and correlations, plus charge, norm, final-sweep, and input-hash checks.
- All six small ED-versus-TeNPy checks pass, and all six corresponding baseline CLI checks pass inside main's network-disabled wrapper.
- The full frozen weak baseline passes invocation on all 12 cases. Core mean score: approximately **0.000214**; challenge mean: approximately **0.000261**; worst-family score on either split: approximately **0.0000808**. These are supplied-baseline checks, NOT fresh-agent scores.
- Stored-reference self-score is 1.0 for every case. Perfect energy with missing gaps/correlations scores only 0.20.
- Initial reference generation took 100--352 seconds per case, using six processes with one BLAS thread each. TeNPy's optional extension subsequently compiled successfully in the private copy; no shared source checkout or global Python installation was changed by that build.
- `private/evaluator.py` honors `ALPS_EVAL_WRAPPER`, requests `--memory-mb 8192 --threads 4`, records `_resource.json`, and passes only temporary physical inputs to the solver.

## Main entry points

```
ALPS_EVAL_WRAPPER=/absolute/path/to/shared/sandbox_exec.py python private/evaluator.py --submission /absolute/path/to/submission --split core --report /absolute/path/to/report.json
ALPS_EVAL_WRAPPER=/absolute/path/to/shared/sandbox_exec.py python private/evaluator.py --submission /absolute/path/to/submission --split challenge --report /absolute/path/to/challenge_report.json
```

Run the wrapper-enabled commands escalated as planned by main. No additional reference build or generation is needed. `private/README.md` documents provenance, scoring, model choices, and reproduction commands.

## Authored/created files

- Public: `participant/TASK.md`; `participant/input/CONTRACT.md`; `participant/input/example_spin1.json`; `participant/input/example_boson.json`; `participant/workspace/solve.py`; `participant/workspace/baseline.py`.
- Private implementation: `private/evaluator.py`; `private/reference/cases.py`; `private/reference/generate.py`; `private/reference/audit.py`.
- Private cases: `private/challenge_pool/manifest.json`; six JSON inputs under `private/challenge_pool/core/`; six under `private/challenge_pool/challenge/`.
- Private references: 12 JSON artifacts under `private/reference/data/`, including high/low-chi outputs and complete convergence histories.
- Validation: `private/reference/validation/small_exact.json`; `private/reference/validation/sandbox_interface.json`; `private/reference/validation/artifact_audit.json`; `private/reference/validation/weak_core.json`; `private/reference/validation/weak_challenge.json`; `private/reference/validation/participant_freeze.json`; `private/reference/validation/readiness.json`; associated generation/check logs and the two small baseline outputs.
- Dependency copy/build: `private/reference/vendor/tenpy/`, pinned to `b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04`; `private/reference/tenpy_build.log`.
- Documentation: `private/README.md`; this file. `attempt/` was created empty and is now left to main.
