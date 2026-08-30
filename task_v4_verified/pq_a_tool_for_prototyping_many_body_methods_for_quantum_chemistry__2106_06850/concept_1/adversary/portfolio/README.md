# Private privileged contraction-planning portfolio

**Follow-up completeness audit:** `RESPONSE_COMPLETENESS_AUDIT.md` supersedes the
initial “unknown” assessment. Unpruned, independently enumerated response graphs
and optimizer-free integer certificate checks prove that the frozen response
family cannot meet 1.15×. The concept is infeasible under its current validator
and cases, not merely difficult. Run `python -S response_completeness.py
--verify-only` from this directory to repeat the checks.

This sidecar reads only the participant contract/baseline and hidden cases/source
families. It does not inspect participant attempts or modify the evaluator,
manifest, participant, or any file outside this directory. The fixed targets
remain 1.75 overall and 1.15 for every family.

Search artifacts are privileged optimization evidence, not a fresh participant
attempt. Offline generation may exceed the 30-second participant limit; reports
distinguish generation time from certificate replay and validation time. Failure
to find a passing portfolio means unknown, not impossible.

## Results and reproduction

Start with `SUMMARY.md`, `best/summary.json`, and `per_case_scores.csv`.
The CSV contains exact integer arithmetic/peak counts and separate offline
generation, cold fresh-planner, and specialized replay timings for every case.

Run these commands from this directory. Keep all output arguments here.

```sh
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python solve.py ../../evaluator/hidden/left_density_0.json local.plan.json --delayed --report local.search.json
python ../../participant/workspace/contract.py ../../evaluator/hidden/left_density_0.json local.plan.json
python replay.py ../../evaluator/hidden/left_density_0.json local.replay.json
python certificate.py ../../evaluator/hidden/left_density_0.json best/left_density_0.bound.json
python run_portfolio.py --output rerun --seconds 20 --trials 16 --delayed --exhaust-trials
```

`solve.py` performs fresh optimization using the input, not a lookup table.
`replay.py` deliberately performs exact-input privileged certificate lookup and
validates the loaded plan; it refuses unknown inputs. It is not represented as a
general solver or participant attempt. Both use the exact supplied contract.
The solver imports the supplied baseline only for the independently optimized
initial incumbent and memory-safe fallback.

Only the standard library and the installed NumPy/SciPy are used. No packages
were downloaded. The LP branch-and-bound implementation supports the local
SciPy 1.8 environment, which lacks a public `milp` entry point.

## Search model

`graph.py` enumerates all term subsets and binary partitions. Canonicalization
permits dummy-index renaming, identical-factor permutation, and free-axis
reordering, but no tensor symmetry, addition, numerical factorization, or zero
assumption. The expanded graph additionally retains arbitrary subsets of
otherwise summed internal indices, subject to necessary allocation bounds.

`optimize.py` solves a global AND/OR problem: a selected subnetwork chooses one
binary decomposition, selected operations require their non-input children, and
all distinct requested roots are selected. The objective charges each selected
operation once. This is a lower relaxation of scheduling because arbitrary live
cache lifetimes are not constrained. Necessary parent-plus-operand allocation
bounds are enforced. LP branch-and-bound and multi-root coordinate/reweighted
tree search explore joint choices, not only fixed independent trees.

`schedule.py` makes real declarative plans. It uses five root-order strategies,
four eviction policies, pinned operands, last-use cleanup, recomputation, and
an exact Pareto-baseline fallback when a selected tree cannot fit. Every
generated candidate is checked by `contract.validate`, including candidates
that are not retained as the winner. Stochastic multi-root restarts are forced
in the `deep/` run even when the numerical joint optimum is already attained.

## Certificates and audits

`certificate.py` checks integer Lagrangian lower bounds for the enumerated
global graph. If binary-edge variables lie in `[0,1]`, arbitrary signed integer
multipliers for valid constraints give
`constant + sum(min(0, reduced_cost))` as a valid lower bound. Equality
multipliers are unrestricted; inequality multipliers are nonpositive.
The checker rebuilds the graph, checks the exact input hash and allowed edges,
and performs the bound arithmetic with Python integers. Expensive omitted edges
are handled by capping the certificate at the edge-cost cutoff. No floating
point tolerance is needed to check these saved root LP certificates.

Numerically closed branch-and-bound results and exact integer-checked root LP
bounds are reported separately. Bounds are explicitly scoped to the enumerated
graph model. Completeness of that model is not asserted as a universal theorem
about every legal interface plan; no impossibility claim is made.

`verify.py` recomputes all frozen baselines, checks the saved plans and integer
certificates in a fresh process, compares independent graph optima with the
baseline, and verifies individual graph operations as exact contraction plans.
Its optional cold solver checks impose a 30-second wall timeout, a 2 GiB address
space, and one BLAS thread. These are local resource-limited checks, not the
evaluator's bubblewrap sandbox. The planner's internal search-time argument is
a search budget, not a universal hard runtime guarantee.

The separate `verification_fallback/` audit deliberately selects oversized
trees and validates 24 resulting plans through 1,003 exact-baseline fallback
events. The optimization runs exercise caching and recomputation without
needing that fallback on their winners.

`challenge.py` creates separately labeled private cases from the supplied
`hidden/source_terms.json`, with random and reuse-rich selections, varied
orbital aspect ratios and caps, and no duplicated source record within a case.
These diagnostics neither replace the original hidden set nor alter its fixed
target. Full source pools are used only to rank selections; emitted challenge
batches stay within the stated 20–80-term range.

`finalize.py` combines only valid private runs, independently rechecks winners,
benchmarks specialized replay, and regenerates the summary, CSV, and input
provenance hashes. It requires the `ordinary/`, `expanded/`, `deep/`,
`verification/`, `verification_full/`, and `challenge/results/` artifacts.
It also requires the targeted `verification_fallback/` report.
