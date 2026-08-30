# Generation 2: persistent model-gate counterexample

Standalone private packet. Expose only the **read-only `participant/`** directory to a fresh agent. Its writable working root must be outside that directory, and the artifact must be directly at `witness.json` in that root. Do not expose this README, evaluator/hidden, adversary, champions, status, or previous submissions.

The sole ratchet is persistence under the specified box-truncated independent uniform coefficient noise at delta=0.001 Eh: nominal success plus at least 122/128 hidden successful cases. All original numeric nominal targets, model constants, and physical admissibility bounds are unchanged. This is a finite deterministic assay, not a universal robustness theorem or a population confidence guarantee.

The previous fresh v1's accepted final artifact showed 9/128 successes in an independent private broad assay at this scale. Ratio-only and joint triple/ratio failures justify the ratchet; nominal evaluation was taken from main, not duplicated. The new hidden pool was drawn once, independently of public training and the exploratory assay, before reference-candidate characterization. Do not regenerate it based on any later outcome.

From this packet directory:

```sh
python evaluator/evaluate.py --artifact /absolute/path/to/fresh/work/witness.json --report /absolute/path/to/score.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B -m unittest discover -s evaluator/hidden -p 'test_*.py' -v
```

The evaluator's default is `witness.json` in its caller's working directory. Prefer an explicit `--artifact` path during integration. It supports a positional artifact or `--submission-dir` as alternatives. It uses isolated Python, `stdin=DEVNULL`, one BLAS thread, resource caps, no submitted imports, and no candidate file search. Completed nonpassing evaluations still exit zero: inspect the JSON flags.

`adversary/baseline_witness.json` is exactly the original zero-variable baseline. `adversary/v1_witness.json` and `adversary/known_witness.json` are privileged previous solutions kept private solely for characterization. Neither is a new champion or a public starting point. `attempts/` is empty; no fresh agent is launched by this build. Any lack of known robust feasibility is stated in status rather than hidden or repaired by adjusting thresholds.

Launch only after status is ready and the freeze manifest is present. Preserve all source, targets, hidden draws, and read-only participant permissions. Main owns integration, archive, fresh launch, and future champions. No optional private optimization is required for handoff.
