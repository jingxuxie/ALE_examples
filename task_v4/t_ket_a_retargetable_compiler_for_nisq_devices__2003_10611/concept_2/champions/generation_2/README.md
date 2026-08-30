# Verified routing-portfolio counterexample

The submission is the static `witness.json`. It uses `ring16`, the fixed identity
initial placement, 64 CX demands, and an explicitly replayable route containing
8 hardware-edge SWAPs. Its native two-qubit cost is **88**.

The supplied public checker reports `valid: true`, `passed: true`, and
`core_score = worst_family_score = resource_score = 1.0`.

| Relabeling family | Best portfolio SWAPs | Native two-qubit cost | SWAP ratio |
| --- | ---: | ---: | ---: |
| identity | 38 | 178 | 4.750 |
| physical-11 | 38 | 178 | 4.750 |
| physical-29 | 38 | 178 | 4.750 |
| logical-47 | 38 | 178 | 4.750 |
| joint-71 | 39 | 181 | 4.875 |
| joint-103 | 39 | 181 | 4.875 |

The worst-family SWAP gap is **30** and the worst-family native-count ratio is
**178/88 = 2.022727...**. Each family includes all 25 settings, including global
lookahead and suffix embedding. No winning portfolio route uses fallback SWAPs.

## Regularity and replay

- Every wire participates in 4–13 demands and has at least two partners.
- The connected interaction graph has 22 distinct edges.
- No pair appears more than seven times, and no pair is consecutive on both wires.
- All 64 demands execute exactly once, in per-wire dependency order.
- Every gate and SWAP uses a hardware edge; the final permutation matches replay.
- `audit.json` includes the artifact hash, per-wire coverage, and SWAP schedule.

The construction starts from a legal physical schedule, derives the logical
demands by tracking occupants, and searches schedule mutations. `fast_router.cpp`
accelerates search; its counts were differentially checked against the supplied
Python router, including the final witness. `validation.json` is the full public
checker result, not an estimated search score. `audit.py` independently checks
regularity, dependencies, adjacency, execution coverage, and final placement.

The maximum interaction degree of every suffix considered by the supplied
embedding policy exceeds the ring's degree two. Thus those particular static
suffix embeddings are infeasible, while the certificate pays for dynamic changes.
This is a counterexample to the supplied implementation only, not a claim about
current tket or an approximation guarantee in the cited papers.

## Reproduce validation

From this submission directory:

```sh
python3 -B ../../adversary/generation_2/participant/input/benchmark.py witness.json
python3 -B audit.py witness.json
```
