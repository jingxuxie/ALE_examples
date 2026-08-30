# Private circuit-loss feasibility evidence

Both requested targets are constructively feasible. **Different designs** solve
the single-loss and two-loss objectives. This is a private generation-time
feasibility study, not a fresh-agent attempt or a hardness decision. No runner
was invoked, no fresh-agent artifacts were read, and all new files are confined
to this `resilience/` directory. The original passing design, its audits, and
all participant/evaluator/task files remain intact.

## Fixed objective and reference

`contract.json` freezes the requested targets and hashes of the original
reference design and benchmark. For each operating point, remove all batches
of each selected circuit, or each pair of selected circuits, and take the
**maximum A-risk at that point before averaging operating points**. There is
no reallocation after loss. The twelve scaled gate parameters retain both
unknown readout nuisance parameters in the full 14-by-14 inverse.

The original privileged reference has hidden-set mean intact risk
4.501737696154136, mean pointwise worst-single-loss risk 11.253527501772503,
and mean pointwise worst-pair-loss risk 123.09322860611013. The intact guard is
therefore 5.402085235384963 on this set. This max-before-mean objective differs
from the maximum aggregate inflation in the earlier circuit-loss audit.

Targets, fixed before search:

- Single loss: at least 25% overall and 15% in every regime.
- Two losses: at least 50% overall and 30% in every regime.
- Either objective: intact mean risk at most 1.20 times the reference;
  at most 24 circuits, at most 48 integer batches per circuit, 64 shots per
  batch, and the original 1,600,000-tick execution budget.

## Final artifacts and exact scores

`single_design.json` is the final single-loss construction;
`single_score.json` is its exact frozen-set score. `double_design.json` and
`double_score.json` are the corresponding pair-loss construction and score.
`design.json` and `score.json` are aliases of the **pair-loss** artifact and
score. `summary.json` indexes the complete evidence; `verified_summary.json`
contains all three evaluation sets and all regime scores.

| Design | Set | Overall reduction | Worst-regime reduction | Intact-risk ratio |
| --- | --- | ---: | ---: | ---: |
| Single loss | 60 frozen points | 0.3243536327202108 | 0.15097807054874335 | 1.1307737656932373 |
| Single loss | 3,000 broad points | 0.3379846891998529 | 0.23837872227726298 | 1.0745106694997046 |
| Single loss | 600 new held-out points | 0.3294964891196196 | 0.29322271591054716 | 1.0645056582941250 |
| Pair loss | 60 frozen points | 0.5559748862889700 | 0.30543015056195233 | 1.1724241843971657 |
| Pair loss | 3,000 broad points | 0.8131608781882864 | 0.30286493187743335 | 1.1429881490639240 |
| Pair loss | 600 new held-out points | 0.7647549415000678 | 0.38798643257815335 | 1.1361342942489303 |

Every row meets its own objective's fixed targets and intact guard. All designs
use 24 circuits. The final single-loss design uses 557 batches and 1,599,296
ticks; its frozen intact and loss risks are 5.090446886843411 and
7.603404975655794. The pair-loss design uses 565 batches and 1,599,872 ticks;
its frozen intact and loss risks are 5.277946146783489 and 54.65648482888587.

The pair-loss design does **not** meet the single-loss improvement target, and
the single-loss design does not meet the pair-loss target. Joint feasibility
with one design was not sought or demonstrated. A larger number of deletions
does not automatically make these relative improvement thresholds harder:
the reference is especially fragile to pairs, and its broad-set mean pair
risk is 348.6447360356279 versus a single-loss risk of 12.121727798468287.
No optimality or fresh-agent hardness claim is made.

## Generalization and numerical validation

The first frozen-only designs met the frozen targets but did not generalize
uniformly: the single-loss design improved broad anisotropic risk only 1.42%,
and the pair-loss design improved broad mixed-regime risk only 20.54%.
Those artifacts and scores remain in `best_single*`, `best_double*`,
`hidden_scores.json`, `broad_scores.json`, and `audit_summary.json`.

