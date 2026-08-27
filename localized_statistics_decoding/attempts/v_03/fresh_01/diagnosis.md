# Decoder repair: diagnosis, experiments, and final validation

## Result and interpretation

The submitted `solve.py` recovers **20/20 small and 20/20 large public frames**,
with **100% syndrome consistency on both networks**. The original repair
recovers **0/20 on each**, despite also satisfying every syndrome. The public
score changes from 0.15 to 1.00 on each network.

These are curated failures. These recovery fractions are diagnostic results on
this corpus, **not physical error rates, thresholds, or unbiased channel
performance estimates**. The independent synthetic experiments below are
engineering checks, not evidence about the hidden corpus.

| Public network | Method | Logical recovery | Valid syndromes | Mean original-prior cost | Mean mechanism weight |
|---|---|---:|---:|---:|---:|
| Small | Shipped repair | 0/20 | 20/20 | 50.9165925994 | 12.15 |
| Small | Final decoder | 20/20 | 20/20 | 23.1506358227 | 5.80 |
| Large | Shipped repair | 0/20 | 20/20 | 105.4078674335 | 26.50 |
| Large | Final decoder | 20/20 | 20/20 | 55.8083099185 | 14.60 |

Costs in this table are calculated by the supplied validator using
`sum(c * log((1-prior)/prior))`, not by interpreting frontend diagnostics as
probabilities. Final predictions are in `validation_small_predictions.npz` and
`validation_large_predictions.npz`. Actual validator output and CLI invocations
are preserved in `validation_cli.log`; measurements are in
`validation_metrics.json` and `baseline_metrics.json`.

## What was wrong with the prototype

The prototype sorts the frontend's signed diagnostic values, constructs one
independent column basis, and solves the syndrome in that basis. It never
compares alternate affine solutions using the true channel probabilities. It
does not perform posterior hard decisions on nonbasis mechanisms or search
neighboring logical sectors. Gaussian elimination establishes consistency, not
logical recovery.

The public detector matrices have dimensions 72 by 216 and 144 by 432, but GF(2)
ranks only **60 and 132**, respectively. Their columns have degrees three or six;
each row has degree twelve. The frontend values reach approximately
plus/minus 1.5e10 and 1.6e10. I did not infer true fault probabilities from these
heuristic values, and the final decoder deliberately ignores them.

A consequential structural discovery was that every public mechanism belongs to
a disjoint triple `(a,b,c)` with both `H_c = H_a XOR H_b` and
`L_c = L_a XOR L_b`. There are 72 and 144 such triples. Therefore toggling all
three mechanisms is both detector-neutral and logical-neutral. Representing
the three independent mechanisms as three independent Tanner variables hides
an exact, useful degeneracy.

## Actual development experiments

All entries below used the real public logical labels for evaluation only.
They are recorded in `experiments.json`, `experiments.log`, `diversity.json`,
and `diversity.log`; prediction artifacts for the ablations are also retained.

| Experiment | Small recovery | Large recovery | Small / large elapsed seconds |
|---|---:|---:|---:|
| Prior-ranked binary elimination, no search or BP | 0/20 | 0/20 | 0.007 / 0.007 |
| Grouped prior-only single/pair kernel search | 5/20 | 2/20 | 0.004 / 0.010 |
| One binary BP restart plus search | 15/20 | 18/20 | 0.028 / 0.104 |
| One grouped BP restart plus search | 19/20 | 20/20 | 0.014 / 0.044 |
| Forty grouped restarts, OSD order zero only | 20/20 | 19/20 | 0.502 / 2.296 |
| 256 grouped sum-product restarts plus search | 20/20 | 20/20 | 4.234 / 19.030 |
| Forty independent-check-basis restarts plus search | 20/20 | 20/20 | 0.989 / 3.252 |
| Forty normalized min-sum restarts plus search | 20/20 | 20/20 | 0.459 / 1.875 |
| Final mixed 256-restart configuration | 20/20 | 20/20 | 4.394 / 16.377 |

