# Mandatory private champion search

This directory replays the **actual fresh D1 submission**, not the sidecar inverse. It is private audit material, not a new participant generation or champion archive.

## Fixed challenge

- 192 independent accepted Hamiltonians: four draws for each of six families × two pair counts × four virtual counts.
- Two additional non-IID support probes: both physical roots of the previously constructed rare two-root case, each satisfying the original weak-correlation/nonnegligible-tail curation.
- Cases are shuffled and identified by independent opaque IDs. Predictor inputs have the public feature schema only. Truth and the independent sampling seed are never mounted into the predictor process.

## Exact replay

The fixtures are already fixed. Do not regenerate them. From the concept_3 root, on a host permitting rootless bubblewrap namespaces:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B adversary/champion_search/replay.py run --run-name replay_2
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B adversary/champion_search/replay.py score --run-name replay_2
```

Choose a new run name; earlier runs are never overwritten. The first command runs the unchanged champion inside the feature-only sandbox. The second is the trusted private scorer and runs only after prediction completes. No call to the official evaluator is made. A nested sandbox may require approval to launch bubblewrap outside it; never replace the isolated run with an unsandboxed submitted-code import.

## Artifacts

- `sandbox_input/`: exact source snapshots, checksums, feature-only NPZ and the mechanical I/O adapter; the only task-specific read mount.
- `private/truth.npz`: private labels and true transfer matrices for scoring/debugging; never mounted.
- `private/sampling_manifest.json`: independent audit randomness, strata/cohorts, data/source checksums and protected-file hashes.
- `runs/run_1/launch.json`: exact bubblewrap command, mount policy, exit status, wall runtime and input checksums.
- `runs/run_1/outputs/`: the champion's predictions, inferred transfer matrices and feature-only diagnostics.
- `runs/run_1/score.json` and `case_results.json`: private aggregate/per-case errors, root diagnostics and failures.
- `REVIEW.md`: code-review and isolation rationale. `REPORT.md`: final interpretation after the run.

This audit does not modify the launched participant package, evaluator, frozen criteria, original prediction file or official static score. The main process archives the champion separately and decides any future ratchet.
