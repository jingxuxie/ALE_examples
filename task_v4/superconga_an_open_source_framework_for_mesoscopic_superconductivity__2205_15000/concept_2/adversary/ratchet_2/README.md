# Final champion ratchet: generation 2 -> generation 3

Write scope is this directory only. The live participant/evaluator, the running
replicate's assets, and all champion source/research/archive files remain intact.
No agents are launched. `protected_hashes.json` and `hash_audit.json` audit this.

## Algorithm, not a static layout

The input champion is the fresh generation-2 agent's **construction/research
algorithm**. Its final submission retained `design.json`, construction sources,
and research outputs; only generation 1 cleaned down to `design.json`.
Top-level and `research/` versions of `optimize.py`,
`continuation.py`, and `discrete.py` were compared and are identical.

The transcript shows that its successful branch is NOT generation 1's strategy:

- Eigenbasis analytic objective gradients; linear, logarithmic, and square-root
  residual modes.
- SLSQP with an exact equality constraint on the normal-site count.
- Binary penalty weights `.02, .1, .3, 1, 3, 10`, each with `maxiter=250` and
  `ftol=1e-9`, using seeds 0..47 and the original `seed+937` initializations.
- Original seed 7 recovers the exact witness at stage 1. This sidecar reproduces
  that success against the archived generation-2 public problem.
- Earlier branches were eight L-BFGS runs (450 iterations), eight warm
  least-squares runs (300 evaluations, count/binary weights 10/1), and eight cold
  least-squares runs (350 evaluations, same weights). These are additionally
  run on the primary finalist with the original seeds/modes and initialization.
- `discrete.py` was independently tested during the original attempt, but did
  not produce its successful artifact. Its low-rank helper is ported and
  numerically verified here, not misrepresented as the successful strategy.

`adapter.py` executes the frozen research source in memory. Adaptations are
dynamic candidate/budget dimensions, explicit ASSETS/OUTPUT paths, and the
discrete helper's onsite literal 6 -> the configured pin potential. Eight
physical neighbors and rank-eight swap updates remain unchanged. The original
SLSQP objective, penalty sequence, equality, tolerances, and seed logic remain
unchanged. The successful continuation worker itself is invoked, with a
noninvasive `minimize` wrapper recording independently scored stage results.

## Physics and feasibility

The full factorial covers widths 14/16/18/20, V=3.2/6, and eta=.01/.02, with
candidate counts 96/144/192/256 and budgets 36/54/72/96. Exactly 3/8 of candidate
sites are normal in every case. To make this fraction integral at widths 14/18,
the four interior candidate corners are fixed superconducting. All candidates
retain the original two-site exterior margin and eight physical neighbors.

Targets use the same open-boundary prescribed chiral-gap BdG model and operating
conditions as generation 2. Uniform energy sampling on [-.3,.3] has step eta/2,
giving at least four samples per Lorentzian FWHM. No eigenvalue-dependent point
selection or shifted/hidden energy grid is used.

The private masks are first-feasible correlated metallic-island fields, generated
by a fixed recipe before any fits (sigma=.65 lattice units, seed 823701+trial),
and accepted solely for exact budget and connected superconducting complement.
Each geometry uses the same witness across all potential/linewidth pairs. The
16x16 primary has 54 normal sites in eight components, rather than one simple U
cavity. Its mask is trial zero, not selected for defeating this optimizer.

The 16x16, V6, eta=.01 primary was declared before fitting. It increases design
dimension to 144 without relying on the largest 18/20 matrices. Two new 12x12
many-island controls supplement the exact archived gen2 control; one receives
the full 48-seed continuation portfolio. This distinguishes geometry/pattern
effects empirically rather than assuming every failure is caused by size.

## Strength, progress, and interpretation

- Broad screening: three seeds (0,1,2), all six original stages, maxiter80.
  These are explicitly lower-budget screens, not full-strength hardness tests.
- Primary stress test: all 48 original seeds, all six stages, original maxiter250.
- Matched 12x12 stress test: the same full 48-seed continuation portfolio.
- Additional primary branches: the original L-BFGS and least-squares portfolio.

`stage_*.json` appears after each independently scored stage. `result.json`
appears only after the complete run. Thus partially running jobs are not counted
as complete failures. `summary.json` includes complete-seed identities, raw RMSE,
scores both with and without fabrication validity, CPU/wall time, and peak RSS.
`batch_*.json` records elapsed batch wall time. Aggregate worker time is not
sidecar elapsed time. All workers use one BLAS thread.

`analyze.py --freeze` refuses to certify a surviving primary unless all 48
original-strength seeds complete all six stages with no passing artifact and
independent checks pass. Additional L-BFGS/least-squares and large-grid jobs may
still be running; their completeness is visible in the per-run records. A
pending branch must never be described as a completed failure.

All witnesses pass matrix, Hermiticity, particle-hole, direct-resolvent LDOS,
independent checker, and finite-difference objective-gradient tests. The primary
also passes all-mode least-squares-Jacobian/gradient consistency, low-rank swap
consistency, and the unchanged original evaluator in a private mirror. Final
diagnostics rescore the best valid blind pattern on 2x and 4x finer grids.

Frozen thresholds remain **.96 core / .94 worst**, with the original 120-second
checker limit. Any surviving candidate is only a finite-portfolio failure, not
proof of hardness. The parent launches the final fresh one-hour attempt.

## Commands

Run from the task root with NumPy/SciPy available:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_2/experiment.py generate --workers 19
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_2/experiment.py run --iterations 80 --workers 54
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_2/experiment.py run --cases generation_2_control --seeds 0 1 2 7 --iterations 250 --workers 4
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_2/experiment.py run --cases islands16_v6_eta0.01 --seed-count 48 --iterations 250 --workers 48
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_2/experiment.py run --cases islands12_v6_eta0.01 --seed-count 48 --iterations 250 --workers 48
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_2/experiment.py auxiliary --cases islands16_v6_eta0.01 --workers 16
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_2/analyze.py islands16_v6_eta0.01
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_2/analyze.py islands16_v6_eta0.01 --freeze
```

Completed jobs are skipped on rerun. Do not regenerate or edit the frozen packet
while the parent is launching the next generation.