The initial forty-restart binary and grouped implementations both reached full
public recovery. Grouping reduced large-network inference CPU time from about
4.54 seconds to 2.44 seconds in those initial runs. Their wall times were not
used for final budget conclusions because some initial runs overlapped.

The failed prior-only variants show that merely replacing the ranking by channel
priors is insufficient. The single-restart and order-zero results separately
justify inference diversity and nontrivial candidate search. A near-equal mean
candidate cost can still conceal an incorrect logical sector: the order-zero
large result costs 55.8173061911 versus the final 55.8083099185, but misses one
frame. Logical labels, rather than cost alone, selected the final design.

The final mixture retains sum-product, normalized min-sum, and randomized
independent-check bases. Each individually works well on the public data;
the mixture provides bounded diversity without choosing a single factorization
on the basis of these forty labels. It also matched sum-product recovery in
the two larger synthetic batches and was faster in the lower-prior batch.

## Final algorithm

1. **Exact reduction of equivalent mechanisms.** Mechanisms with identical
   detector AND logical columns are merged by parity. Their effective probability
   is `(1-product(1-2*p_j))/2`. An odd correction is expanded to the original
   member with the lowest independent-mechanism cost. Identical detector rows
   are deduplicated; their observations are not treated as extra evidence.

2. **Exact four-state variables where justified.** A disjoint triple is combined
   only after testing the detector and logical identities above. The four states
   are `x=e_a XOR e_c`, `z=e_b XOR e_c`. Each state's probability is the sum of
   the probabilities of its two original three-bit representations. Ungrouped
   mechanisms remain binary variables, so absence of this structure is allowed.
   A check connects to a group's `x`, `z`, or `x XOR z`, as determined by the
   supplied matrix, not by an assumed geometry or mechanism order.

3. **Bounded, diverse inference.** At most 256 restarts, each with at most 80
   iterations, use grouped variable-to-check marginal messages. The first run
   uses the unperturbed true prior. Later runs vary prior temperature, Gaussian
   state-energy perturbations, damping, and check-update approximation. One
   quarter uses a randomized sparse-first independent subset of the original
   checks; another quarter uses normalized min-sum. The remaining runs use
   sum-product on all distinct original checks. All constraints remain present
   in candidate validation and Gaussian elimination. Redundant constraints are
   never counted as independent channel observations.

4. **Rank-aware affine candidate search.** The least-reliable marginal bits are
   offered first as elimination pivots, while joint posterior hard decisions
   supply nonpivot values. Bit-packed GF(2) elimination computes an exact
   syndrome solution and kernel vectors. Search considers every single kernel
   move, all pairs among up to sixty moves selected by single-move candidate
   cost, and up to three greedy kernel-improvement sweeps. Best-residual and
   final-iteration inference states supply different bases. No assumption that
   row count equals rank is made, and no full affine-space enumeration is used.

5. **Probability-based selection and expansion.** All valid candidates are
   compared under the original, unperturbed, grouped probabilities. Perturbed
   priors affect proposals, not final scoring. The score sums
   `-log(P_group(state)/P_group(0))`, exactly integrating the local redundant
   representations that were merged. Each selected group state uses a
   minimum-cost representative under the reduced mechanism priors; merged
   parity bits then expand to their cheapest original member. A final multiplication by
   the ORIGINAL `H` checks every syndrome before the NPZ is written.

The solver uses `L` solely to certify that reductions preserve logical effects;
it does not receive or access target logical labels. It never loads development
labels or any public input by a hardcoded path. All deployment information comes
from the five arrays in the requested input NPZ.

## Runtime and resource validation

The exact final required CLI was run with CPU affinity restricted to one core,
a 1.5-GiB address-space limit, and a 60-second subprocess timeout. The native
library was deleted before the small run to exercise runtime compilation.

