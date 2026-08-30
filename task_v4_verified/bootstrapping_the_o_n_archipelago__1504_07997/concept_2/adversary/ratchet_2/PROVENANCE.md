# Generation-two ratchet provenance

The starting champion is Main's `ultima-alpha` generation-one output, archived
unchanged at `champions/generation_1`. Main reports 8/8 solved in 18.4 minutes.
The builder independently rescores its archived answer against the preserved
generation-one inputs. Neither those answers nor any planted support is copied
into the new participant baseline. Original participant/evaluator snapshots
remain under `adversary/generation_1`.

## Reuse, rather than a duplicate sweep

The candidate pool is Main's existing 32-case `adversary/sweep_1/candidates.json`.
No new random case generator was introduced. The running main scripts
`adversary/sweep.py` and `adversary/champion_replay.py` are not edited. Initial
confirmation chooses the two largest completed moment-residual failures per
family. Targeted backups are checked when a corrected replay solves a candidate
or reduces its residual substantially. Only completed, normal-exit numerical
failures with independently valid planted certificates may be selected.
Public IDs are independent opaque UUID labels. The seed-bearing source-to-public
mapping is kept only in private `id_map.json`. Relabeling changes neither arrays
nor numerical certificates; archived replay answers are relabeled consistently.

## Champion adaptation, without labels

The original numerical core, support search and refinement are preserved, apart
from module imports and injected paths. The original core is named
`champion_core.py`; `solve.py` supplies the input-file/output-file CLI. Each case
uses fresh scratch beneath the output directory, so participant material can be
read-only. No old input paths, saved solutions, seeds or planted supports are read.

The enumeration stage no longer uses `range(1,24)`. It freezes nonzero-spin
indices from the *current computed iterate*, then enumerates all remaining
spin-zero candidates, ordered by their supplied dimensions. This generalizes
the original weak-residue conditional enumeration to every family. The preceding
support-exchange stage still considers every candidate, including nonscalars.
This remains a heuristic, not an assertion that nonscalar support is known.

Enumeration formerly fitted its retained candidates only after exhausting the
entire combinatorial iterator. It now reserves 55% of its stage allowance for
fitting the best retained supports. This prevents the larger, correct candidate
domain from making its result disappear at a timeout. The source SVD ranking,
heap size, nonlinear fit and stop criteria are retained. Unused early-stage time
flows to enumeration. The alarm exception bypasses broad numerical-exception
handlers, preventing an alarm from accidentally starting an unbounded fallback.
`adaptation.patch` records the source changes; the new CLI is separately visible.

## Stronger confirmation and failure clusters

Each confirmation has a 300-second algorithm allowance, compared with Main's
60-second initial replay. The unchanged Landlock/seccomp launcher runs each
program on a separate pinned CPU, with 1 GiB memory and writable scratch only.
Its outer CPU/wall watchdog is slightly larger for startup. A process timeout,
exception exit, malformed result or index bug is not a selectable failure.
Normal-exit residuals and elapsed times are stored per case; the budget need not
be consumed if the algorithm finishes its stages. Solved cases are excluded.

Four scientific failure clusters are retained, two cases each:

- Crowded singlets: closely spaced scalar columns with strongly correlated
  leading-radial responses; sparse rank-one completion remains inaccurate.
- Spin aliases: forward angular probes reduce separation of different partial
  waves, leaving coupled support/OPE ambiguities for the replay.
- Mixed cancellation: opposite off-diagonal OPE products can cancel while
  diagonal PSD contributions remain positive.
- Weak residues: small but constrained rank-one atoms coexist with larger ones;
  the shared coefficient and residual condition still apply.

All candidates retain the same leading-radial/Legendre surrogate, 96 normalized
columns and 40 probes, with a 10- or 12-atom cap and 36 crowded scalar columns.
These are not full conformal blocks. No numerical contract or acceptance
threshold changes: every certificate must satisfy the original checker, with
core=1 and worst-family=1 required. Any valid completion is accepted, not only the
planted support. The builder independently reconstructs the radial kernels and
checks certificate sums at 80 decimal digits, plus malformed/omission controls.

## Limits of the evidence

Resistance means failure of this documented generalized replay at its measured
budget; it is not proof of intrinsic hardness or resistance to all algorithms.
Planted certificates prove feasibility of the finite certificate instances, not
a fast input-only method for recovering them. The unchanged public and hidden
checkers, independent arithmetic and private certificates provide evaluator
evidence. Main owns the fresh generation-two tournament; this sidecar launches
no agents and makes no fresh-v2 success claim.
