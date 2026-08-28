# Bounded author-side performance acceptance evidence

This directory is the only write scope of this sidecar. It does not launch a fresh agent, execute a participant solver, change the running task, or add a concept. All numeric workers inherit the last two allowed CPUs and use one BLAS thread.

## Protocol fixed before running

- Request: the existing matched 1300 nm case, 61 by 65 sites and 15,860 BdG degrees of freedom. Use its original, unoptimized zigzag.
- Dense default: actually build the full complex128 Hamiltonian and call `numpy.linalg.eigh` under a 6 GiB address-space cap, at most two allowed CPUs, and a 30-second watchdog. Record any real allocation exception or timeout.
- Dense memory-conscious variant: Fortran-contiguous storage, overwrite enabled, no finite-check copy, SciPy `evr` selecting the eight central eigenvalues. Apply the same 6 GiB cap and a separate 60-second watchdog. This short timeout is not claimed to prove failure at 1200 seconds.
- Direct optimization: a fresh 1200-second wall budget after dense probes; two concurrent scenario workers, each capped at 2 GiB virtual memory, with a 1 GiB parent cap. Search two parameters of the original triangular zigzag: centerline amplitude and perpendicular width. Start at 100/200 nm, poll coordinates at 40 nm steps, halve down to 10 nm when the local stencil is exhausted. Reject manufacturing violations. Each accepted measurement uses all 51 momenta at all three robust operating points, plus independent topological checks; every eigensystem is recomputed directly.
- No archived optimized geometry or author greedy optimizer is read for search. The stored strong scalar is read only after search terminates. The naive baseline is deliberately given the exact three held-out operating points, a favorable assumption that must be disclosed.
- Save every candidate, full or partial per-point traces, best fully evaluated feasible result, timing/resource metadata, and exceptions. Incomplete candidates never determine best-so-far performance.
- Dense probes precede optimization, so they do not compete for its two CPUs. Numeric run time is bounded by 1200 seconds plus at most 90 seconds of dense probes and short process-cleanup overhead.

## Command

From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B baseline_gate.py --wall-seconds 1200 --dense-seconds 60
```

`summary.json` is generated after the run, not a predeclared verdict. `direct_report.json` separates wall/CPU cost and optimization quality; `best_result.json` is the best fully evaluated geometry. `events.jsonl` and `candidate_*_scenario_*.json` preserve detailed observations. Estimates are explicitly separated from witnessed outcomes. A one-family result does not establish aggregate three-family performance or rule out every possible generic method.

The first forward-worker launch encountered an inherited hard-limit setup error before numerical execution; its artifacts are retained in `setup_failure/`, not counted as numerical failure. The corrected search starts a fresh 1200-second budget and reuses the already valid dense probes with `--skip-dense`. Once `summary.json` is complete, `python -B report.py` validates and writes `REPORT.md` and `report.json` without further eigensolves.