| Final CLI case | Frames | Wall seconds | User CPU seconds | Peak RSS KiB |
|---|---:|---:|---:|---:|
| Public small, including cold compilation | 20 | 7.02 | 6.71 | 187300 |
| Public large, compiled library present | 20 | 17.72 | 17.66 | 34396 |
| 864-mechanism synthetic batch, prior scale 1.6 | 24 | 33.94 | 33.90 | 35140 |

`benchmark.py` reproduces these checks and additionally runs a 24-frame,
864-mechanism synthetic batch. Its exact results are stored in
`validation_metrics.json`, `bounded_synthetic_runtime.json`, and
`validation_cli.log`. The cold-compile memory peak includes the compiler; the
inference-only process is much smaller. No SciPy or external decoding package
is required: runtime uses NumPy, the standard library, and local C++17 source.

The native frame deadline is `min(1.85, 46/frames)` seconds, checked between
restarts. For 24 frames this allocates 44.4 seconds to search, with room for
loading, preparation, compilation, and a final restart's possible overshoot.
This is a practical bounded-search policy rather than a hard real-time proof.
OpenMP, MKL, and OpenBLAS thread counts are set to one before importing NumPy.

## Additional robustness evidence

`stress.py` forms two disconnected copies of the large public matrix, yielding
288 detector rows and 864 mechanisms, and uses new independently sampled faults,
perturbed heterogeneous priors, and row/column permutations. Two prior scales,
1.0 and 1.6, were tested. Frames were retained only when the shipped repair was
logically wrong and the sampled physical fault itself supplied a strictly
lower-cost correct-sector witness. The synthetic soft rankings are noisy priors,
NOT replays of the unavailable frontend, so this is not a reproduction of the
hidden distribution. Both sum-product and mixed inference recover **24/24 at
each scale**, with full syndrome consistency. Mixed elapsed times were 14.885
and 33.036 seconds. See `stress_results.json` and `stress.log`.

`invariance_checks.py` separately reports:

- Random row and mechanism permutation of the public large batch: 20/20,
  16.670 seconds.
- Every mechanism split into two equivalent independent mechanisms with
  appropriately adjusted priors, and every detector row duplicated: 288 by 864,
  20/20, 17.431 seconds. The higher original-mechanism cost in this case is
  expected because splitting changes the individual mechanism priors.
- A freshly generated, non-quantum random sparse binary matrix with column
  degrees 3, 4, and 5, 288 by 864, and eight random logical maps: 24/24,
  24.974 seconds. It has no usable triple grouping (864 binary groups), exercising
  the generic fallback rather than the public geometry.

These engineering checks and their actual metrics are preserved in
`invariance_results.json` and `invariance.log`. They do not establish a physical
quantum-code threshold or guarantee generalization to a different topology.

## Files, reproduction, and limitations

The runtime deliverables are `solve.py`, `decoder.cpp`, and the built
`decoder.so`. The library is rebuilt locally if missing or older than the source.
`repair.py`, `baseline_solve.py`, and `validate.py` are unmodified copies of the
starter modules for development reproduction. Other scripts and prediction
files document experiments; the runtime imports none of them.

Required invocation, from any working directory:

```
python /path/to/submission/solve.py --input /absolute/path/batch.npz --output /absolute/path/predictions.npz
```

Each prediction NPZ contains `correction` in original frame/mechanism order,
`groups`, and a numeric `diagnostics` array. Diagnostic columns are grouped
candidate energy, restart count, number of syndrome-valid BP iterations,
native elapsed seconds, and number of best-candidate improvements. Diagnostic
energy is not the validator's original-mechanism cost. Environment variables
prefixed `DECODER_` expose development ablations; default settings define the
submission and do not need any environment configuration.

This is an approximate decoder, not an optimum certificate. Exact integration
covers duplicate mechanisms and detected neutral triples, not the entire
quantum stabilizer space or every logical-sector partition function. High-noise,
high-degree, or unusual degeneracy structures can defeat both BP proposals and
limited-order affine search. At larger sizes some frames may stop at their time
budget before exhausting the restart cap. Public success and the synthetic
checks are encouraging but cannot prove the hidden-batch target. The original
task and public input files were not modified.
