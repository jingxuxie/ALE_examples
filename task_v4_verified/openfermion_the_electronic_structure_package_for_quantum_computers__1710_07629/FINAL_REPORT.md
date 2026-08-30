# Hardness-discovery result

**Final status: `hard_verified_achievable`. Selected task: concept 2, sparse
native-graph Slater-state circuit construction. Solvability is demonstrated.**

## Concepts and verification modes

| Concept | Primary mode | Final status | Solvability |
|---|---|---|---|
| Joint orbital/auxiliary gauge compression | A — baseline improvement | `solved` | Demonstrated by fresh champions |
| Sparse native-graph Gaussian-state synthesis | C — witness/design construction | `hard_verified_achievable` | Private witness certifies all four targets |
| Correlated Hubbard gap prediction | D — hidden prediction | `rejected` as a hard candidate | Unchanged predictor passes after packaging-only cleanup |

Nine concepts were considered; three were built. Six isolated fresh attempts
used `ultima-alpha`, with a one-hour limit each.

## Baseline, champion and fresh scores

**Concept 1.** Scores are relative coefficient-cost reductions; generations
use different cases/reference costs and must not be added together.

| Generation | Baseline / private control | Fresh score | Worst-family score | Runtime / target |
|---|---|---|---|---|
| Initial | Baseline approximately 0%; private portfolio 44.5191% | 44.8878%, pass | 26.1069% | 86.199 / 180 seconds; targets 25% / 10% |
| Ratchet 1 | Supplied champion approximately 0%; private quality-only artifacts 2.0029% | 1.7080%, pass | 1.7080% | 19.161 / 20 seconds; targets 1% / 0.5% |

The ratchet has one disclosed family and two hidden cases, so its worst-family
score equals its aggregate score. The private quality-only artifacts were not
claimed to be a runtime-valid generic solver; the fresh challenger establishes
that achievability.

**Concept 2.** Baseline: **0/4** certified, resource score **0.02823**.
Fresh attempts: **2/4 each**, core/worst-family **0.5/0.5**, resource scores
**0.93529** and **0.96547**. Neither satisfies the complete witness condition.
All eight submitted circuits attain numerical state accuracy; resources fail.
The private witness scores **4/4**, core/worst/resource **1/1/1**.

**Concept 3.** Passing requires core and worst-family scores at least **0.5**,
with a **25-second, one-CPU** inference budget.

| Generation/control | Core | Worst-family | Runtime | Outcome |
|---|---:|---:|---:|---|
| Initial kernel baseline | 0.208190 | 0.265776 | 0.994 s, matched-affinity retest | Accuracy fail |
| Initial fresh native champion | 0.999982 | 0.999987 | 24.093 s official; 11.467 s mutex retest | Pass |
| Ratchet kernel baseline | 0.216491 | 0.280843 | 0.749 s | Accuracy fail |
| Supplied native champion on ratchet | 0 | 0 | Exceeds 25 s | Resource fail |
| Ratchet raw fresh artifact | 0 | 0 | Rejected before inference | Exceeds 256-MiB submission cap |
| Packaging-normalized unchanged fresh solver | 0.505107 | 0.524349 | 24.505 s | Pass; diagnostic control, not a fresh submission |

The normalized predictor has charge/spin RMSE **0.029393 / 0.013783** against
limits **0.030 / 0.020**. Only unused `dev/` intermediates were omitted; source,
weights and hyperparameters are byte-identical. The raw tree is 1,018,469,990
bytes; the normalized tree is 76,677,488 bytes. This packaging-only failure is
**not** treated as genuine prediction hardness.
An independent repeat with a new hidden-row permutation also passes: core
**0.519003**, worst-family **0.524349**, runtime **24.125 seconds**.

## Counterexample searches

- **Gauge compression:** 60 supported initial-family cases and 24 competing
  locality cases were checked. Three quality gaps of approximately **1.403%,
  2.818%, and 1.183%** were mutex-revalidated, motivating ratchet 1. Thirty
  out-of-contract size cases were excluded rather than counting buffer failures.
- **Second gauge champion:** 24 additional independent cases were checked,
  followed by five repeat batches. The confirmed residual gap is **0.51117%**.
  A single-run **1.05377%** gap remains unconfirmed after a repeat timeout.
  Timing fragility and an inflated slower-run gap are not used to manufacture
  another one-percent aggregate target. No further ratchet is justified.
- **Circuit witnesses:** a privileged union of the best per-target fresh
  circuits still certifies only **3/4**. Both fail `irregular_16`: **50 gates /
  15 layers** and **45 / 12**, versus caps **40 / 12**; a private witness uses
  **38 / 11**. All **95** individual gate-deletion checks fail accuracy, and
  simple rescheduling does not remove the misses.
- **Prediction:** the unchanged native champion remains accurate on all 256
  ten/twelve-site cases but needs **209.112 CPU seconds** and **236.811 wall
  seconds** in a relaxed control. The fresh hybrid predictor overcomes this
  computation/accuracy tradeoff after packaging cleanup, so the concept is not
  retained as hard.

## Ratchet generations

**Concept 1: one. Concept 2: zero. Concept 3: one.** There are two genuine fresh
gauge champions and one original prediction champion. The cross-attempt circuit
portfolio and packaging-normalized prediction control are not extra fresh runs.

## Substantive failed capability

The retained task exposes difficulty in **joint discrete/continuous fermionic
circuit synthesis**: recovering a sufficiently sparse native-edge topology and
schedule while exploiting occupied-subspace gauge freedom and preserving exact
state accuracy. Both independent agents substantially improve the generic
compiler but miss the same irregular-graph witness. Private valid circuits
demonstrate feasibility; the evidence is empirical, not a minimality or universal
hardness theorem. No open-solvability claim or packaging-only hardness claim is
needed for the retained result.
