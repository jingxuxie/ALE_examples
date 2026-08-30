# Active mirror-benchmark crosstalk prediction

**Mode E — ACTIVE EXPERIMENT DESIGN.** Operate a simulated 16–25-qubit grid
processor. Choose native-edge matchings, even mirror depths, and shot allocations
to learn its unknown layer errors and sparse simultaneous-gate crosstalk. After
closing experiments, predict layer entanglement infidelities for 96 previously
unavailable, denser matchings. SPAM depends on matching context and sometimes
drifts. Family identity is disclosed; its parameters are not.

## Interface

Put your final self-contained policy at **`OUTPUT/submission/policy.py`**, with
required helper files inside `OUTPUT/submission/`. Keep development logs,
experiments and temporary assets elsewhere under `OUTPUT`; only `submission/`
is snapshotted for evaluation and subject to its 16 MiB limit. The trusted
evaluator starts a fresh, **bubblewrap-isolated subprocess** for every episode.
Read one JSON object per stdin line, write one per stdout line, and flush.
The evaluator sends `hello`; your messages are `experiment`, then `ready`, then
`final`. Diagnostics belong on stderr. `workspace/API.md` specifies the complete
protocol. The runnable weak baseline is exactly `baseline/policy.py`.

## Objective and resources

Generation 3 fixes a 2,000-shot budget; all four physical families and the quality targets remain the same.

Each episode permits 2,000 shots and 768 experiments; a request uses 32–4096
shots and an even depth from 0 through 256. Empty and singleton matchings are
legal. Experimental matchings have at most `floor(n/2)-2` edges; withheld targets
have `floor(n/2)-1`. Targets are fixed before interaction and revealed only after
`ready`; no further experiments are then possible.

For each family, pool squared prediction errors normalized by
`0.003 + 0.10 * true_rate`; its score is `1/(1+mean_squared_error)`.
Pass requires the mean of the four family scores to be at least **0.50**, the
worst family score to be at least **0.3902439024390244**, and every episode to be
valid and isolated. The hidden suite has one episode of each graph size in each
family. Limits per episode: 90 seconds wall time and 60 seconds aggregate CPU.
Each process has a 1536 MiB address-space limit and a 64-file-descriptor limit.
Stderr is capped at 256 KiB; every writable regular file, including scratch
files, also has a 256 KiB size limit. Each policy stdout JSON line is limited
to 32,768 bytes before its newline. The policy has no network or private evaluator access.
Python, NumPy 1.21 and SciPy 1.8 are installed; no downloads are needed.

## Public assets

- `workspace/MODEL.md`: complete generative law, support distributions and ranges.
- `workspace/model.py`: executable public episode generator, including truth for development.
- `workspace/develop.py`: line-delimited subprocess development runner.
- `input/limits.json`: fixed limits and scoring targets.

From this participant directory, run the baseline on public episodes:

```bash
OPENBLAS_NUM_THREADS=1 python -B workspace/develop.py --submission . --policy baseline/policy.py --family all --shape all --seed 2026
```

For your submission substitute its directory and relative policy path. Public
development seeds are independent of private seeds. Development reports are not
official passes. Only this participant tree is an authorized research resource;
do not read sibling evaluator, audit, attempt, or champion data.
