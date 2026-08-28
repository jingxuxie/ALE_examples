# Verdict: reject the pilot as robustly solved

No genuine counterexample was found. Stop this bounded sidecar after six fresh
large cases. The frozen solver implements a generic solution to the supplied
exact-local-marginal problem, not output memorization or a family-specific
lookup. Calling this a universal shortcut describes a legitimate algebraic
solution, not a rule violation.

## Bounded audit

The unchanged `author_tools.case` generator supplies all six predeclared cases;
only its existing seed, region, size and challenge-query arguments vary. Every
family appears once in each of regions 1 and 2. There was no adaptive case
selection, new topology/model, noisy table, altered constraint, changed score
threshold, or tighter resource limit.

| Case | Family | Region | Qubits | Seed | Frozen score | Maximum log error |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| regional_01 | mediated_chain | 1 | 100 | 482716903 | 1.000000 | 1.592e-12 |
| regional_02 | mediated_chain | 2 | 120 | 803194627 | 1.000000 | 1.364e-12 |
| regional_03 | loop_ladder | 1 | 112 | 297450183 | 1.000000 | 6.821e-13 |
| regional_04 | loop_ladder | 2 | 120 | 641829507 | 1.000000 | 1.364e-12 |
| regional_05 | branch_triples | 1 | 108 | 950362741 | 1.000000 | 2.274e-13 |
| regional_06 | branch_triples | 2 | 120 | 174836259 | 1.000000 | 1.819e-12 |

There are 18 queries per case, including event log probabilities as low as
-1391.19. Frozen mean: `0.9999999999999917`; worst family:
`0.9999999999999883`. Frozen runtime totals 2.575 seconds, with a maximum case
of 0.700 seconds. The complete audit script runs in 13.072 seconds on this run.

The separately staged visible-input author reference scores
`0.9999999999999893`, with worst family `0.9999999999999845` and maximum log
error `2.501e-12`. It independently recovers the known coefficients to within
`8.882e-15`. Targets come from the independent known-order frontier oracle,
not the frozen solver. Three additional tiny systems, one per family, validate
that oracle by exhaustive enumeration of 1,024, 1,024 and 4,096 states. These
are numerical verification checks, not extra counterexample draws.

Both solvers run through the existing evaluator's `execute` function: staged
single-file source, Landlock restrictions, 120-second wall limit, 3 GiB address
space, and the original score. All transient inputs and staging files live
inside this sidecar and are removed afterward. The participant tree, old
pools/targets, evaluator, reference files and frozen submission are unchanged,
verified by before/after hashes in `results.json`.

## Why the method generalizes

For center i, write B for its supplied envelope excluding i. The envelope
contains the complete Markov blanket. Consequently the outside-variable sum
and the global normalizer cancel in the local odds:

`g_i(b) = log p_i(1,b) - log p_i(0,b)`

`g_i(b) = sum_{S contains i} theta_S * product(b[v] for v in S without i)`.

Since the contract bounds factor order by three, this is a quadratic binary
polynomial on at most seven variables. Extra candidate neighbors do not change
that fact. The frozen `learn_interactions` applies a complete Walsh transform
to this small truth table. In spin coordinates `s_j = 2*b_j - 1`, write

`g_i = c + sum_j a_j*s_j + sum_{j<k} d_jk*s_j*s_k`.

Converting back gives unary intercept `c - sum(a) + sum(d)`, pair coefficients
`2*a_j - 2*sum_k(d_jk)`, and triple coefficients `4*d_jk`. These are precisely
the conversions implemented in the frozen code, followed by averaging repeated
estimates across centers and removing numerical zeros. It therefore recovers
both interaction structure and parameters directly. It does not need CMI, so
the historical CMI indexing defect is not an unavoidable bottleneck here.

The frozen `EliminationModel` then builds an elimination tree for the recovered
graph. Its messages carry truncated weight-polynomial coefficients and parity
states in log space. Child messages combine by count convolution and parity
XOR; local elimination sums the two bit assignments with `logaddexp`. Fixed
ones are removed from the free count/parity bookkeeping, and complementary
counts reduce work for high-weight events. A separate unconstrained log
partition at each activity supplies the global denominator. Thus ordinary
probability underflow is avoided rather than hidden by flooring.

The three existing constructions retain frontier width one or two at the new
sizes. Changing their seed, region, labels, masks or activity does not defeat
either identity above. The two intended implementation requirements remain,
but the frozen program has implemented both generically.

This is not a proof of every numerical corner of every conceivable positive
GRF: the code has a finite zero threshold and a heuristic ordering routine.
Neither yields a failure in the source-grounded regional scope tested here.
Searching unrelated pathological thresholds or inventing new constraints would
not establish a genuine failure of this pilot. No new concept or model is
proposed by this audit.

## Reproduce

From the `concept_04_graphical` root:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python private/reference/counterexample_audit/audit.py
```

Frozen submission SHA-256:
`f8fde4677aa40d049bd4900b263c988cda4f81dc4c4d3b6555d9ee07e33a8af2`.
The only added persistent files are `audit.py`, `results.json`, and this report,
all in `private/reference/counterexample_audit/`. Scientific source grounding
and the synthetic/ideal-marginal caveats remain those of the unchanged parent
reference provenance; no experimental data or unavailable code oracle is used.
