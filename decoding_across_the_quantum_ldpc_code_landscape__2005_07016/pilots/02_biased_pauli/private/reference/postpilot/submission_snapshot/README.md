# Biased Pauli decoder

Run `python solve.py --input case.npz --output answer.npz`.

The solver uses only the input archive, NumPy, and the accompanying native
library. `decoder.so` is included; if absent or older than `decoder.cpp`, the
Python entry point builds it with the installed C++17 compiler. Computation
is single-threaded. There are no downloaded dependencies or learned labels.

## Algorithm

1. Pull back all four physical Pauli probabilities through the supplied
   permutation and local Clifford maps. This preserves the complete joint
   channel, including X/Z correlations and non-self-inverse frames.
2. Decode the canonical CSS syndrome with four-state belief propagation.
   Damped min-sum, sum-product, layered schedules, max-log updates, and
   deterministic channel perturbations provide complementary candidates.
   If these fail to settle and CPU time remains, guided single-qubit
   hypotheses on uncertain variables provide additional candidates.
3. When belief propagation does not converge, use bit-packed GF(2) ordered
   statistics decoding. Each qubit's binary coordinates follow its dominant
   channel axes. Posterior reliabilities determine the elimination basis.
   The search combines all single flips, reliability/energy-ranked pairs,
   exhaustive enumeration of twelve uncertain free bits, and iterative
   refinement. Every candidate satisfies all parity equations, including
   dependent check rows.
4. Compare candidates using their original joint Pauli likelihood, with
   local stabilizer reductions. Stop early when different BP schedules
   agree. A process-CPU allowance bounds optional restarts, reserving time
   for every shot's syndrome-consistent initial solution.
5. Transform the correction back to physical coordinates and write exactly
   the two required integer arrays.

## Validation

`python validate_contract.py` checks the released examples through the real
CLI, arbitrary output extensions, all six Clifford matrices, every
single-qubit X/Y/Z error on both code sizes, and the zero syndrome. It also
checks that the logical-success test accepts stabilizer residuals but rejects
nontrivial logical residuals with zero syndrome.

`python validate.py --shots 128 --modes 22,100 --seed 54321` measures synthetic
full-block logical recovery against an independent GF(2) row-space test.
`--suite transfer` adds sector-dependent axes and heterogeneous joint
channels; `--suite hard` stresses high-rate cases. These are generated tests,
not labels for the unlabelled released examples. Mode 22 is a single-pass
comparison, and mode 100 is the default bounded ensemble.
`--suite extremes` covers the low-rate boundary and uniform canonical Z
bias. Generated per-qubit rates are clipped to the contract's [0.01, 0.16]
interval.

The native implementation uses small sparse message arrays and bit-packed
elimination matrices, well below the 4 GiB address-space limit. Its optional
search allowance is 48 process-CPU seconds, leaving headroom under the
60-second per-case limit for Python, I/O, and fallback compilation.

`python validate_resources.py --cold` runs an isolated, 256-shot CLI case
with a 58-second CPU limit and 4 GiB address-space limit, including a fresh
native build. All temporary input, output, and build files stay inside the
submission directory and are removed afterwards.

## Recorded results

The final implementation passes both released CLI smoke cases, all 3,894
single-qubit Pauli errors, zero-syndrome checks, and the independent
logical-versus-stabilizer checker tests.

All 6,400 default-decoder synthetic outputs are syndrome-consistent. Full
block logical recovery, measured separately using the generated errors, is:

| Workload | Recovered / shots |
| --- | --- |
| Standard, seed 54321, 128 shots per case | 1500 / 1536 |
| Frame/channel transfer, seed 54321, 128 per case | 1381 / 1536 |
| High-rate stress, seed 54321, 256 per case | 1438 / 3072 |
| Low-rate and Z-bias checks, seed 99997, 64 per case | 251 / 256 |

These are synthetic test results, not hidden-evaluation scores. Difficult
high-rate cases still have logical failures despite consistent syndromes.
Per-case measurements are retained in `validation_logs/`.

The isolated 256-shot cold-build test passes the 58-second CPU and 4 GiB
address-space limits: 51.169 CPU seconds including compilation, 51.573 wall
seconds, and 162576 KiB peak RSS. The largest warm-case CPU measurement in
the final quality suites is 48.032 seconds.
