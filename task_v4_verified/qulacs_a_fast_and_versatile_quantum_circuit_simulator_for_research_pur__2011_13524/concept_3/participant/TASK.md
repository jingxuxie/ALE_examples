# Calibrate a noisy two-qubit experiment

## Mission
Write an executable `solution.py` that chooses experiments and estimates ten unknown coherent-noise, correlated-dephasing, and effective SPAM parameters. Frequency aliases, uncertain visibility, and correlation-sensitive measurements compete for a limited experiment budget. The model is completely specified; no paper knowledge is required.

## Assets
`input/PROTOCOL.md` defines the physics, priors, JSONL interface, and scoring. `input/simulator.py` exposes the exact probabilities, derivatives, prior sampler, and scoring function. `input/public_examples.json` supplies three disclosed practice episodes. `input/estimation.py` and `baseline/solution.py` supply a runnable nonadaptive multistart maximum-likelihood baseline. `workspace/` identifies the starting layout; participant assets are read-only during fresh attempts. Work in your designated writable output directory and submit it with `solution.py` and any helper files.

## Interface
The evaluator starts a fresh Python process per episode, sends initial metadata, and then exchanges one JSON object per line. Reply with an experiment or a final parameter estimate. Each observation contains only your action, binary counts, and remaining budgets. Flush stdout; send diagnostics to stderr. The process must exit successfully after its estimate. Your submission receives a fresh local `input/` copy.

## Objective
Maximize the published score on 18 fixed hidden episodes, six each from three disclosed prior families. Passing requires **mean >= 88 and worst-family mean >= 85**, fixed in `input/OBJECTIVE.json`, and valid completion of every episode. The family, parameters, and outcome seeds of hidden episodes are never supplied to your process. Public examples do not count toward hidden performance.

## Resources
Per episode: **48 queries, 6,144 shots, 1–1,024 shots/query, 45 seconds wall time, 40 seconds CPU, one CPU affinity, and 1,024 MiB address space**. Python, NumPy, and SciPy are available; no Qulacs installation or reference solver is required. Use only supplied public assets and observations, not evaluator files, hidden data, other processes, or network services. Submission limit: 128 files / 8 MiB, no symlinks. Public smoke test, from the participant asset directory: `python input/public_evaluate.py --submission /absolute/path/to/your/output --output /absolute/path/to/your/output/public_report.json`. This runner uses only disclosed public examples and copies only public inputs; no private evaluator access is needed.

## Scoring
The 0–100 episode score combines scaled parameter error and predictive error on a fully disclosed measurement grid. Invalid protocol, nonfinite/out-of-range outputs, exceeded budgets, and resource violations score zero and fail the submission. Reports include mean, worst-family mean, family means, runtime, pass/fail, and reason. See `input/PROTOCOL.md` for the exact formula.

The 45-second solve clock starts after the isolated runtime is ready, before your
program receives metadata. Host sandbox setup is separately bounded and is not
scientific task time. Address-space limits are per process; execution is pinned
to one CPU core.
