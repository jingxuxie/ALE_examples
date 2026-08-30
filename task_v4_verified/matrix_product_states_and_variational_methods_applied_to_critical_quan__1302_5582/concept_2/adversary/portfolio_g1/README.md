# Ratchet-v2 private achievability portfolio

An actual D=24 tensor passes the unchanged `critical-vacuum-v2` evaluator.
The selected artifact is `state.npz`; `exact_checker_score.json` is the official
entrypoint result. The separately invoked public checker and a random complex
parity-preserving gauge audit also pass. All four family scores, the core score,
and the worst-family score are 1.0.

| Condition | Selected value | Frozen bound |
| --- | ---: | ---: |
| Energy excess | 2.6928846230e-5 | 5e-5 |
| Maximum xx relative error, every r=1..1024 | 0.02291794650 | 0.025 |
| Maximum connected zz relative error, every r=1..256 | 0.04813237298 | 0.1 |
| Maximum yy relative error, every r=1..128 | 0.09097552817 | 0.1 |
| Right-canonical Frobenius defect | 2.1670435463e-15 | 2e-8 |
| Parity defect | 0 | 2e-8 |
| Minimum stationary-density eigenvalue | 5.1090104492e-10 | at least 1e-12 |
| Second transfer eigenvalue modulus | 0.99960515138345 | at most 0.99999999 |

Worst distances are xx=1024, zz=20, and yy=4. Correlation length is about 2532.12.
The root artifact SHA-256 is
`ff80107fb6dbe8bd71c5cf8c27b2e913ea66089194fe5df8650b5d222328298d`.

## Construction and portfolio

`optimize.py` uses two real QR row isometries to enforce right canonical form
and the prescribed parity blocks exactly. A trace-constrained stationary solve
and dyadic transfer powers provide differentiable actual tensor contractions at
all required distances. L-BFGS fits all four normalized error families jointly.
The new implementation agrees with the independent evaluator to better than
9e-15 in the initial observable audit; directional derivatives agree to better
than 4e-8 relative at stable finite-difference step sizes.

The selected `direct17/0008_1024_square_00800.npz` required 883 objective/gradient
evaluations and 55.36 seconds of logged worker time, including checkpoints but
excluding Python/Torch startup. It warm-starts from this sidecar's own earlier
v1 tensor, not from a fresh random initialization. The curriculum strategy
also passes in 69.58 seconds from the same private v1 warm start. These are two
strategies, not two independent random seeds. A third branch uses the earlier
private seed-71 tensor; its scored checkpoints remain available, including
primitivity failures. No further search is needed once the official pass exists.

`near_miss.npz` retains the best valid failing checkpoint.
`near_miss_score.json` records its full score. `portfolio_results.json` records
the selected source, hashes of the unchanged checker/contract inputs, exact
results, worker summaries, and the complex-gauge audit.

## Reproduce

Run from this directory, keeping all output here:

```sh
PYTHONDONTWRITEBYTECODE=1 python -u optimize.py --validate
PYTHONDONTWRITEBYTECODE=1 python -u optimize.py --name direct17_replay --seconds 1500 --iterations 2000
PYTHONDONTWRITEBYTECODE=1 python finalize.py
PYTHONDONTWRITEBYTECODE=1 python ../../evaluator/evaluate.py --submission . --output replay_checker_score.json
```

Only this directory is written. No attempt files or champion construction code
were accessed. The earlier v1 portfolio evidence, v2 targets, and status files
are unchanged. See `provenance.md` for permitted inputs and research sources.
