# Anti-compression audit

## Two separate requirements

1. **Conditional structure and parameter recovery.** Inputs contain shuffled
   local probability tables with candidate supersets, not factor potentials,
   a true edge list, a generator seed, or reference outputs. A contraction
   engine accepting given factors cannot directly consume these tables as a
   joint model. Local ratios, conditioning/axis semantics and interaction-order
   recovery are required. An alternative correct learner need not use CMI.
2. **Scale-aware global inference.** The learned distribution must be summed
   over approximately 100 bits, including loops/three-body branches, changing
   global activities, cardinality intervals, parity masks and pinned events.
   Learning every coefficient does not by itself supply these normalized
   probabilities. A logarithmic count/parity elimination semiring is the
   reference's choice; equivalent stable bounded-width methods are welcome.

These are separable implementation requirements, not a claim of computational
intractability or a theorem that generic algorithms cannot solve the task.
The first requirement is deliberately noise-free in this minimal pilot.

## Controlled evidence

`audit.py` compares the source-grounded CMI port against entropy computed by
independent bit-enumerated marginals, including unequal X/Y block cardinalities.
It also checks mediated dependence and a pure three-bit synergy example with
vanishing pairwise MI. Six tiny models are fully enumerated (1,024--4,096 states)
to independently check all local tables, recovered coefficients, global
normalization, masks, parity, fixed-bit counting and both contraction engines.

The author oracle uses known-order forward frontier summation directly from
hidden monomial energies. The executable reference independently reconstructs
from visible input and uses min-fill bucket elimination with log-polynomial
messages. It cannot read hidden inputs or targets under the evaluator's staged
filesystem permissions. The shared sandbox is an external author dependency;
only the staged single-file submission directory is passed as readable, never
the original `private/reference/` directory.

`audit.json` contains every case's ablations, exact errors, underflow counts,
monotone score interpolation and six fresh seed/region checks. Initial results:

| Method | Chain | Ladder | Triple branches |
| --- | ---: | ---: | ---: |
| Exact visible-input reference | 1.000 | 1.000 | 1.000 |
| Independent bits | about 0.202 | about 0.202 | about 0.201 |
| Canonical pair truncation | 1.000 | 1.000 | about 0.201 |
| Pair-MI spanning tree | 1.000 | about 0.676 | about 0.725 |
| Correct factors, ignore activity | about 0.221 | about 0.237 | about 0.257 |
| Correct targets, ordinary-probability floor | about 0.807 | about 0.829 | about 0.862 |

The table averages core and challenge within each family. Pair truncation is
not a claim about a best possible pairwise statistical fit. The probability
floor is a numerical ablation of correct answers, not a complete competing
solver. Neither is claimed to reproduce errors in the later experimental paper.

## Leakage, identity and ratchet controls

- Participant exposure is only `TASK.md`, `input/FORMAT.md`, one unlabeled
  nine-variable NPZ, and two incomplete workspace files. There is no working
  global solver, factor table, hidden graph, target, baseline prediction or
  generator in that tree. The learner sees candidates, not active factor edges.
- Every scored event excludes the all-zero pattern. No identity probability,
  sparse structural zero, or table-reconstruction accuracy contributes to the
  score. All three event groups and all three families receive equal weight.
- The score has no tolerance pass/fail plateau or clipping to one below a
  positive error threshold. The baseline is roughly 0.2 by design, not an
  implicit zero. Score interpolation is checked at seven accuracies; absolute
  log errors are retained privately as an additional scientific check.
- Seeds and regions regenerate latent coefficients, relabelings, local axes,
  events and activity shifts. The generator aborts if a proposed case's weak
  baseline separation is below 0.15 log units rather than silently padding the
  pool with an uninformative event; use another seed if this guard ever fires.
- A local-factor learner plus generic contraction is a legitimate solution,
  not an attack. Fixed filenames/output memorization, an independent model,
  pairwise-tree restriction and ordinary-probability flooring do not solve all
  held-out families. The main author's isolated attempts determine whether the
  pilot is sufficiently challenging; the current audit alone does not.
