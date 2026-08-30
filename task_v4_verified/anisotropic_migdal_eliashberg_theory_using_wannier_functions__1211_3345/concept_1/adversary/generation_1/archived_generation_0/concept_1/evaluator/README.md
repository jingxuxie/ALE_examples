# Private evaluator operation

Run from the concept root:

```sh
python evaluator/evaluate.py --submission participant/workspace --report attempts/result.json
```

`--cases case_00 case_16` is diagnostic only and cannot pass the full objective.
Output includes `core_score` (overall acceptance), `worst_family_score`, `passed`,
`reason`, `runtime`, `resources`, and the older `overall`, `score`, `success` keys.
All thresholds live in `hidden/policy.json`. `hidden/baseline_anchor.json` fixes
the measured comparison baseline; its score plus improvement is checked <= 1.
`hidden/prelaunch_seal.json` records SHA-256 hashes before any fresh launch.

The trusted parent never imports a submitted module. Each case is serialized
without labels or metadata into a fresh scratch directory. A bounded,
descriptor-relative, no-symlink copier stages the submission. The child-only
`launch.py` adapter calls the shared `../authoring/sandbox_runner.py`, preserving
its Landlock/seccomp restrictions and additionally prohibiting clone/clone3.
There is no insecure fallback. Candidate code gets only generic instance/output
filenames, public physics assets, and the copied submission. Input mutation in
scratch does not affect the parent's in-memory instance.

The evaluator supplies a minimal environment and closed stdin, bounds CPU,
memory, file size, and wall time, kills the child process group, and uses parent
`getrusage(RUSAGE_CHILDREN)` deltas rather than candidate stderr timers. Candidate
forks and threads are prohibited. Calls are serial within each evaluator, so
the child-usage delta is attributable to that invocation. Parallel evaluation
should use separate evaluator processes, not threads sharing this process.

Output must resolve inside scratch and cannot be a symlink, hard link, FIFO,
device, pickle, oversized archive, unexpected member set, or invalid array.
Headers are checked for shape/dtype before allocating the payload. The private
parent recomputes both equations with blocked direct frequency sums; it does
not trust the public FFT implementation, candidate residuals, output metadata,
or any claimed convergence flag.

Requirements: Linux with Landlock and libseccomp, Python 3.10+, NumPy, SciPy,
and the shared runner at the path above. The builder environment uses NumPy
1.21.5 and SciPy 1.8.0. Do not expose `evaluator`, `champions`, `attempts`,
`adversary`, or `status.json` to a fresh participant. Expose `TASK.md` and the
`participant` tree only. Do not run suite generation/sealing after fresh launch.
