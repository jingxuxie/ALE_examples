# Build, evaluation, and author handoff

All commands below run from `concept_02_gateset/`. Python 3.10, NumPy 1.21.5 and SciPy 1.8.0 were used; no Qiskit runtime is required. The shared `../private/evaluation_sandbox.py` and pinned source checkout are parent-task dependencies, not files authored here. The evaluator deliberately uses `/usr/bin/python3` for the shared Landlock runtime allowlist.

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python private/reference/generate.py --seed 241003906 --pool all --example
python private/reference/test_reference.py
python private/reference/scale_check.py --qubits 20 24
python private/reference/audit.py
python private/evaluator.py --submission private/reference/solver.py --pool core --output private/reference/reference_core.json
python private/evaluator.py --submission private/reference/weak_baseline.py --pool core --output private/reference/baseline_core.json
python private/evaluator.py --submission private/reference/solver.py --pool challenge --output private/reference/reference_challenge.json
python private/evaluator.py --submission private/reference/weak_baseline.py --pool challenge --output private/reference/baseline_challenge.json
```

For a future unseen-seed ratchet, preserve the checked-in pools and generate an alternate owned root:

```bash
python private/reference/generate.py --seed 72631229 --pool all --root private/reference/ratchet_72631229
```

That command generates the two pool structures and calibrated manifests below the alternate root. Review their independent checks and quality before explicitly promoting files into the active pool paths. Changing a seed regenerates both physical rates and designs; the seed is never included in participant input. The example uses a separate fixed seed and is only emitted with `--example`.

## Artifacts and observed results

- `participant/TASK.md`: nine-line mission only. `participant/input/FORMAT.md`: full physical/numeric contract and smooth scoring. `participant/input/example.npz`: sole public data sample, no labels or solutions. `participant/workspace/` and `attempt/` are empty.
- `solver.py`: standalone input-only source-derived reference; `weak_baseline.py`: standalone sign-aware scalar per-gate/SPAM baseline.
- `generate.py`, `metrics.py`: deterministic physical generation and component scoring. `core/` contains 9 hidden inputs/oracles plus a manifest; `../challenge_pool/` contains 6 plus a manifest. Each manifest pins content hashes, seeds, family, dimensions, fitted ranks, absolute losses and optimizer status.
- `test_reference.py`, `sandbox_probe.py`: independent scientific, source and sandbox checks. `tests.log` records the run. `scale_check.py`, `scale_probe.json`, `scale_probe.log`: unchanged-reference 20/24-qubit coupled scale measurements. `audit.py`, `ablation_report.json`, `ablation_log.txt`: quantitative shortcut tests. `generation_log.jsonl` records the current scale-corrected build.
- `reference_core.json`: mean 0.99165002, worst-family 0.98317233. `baseline_core.json`: mean 0.22299940, worst-family 0.20571102.
- `reference_challenge.json`: mean 0.99223239, worst-family 0.98010166. `baseline_challenge.json`: mean 0.22177107, worst-family 0.20335581.
- The isolated core reference process-runtime sum was 12.73 seconds; challenge was 26.30 seconds. Largest case runtime was 8.08 seconds and peak RSS was 340.67 MiB, below 120 seconds and 3 GiB. Timings include interpreter startup and shared-machine load, not just the optimizer; inspect individual reports rather than treating them as a scale law. Reports retain all three component scores, absolute losses, baseline/reference anchors, model ranks, family summaries, errors, runtime and peak memory.

Core reference held-out RMSE ranges from roughly 0.0023 to 0.0135; challenge RMSE ranges from 0.0035 to 0.0108. The builder additionally requires absolute held-out RMSE below 0.04 and optimizer success independently of normalized score. Strong and weak runs use the same staged-file interface and resource caps as a participant. All 14 independent tests pass, including a fresh-seed 24-qubit fit and connected 16-qubit restricted-sector check.

## Active scale profile

The active manifests specify `scale_profile=coupled_20_24`. Exactly nine core cases remain: the largest case in each family is now a connected 20-qubit system. All six challenges are connected 20/24-qubit systems. The largest model has 672 reduced parameters; compressed structural construction touches at most four qubits per dependency scope. The reference solver itself was unchanged for this scale correction. Large restricted-sector models are single connected chains/rings, not repeated disconnected patches. Source/graph enumeration tests remain deliberately small, while production construction never enumerates the full `2^n` pattern graph.

Changes for this review: `generate.py` (scale profile, connected restricted-sector design, connectivity metadata); `scale_check.py` and its JSON/log (capped scale probes); `private/evaluator.py` (peak-memory telemetry); `test_reference.py` (24-qubit fresh-seed and connectivity checks); `participant/input/FORMAT.md` (20/24-qubit limits); three core input/oracle pairs and all six challenge pairs, both manifests, refreshed evaluation/ablation/build logs, and these author notes. The public example and mission-only `TASK.md` are unchanged.

## Isolation and reporting

`private/evaluator.py --submission PATH_TO_solver.py [--pool core|challenge] --output REPORT_JSON` starts one new subprocess per hidden input. It copies only that input and the single submitted file into a new temporary directory. The child is Landlock-restricted to this staging directory and the shared system-runtime allowlist; it cannot even read the original submission directory. The parent imports the shared `restrict_solver` helper and applies it in `preexec_fn` with 120 CPU seconds and 3 GiB address space. The evaluator additionally caps wall time at 120 seconds, open files at 64, and file size at 16 MiB, limits numerical threads to one, closes inherited descriptors, kills remaining process-group descendants, and validates NPZ headers/shapes/dtypes before loading values. `/usr/bin/time` wraps the identical solver invocation inside the same sandbox and records per-case peak RSS; reports include `peak_memory_mib`.

`HOME`, `TMPDIR`, and `NUMBA_CACHE_DIR` point inside staging. No seed, family metadata, oracle path, oracle file or other case is passed to the child. Test probes confirm denial through both `/home/xuandong/...` and `/srv/home/xuandong/...` aliases and confirm NumPy/SciPy/temp/cache access. The helper supplies filesystem confinement, not a claim of kernel network isolation; participants are instructed not to use the network.

Failed processes or invalid output receive zero for that case, with an error in the JSON report. Valid component scores are strictly loss-based with no clipping/tolerance plateau. Challenge reports set `mean_core` to null and report `mean_challenge`; both report `mean`, `worst_family`, `families`, case details and runtime.

No unrelated files, shared helper, source checkout, participant attempts, branches, or commits were created or modified. `PROVENANCE.md` describes exact source correspondence and the input-frame adaptation; `ANTI_COMPRESSION.md` records both successes and limitations, without claiming synthetic difficulty establishes hardness.
