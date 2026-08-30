# C1 champion–challenger review: no ratchet

Generation 2 remains solved and byte-for-byte unchanged. No generation 3 is created or ready; no fresh agent was launched.

## Fixed decision rule

The inherited thresholds remain mean gain >= 0.070, worst-family gain >= 0.057, no case regression, and all cases feasible. No new targets are proposed. Every solver replay uses the unchanged evaluator isolation: 90 s/case, four CPU cores, and 2 GiB RLIMIT_AS.

## Scores

| Suite | Champion mean | Champion worst | Weak baseline | LP-control mean / worst |
|---|---:|---:|---:|---:|
| discovery | 0.0926834664 | 0.0624725371 | 0 | 0.0921644655 / 0.0624725371 |
| heldout | 0.0942325125 | 0.0575444794 | 0 | 0.0940290180 / 0.0570543343 |
| resolved_discovery | 0.1144317517 | 0.1144317517 | 0 | 0.0000000000 / 0.0000000000 |
| resolved_heldout | 0.1154954747 | 0.1154954747 | 0 | 0.0000000000 / 0.0000000000 |

| Combined family | Champion gain | Weak baseline gain |
|---|---:|---:|
| heterogeneous_costs | 0.1412168150 | 0 |
| multiple_cones | 0.0649910781 | 0 |
| narrow_gap | 0.1009521616 | 0 |
| scenario_frustration | 0.0769042589 | 0 |

Combined champion: core_score=0.0960160784, worst_family_score=0.0649910781, runtime_seconds=679.437, resource_score=1.0. All 23 outputs are feasible; per-case runtime is 13.293–87.413 s. Full reports include reason and all requested score fields.

## Failure clustering and headroom

- Champion execution, topology/budget/admissibility, regression and suite-threshold failure clusters are empty.
- Four regimes: near-inversion narrow gaps; spatially correlated opposing-scenario acquisition errors; nonuniform integer acquisition costs; doubled-winding Dirac textures with optional second nontrivial occupied block.
- Discovery has 11 valid cases and independent held-out has 10. Two unresolved narrow-gap seeds are recovered on 16x16 meshes without changing their Hamiltonian parameters. One held-out seed with the wrong Chern sector is excluded before replay. None of these construction defects counts as hardness.
- 21 LP solves succeeded. The largest numerical upper bound on remaining improvement beyond the champion is 0.5570 percentage points of baseline-normalized gain. These are not interval-certified optimality claims.
- The simple LP control passes discovery and held-out. Its internal 35-second LP allowance expires on both refined meshes and it returns the baseline; these are control limitations, not champion failures. The champion achieves 11.443% and 11.550% gain on those same meshes within the official caps.
- No additional expensive portfolio is warranted after all champion suites pass. Existing champion outputs and the independent control constitute feasible witnesses; no cached answers are published.

## Validation and preservation

- Independent Wilson-loop scoring, candidate-frame gauge changes, baseline LP embeddings, original common-ambient-unitary test, and 64-state exhaustive enumeration pass.
- Eleven public-only dummy canary isolation checks pass, including private/sibling dummy denial, read-only input, environment cleaning, PID/network namespaces and numerical imports. No authentication files are read.
- Generation-2 participant, evaluator, frozen manifest and supporting metadata are archived in `../generation2_archive/`; all 44 archived files still match the root originals.
- Public participant, evaluator, cases, policy, root status, and frozen manifest have not been edited. All new work is confined to this private review and the requested archive.

## Replay commands

Run from concept_1. Use an escalated shell if the default sandbox hangs. Choose fresh output directories; replay refuses to overwrite existing evidence. Numerical dependencies are the existing NumPy/SciPy installation; the frozen champion uses its private native shared object only inside bwrap.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 timeout 620 /usr/bin/python3 -B adversary/ratchet3/replay_challenges.py --cases adversary/ratchet3/discovery_cases --submission champions/generation_2/submission --output adversary/ratchet3/discovery_rerun --workers 2 > adversary/ratchet3/discovery_rerun.log 2>&1
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 timeout 1000 /usr/bin/python3 -B evaluator/evaluate.py --submission champions/generation_2/submission --split hidden --output adversary/ratchet3/original_hidden_rerun.json > adversary/ratchet3/original_hidden_rerun.log 2>&1
```

The first command reproduces the private challenge protocol; the second is the official unchanged generation-2 evaluator CLI, not a new generation-3 test. Each private worker uses four disjoint cores; two workers do not give one solver eight cores. Per-case stdout/stderr, output artifacts, source snapshots and hashes are retained beside each report.

## Scientific cautions

- Synthetic lattice-Dirac acquisition proxies, not material-specific kdotpy/Kane simulations.
- Fixed four candidates, rank two in ambient dimension six, and four robust scenarios.
- Determinant-bundle Chern targets include -1, -2 and -3; no globally smooth frame is required.
- Candidate GL(2,C) frame invariance, common ambient unitary invariance, independent Wilson-loop scoring and 64-state exhaustive enumeration checked.
- Doubled-mesh Chern agreement is necessary here, not a proof of converged pointwise Berry curvature.
- The two refined meshes preserve Hamiltonian parameters and RNG seeds, not a continuum realization of acquisition noise.
- Wall runtime is hardware-sensitive; the largest observed runtime is near, but below, 90 seconds.
- The inherited 2-GiB restriction is RLIMIT_AS per process, not a cgroup-wide resident-memory measurement.