The bounded refinement adds 180 operating points, 30 per regime, to the 60
frozen points and searches a 29-circuit pool formed by the earlier supports.
It enforces the family and intact constraints on both groups and uses the
full 3,000-point set for selection. Thus the final broad-set results are **not
held out**. The final 600 points, generated with seed 2174495931 and 100 draws
per regime, are new and were never used for training, selection, or subsequent
tuning. Here “fresh” in filenames means new simulator draws, not a Codex agent.

All final scores explicitly invert every deletion case: 24 single losses and
276 pairs for every point and design. Woodbury calculations used during search
agree with direct inversion; all final numerical checks pass.
`numerical_checks.json` also checks analytic gradients by finite differences.
The original reference hash is checked whenever the private scorer loads.
These are deterministic finite-set scores plus independent sampling evidence,
not a guarantee over every possible operating point.

## Root-cause clusters

`hidden_root_clusters.json`, `robust_broad_root_clusters.json`, and
`fresh_root_clusters.json` contain parameter-wise covariance increases,
physical circuit descriptions, family frequencies, conditioning, and concrete
worst operating points. The principal mechanisms are:

1. **Loss of concentrated rotation-angle information.** Circuit 151 (`Y^64`,
   +X preparation, Z measurement) is the original worst single loss at 40/60
   frozen points. Pair `(151,701)` is worst at 15/60 points, with a mean
   conditional `Y_y` variance increment about 230.27. The added `YYI^64`
   experiment (90) supplies complementary sensitivity. Retaining the short
   `XXY` experiment (701) is important when decoherence suppresses long germs.

2. **Readout calibration versus decay-rate confounding.** Losing a short
   calibration reference creates correlated uncertainty in multiple decay
   rates. The single-loss construction includes complementary short circuits
   13 and 30 rather than relying on the original positive-response reference.
   This interpretation is consistent with the earlier known-readout
   counterfactual and the measured covariance-increment directions.

3. **Two-circuit bottlenecks in decay-rate identification.** Original pair
   `(59,69)` is worst at 20/60 points and predominantly increases X decay-rate
   uncertainty; `(278,463)` is worst at 19/60 points and predominantly increases
   Y decay-rate uncertainty. Their mean conditional increments are about
   77.90 and 78.61, respectively. Pair-resilient allocation reduces these
   bottlenecks while allowing a controlled intact-risk increase.

4. **Regime-dependent redundancy.** A duplicate sensitivity supplied only by
   a long, strongly attenuated germ is not reliable under anisotropic noise.
   Mixed coherent errors also change which decay-rate directions are weak.
   The broad audit exposed both effects; broader training and short-circuit
   redundancy repaired the observed family failures.

These mechanism descriptions are inferences from the physical model,
covariance decompositions, and support changes, not laboratory experiments.

## Reproduction

From `concept_1/`, using the installed NumPy/SciPy interpreter:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
/usr/bin/python adversary/portfolio/resilience/search.py --seconds 300
/usr/bin/python adversary/portfolio/resilience/audit.py --per-family 500
/usr/bin/python adversary/portfolio/resilience/refine.py --seconds 330 --per-family 30
/usr/bin/python adversary/portfolio/resilience/verify_refined.py --fresh-per-family 100
/usr/bin/python adversary/portfolio/resilience/metrics.py --submission adversary/portfolio/resilience/single_design.json
/usr/bin/python adversary/portfolio/resilience/metrics.py --submission adversary/portfolio/resilience/double_design.json
```

The search uses constrained continuous allocation, analytic outage-risk
gradients, sparse add/drop exchanges, integer batch allocation, and
family-specific constraints. It warm-starts from existing first-stage files.
Logs are `run.log`, `constrained_run.log`, `search.jsonl`, `refinement.jsonl`,
`audit_run.log`, and `verification_run.log`. Running the pipeline again can
replace files inside this new directory, but never writes the original parent
design or any participant/evaluator/task assets.
