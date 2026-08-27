# Scientific diagnosis and validation

## Defects established before replacement

The original probability adapter assigns a point logical label to one fault
hypothesis per mode. It neither sums degenerate fault configurations nor computes
their conditional probabilities. The regional solver assigns a crossing mechanism
to its first detector's region, omitting its effects elsewhere; region ownership
is not an independence assumption. Silent mechanisms are never activated. The
binary solver also ignores contradictory dependent rows, and erasures are
incorrectly converted into observed zeros. Sorting pivot columns by probability
and setting all free variables to zero is not a posterior calculation.

The adapter keeps the prior mode weights for every shot and multiplies
separately mode-marginalized shot likelihoods. This resamples the mode between
shots instead of conditioning one shared mode on the whole batch. Its evidence
uses only selected configurations, with an artificial positive floor even for
impossible support.

These are measured failures, not just architectural objections. The original
solver was copied into this workspace and run before replacement. Its unchanged
public version was also rerun to save reproducible baseline reports.

| Validation case / implementation | Maximum logical TV | Maximum query error | Absolute log-evidence error | Mode TV |
|---|---:|---:|---:|---:|
| regional_ring / starter | 0.766090 | 0.602256 | 26.510523 | 0.546635 |
| regional_ring / replacement | 9.94e-16 | 1.22e-15 | 1.42e-14 | 1.82e-16 |
| masked_ladder / starter | 0.747521 | 0.498648 | 73.115252 | 0.749370 |
| masked_ladder / replacement | 1.56e-15 | 1.49e-15 | 0 | 0 |

Across the three micro cases, the starter's worst logical TV was 0.620772 and
worst query error 0.618977. Replacement errors are below 4e-16 for logical TV
and 3e-16 for queries. Full per-case results are saved in `micro_report.json`,
`validation_report.json`, and the corresponding `baseline_*_report.json` files.

## Replacement algorithm

`solve.py` provides the required CLI and forces single-threaded numerical
libraries. `inference.py` handles modes and joint outputs; `posterior.py` performs
exact regional sums and boundary tensor contraction. The runtime uses only the
standard library and NumPy; no reference data are loaded by the decoder.

For each region and observed-row pattern, GF(2) elimination keeps both the
independent equations and the dependent-row consistency constraints on crossing
faults. Erased rows are absent. Conditional on each boundary assignment, the
local calculation sums all compatible independent mechanisms. It chooses between
affine-nullspace enumeration and a dynamic program on independent syndrome
coordinates, so low local rank does not force large nullspace enumeration.
Locally unobserved and detector-free mechanisms contribute exact independent
parity factors, including their logical effects.

Each local tensor contains the evidence channel, all logical Walsh characters,
and the requested query characters. A character is the expectation of
`(-1)**parity`, not a hard prediction. Boundary Bernoulli weights and characters
are included exactly once. An optimized binary contraction tree sums shared
boundary variables, retaining hyperedges until their last participating region.
This supports loops, arbitrary hardware labels, and mechanisms touching more
than two regions. Channels are chunked to limit intermediate memory; only queries
needed by the current shot are contracted.

If `Z[t,z]` is shot evidence at a mode, the mode log weight is
`log(prior[z]) + sum_t log(Z[t,z])`. Normalizing these weights gives the shared
batch posterior. Each shot's conditional characters are mixed with those same
weights. An inverse Walsh transform gives the **joint** logical distribution;
each query probability is `(1 - character)/2`. Local and contraction scales are
tracked logarithmically. Unsupported modes have zero weight, without likelihood
floors. Only roundoff-scale output negatives are clipped and normalized.

## Commands and additional checks

Commands were run from this output directory; the available filesystem uses the
`/srv/home` prefix:

```bash
P=/srv/home/xuandong/mnt/jingxu/ALE/tasks_v2/localized_statistics_decoding/participant/v_01
python "$P/software/solve.py" --input "$P/input/validation.json" --output "$PWD/baseline_validation_predictions.json"
python validate.py --expected "$P/input/validation_expected.json" --actual baseline_validation_predictions.json
python solve.py --input "$P/input/micro.json" --output "$PWD/micro_predictions.json"
python validate.py --expected "$P/input/micro_expected.json" --actual micro_predictions.json
python solve.py --input "$P/input/validation.json" --output "$PWD/validation_predictions.json"
python validate.py --expected "$P/input/validation_expected.json" --actual validation_predictions.json
python diagnostic_tests.py --random-cases 250 --public-input "$P/input/validation.json" --report diagnostic_report.json
```

The independent exhaustive checker covers 250 seeded small networks with
duplicate supports, arbitrary logical masks, multiregion hyperedges, missing
checks, zero/one fault rates, zero prior weights, and shot-specific parity
queries. Worst errors: logical TV 1.89e-15, query 3.89e-15, log evidence
5.64e-15, mode TV 2.29e-15. Twenty direct comparisons of the two local summation
methods have maximum absolute error 5.56e-17. Permuting detectors and mechanisms
and relabeling hardware regions preserves public answers to floating-point
precision. Directed tests cover empty networks, empty queries, no faults, silent
faults, and modes excluded by different shots. A batch with log evidence
-16579.30581673768 remains finite, with 7.28e-12 absolute error; its ordinary
probability would underflow. Results are saved in `diagnostic_report.json`.

Resource checks use generated inputs, not accuracy references:

```bash
ulimit -v 1572864
/usr/bin/time -f 'elapsed=%e peak_kib=%M' timeout 60s python solve.py --input "$PWD/stress_input.json" --output "$PWD/stress_predictions.json"
for variant in dense_16 hyper_16 ring_1; do
  /usr/bin/time -f 'elapsed=%e peak_kib=%M' timeout 60s python solve.py --input "$PWD/stress_${variant}_input.json" --output "$PWD/stress_${variant}_predictions.json"
done
```

The generator is `stress_case` in `diagnostic_tests.py`: `stress_input.json` uses
seed 129, dense topology, local rank 22; the other variants use seed 142 and the
indicated topology/rank. Every stress case has ten regions, three modes, four
shots, and four logical observables. Dense cases have 320 mechanisms and 40
crossing mechanisms, eight touching each region.

| Workload | Seconds | Peak RSS (KiB) |
|---|---:|---:|
| Public micro, replacement | 0.18 | 33680 |
| Public validation, starter | 0.20 | 32168 |
| Public validation, replacement | 0.23 | 33480 |
| Dense, 220 detectors, rank 22 | 9.65 | 185824 |
| Dense, 160 detectors, rank 16 | 27.03 | 190208 |
| Three-region hyperedges, rank 16 | 5.13 | 77492 |
| Ring, rank 1 / large nullity | 0.24 | 37460 |

The dense rank-22 test initially took 23.80 seconds while contracting every
shot's query channels for every shot. Restricting contraction to the current
shot's queries reduced this to 9.65 seconds; exhaustive and public comparisons
were rerun after that revision.

The method is exact in real arithmetic, not Monte Carlo or a regional
independence approximation. Runtime remains exponential in contraction width
and the chosen local state dimension; the measurements are not a universal
runtime guarantee for all conceivable topologies or unbounded query counts.
It uses double precision, so extremely disparate conditional weights can still
underflow within a tensor despite logarithmic overall scaling. No hidden test
data or external dependencies were used.
