# Private generation-3 achievability search

This directory is privileged and must never be supplied to either fresh G3 solver.
The sole warm start is the archived generation-2 champion. The optimizer is an
adaptation of the generation-2 solver source, with exhaustive triple-omission
checks and a counterexample-guided private optimization objective. The public
task, evaluator, hidden specification, and global status are never modified.

Reproduce from the concept directory:

```sh
python -B adversary/generation_3/private/build.py
python -B adversary/generation_3/private/run.py --seconds 1700
```

The four workers use explicit seeds and bounded wall durations recorded in
`config.json`. `provenance.json` hashes the original G2 source, adapted source,
binary, warm start, and frozen spec. The sparse conjugated-error checker is
tested against explicit deletions on small circuits and every scenario of the
actual G2 champion, including exact failing-scenario counts.

For optimization only, forward low-weight-set disjointness is equivalent to
inverse low-weight-set disjointness: V(S) intersects S iff V^-1(S) intersects S.
This does not replace the independent official checker, which still evaluates
every input in both directions and all fault orders. Only a complete passing
`official_report.json` demonstrates achievability. Nonpassing private artifacts
leave solvability unknown. `summary.json` records the final outcome and verifies
the frozen public/evaluator/spec/status hashes without changing those files.

## Bounded adaptations and audit

The initial counterexample-only search was also compared with exact exhaustive
Metropolis scoring and counterexample search that preserves the previous
generation's complete two-omission guarantees at every accepted mutation.
`phase2_config.json` and `*_adaptation.json` retain the replacement commands,
seeds, timings, and source hashes. Replaced workers' outputs are preserved in
their private `*_cex_archive/` directories. Replacements reuse CPU slots; at
most four native search workers run at once. The PID-bearing supervision
scripts describe this run, not portable process IDs for a future replay;
use the recorded native command arrays and configurations for replay.

`audit.json` consolidates official per-family scores, exact fault counts,
resource counts, elapsed wall time, every search seed hash, code hashes, and
checks that all frozen public/evaluator/hidden/spec/status files are unchanged.
Wall-time annealing makes optimizer trajectories timing-dependent; the saved
static artifact and its exhaustive official evaluation are reproducible.

Recheck the private candidate from the concept directory:

```sh
python -B evaluator/evaluate.py --submission adversary/generation_3/private/artifact.json --output adversary/generation_3/private/official_recheck.json
```
