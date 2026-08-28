# Thermal counterexample audit: REJECT / no validated counterexample

Do not build a thermal ratchet from these regions. The full-budget completed
solver handles the strongest reference-certified follow-up tested here.
No pilot, participant, attempt, evaluator, frozen case, or original reference
was modified. No model was launched and no existing initial/challenge run was
repeated. Everything authored by this audit is in this sidecar.

## Main scores and duplication

| Split | Mean | Worst family: interface | Surface | Cubic |
|---|---:|---:|---:|---:|
| Initial | 0.984411269 | 0.965552318 | 0.991120251 | 0.996561237 |
| Challenge | 0.985749112 | 0.968700279 | 0.992045313 | 0.996501743 |

Sources are the completed, read-only main JSONs under
`../runs/initial/free_energy.initial.parallel.scores.json` and
`../runs/initial/free_energy.challenge.parallel.scores.json`.
`score_clusters.json` records their hashes, family/component errors, and score
normalization. Interface errors are largest; some components use the existing
reference-uncertainty floor. No floor or score threshold was tightened here.

There are **six distinct initial physical inputs**, twelve distinct challenge
inputs, and six distinct confirmation inputs, with no cross-split duplicates
under metadata removal and canonical undirected bond ordering. This is not a
graph-isomorphism proof. Confirmation cases were inventoried, not evaluated.

## Candidate regions, all N = 2048

| Candidate | Physical mechanism | Evidence | Decision |
|---|---|---|---|
| `ce_surface_compensation` | Bulk easy-z K=.10 versus surface easy-plane K=.40 at T=.80; coherent-rotation anisotropy cancels | Full solver 0.995195403; independent source 0.994628356; all validation gates pass | Reject: no failure |
| `ce_bulk_twoion_competition` | Axial bond b=.12 versus easy-plane onsite K=.24 plus surface .035 at T=1.12; hard-angle moment suppression | Three-angle raw torque differs by at most 1.575 combined SEM | No scout failure; no certified full reference |
| `ce_weak_interface_twist` | Orthogonal layer axes, weak interface J=.18, upper J=.65, interface b=.10 at T=.65 | Official multi-start Rhat 26.5463 | Reject invalid reference; not a hard solver case |
| `ce_compensated_exchange_stiffness` | Single-/two-ion cancellation, b=.25 and Qxx=Qyy=b*degree/2 at T=1.05 | Three-angle raw torque differs by at most 0.554 combined SEM | No scout failure; no certified full reference |

The first surface scout's maximum raw-torque discrepancy was 1.845 combined SEM.
All scouts use four independent official-CMC starts at five angles, each with
10000 burn and 10000 production sweeps. Their Rhat values 1.124, 1.130, and
1.206 for the three non-twist regions do **not** certify final references.

Submitted-kernel scouts use byte-identical copied runtime code with a wrapper
setting a 95-second budget and three windows. Only raw torque, magnetization,
and acceptance are compared. Sparse-grid MBAR output is not scored as failure
of the default fifteen-window solver. Protocol, outputs, and block data are
retained in `scout_protocol.json`, `scouts/`, and `scout_analysis.json`.

## Independent full-size surface validation

The unchanged `attempt/solve.py` ran through the audited bubblewrap harness at
the original 600-second limit: **540.536 s wall, 535.55 s compute**, return code
zero, 172724 KiB peak RSS. It used its normal fifteen-window symmetric MBAR.
The output and stderr are in `submissions/ce_surface_compensation/`.

The reference uses the unchanged extracted official `cmc_step` and `mc_angle`,
not an invented replacement kernel. Source commit:
`525bc27ee44c525aee229570f30f3d4c61d54f66`.
Only initialization and extra spatial diagnostics are added by the wrapper.
Aligned, hot, domain-x, and domain-z starts keep the same directional ensemble.

- Gold: seventeen angles, four chains each, 20000 burn + 30000 production sweeps.
- Interleaved midpoints: sixteen angles, two chains each, same lengths.
- Independent strong: seventeen angles, separate seeds, two chains each,
  40000 burn + 40000 production sweeps.
- Reflection: minus pi/4, two independent chains, 20000 + 30000 sweeps.
- The first pass failed spatial Rhat gates despite a 0.994715 strong score.
  All first-pass data and reports remain in `reference/raw/` and the result
  directory's `first_pass/`; this failure was not hidden.
- Both flagged midpoint angles and the strong zero-angle set were replaced
  for final estimation by four fresh starts each with **60000 burn + 120000
  production sweeps**. Gates were unchanged. The plan and old failures are in
  `reference/refinement_plan.json`. Total: 148 full-reference trajectories
  generated, 142 used in final estimation, plus separate scout trajectories.

Final predeclared checks all pass:

| Check | Result |
|---|---:|
| Maximum block Rhat over torque, M, energy and spatial observables | 1.037145450 |
| Maximum split Rhat | 1.039765011 |
| Independent source score | **0.994628356** |
| Old solver score | **0.995195403** |
| Old solver torque RMSE | 3.2777728431e-5 |
| Old solver free-energy RMSE | 2.7724611839e-5 |
| 17-to-33-angle refinement envelope / baseline free-energy RMSE | 0.011037655 |
| Endpoint symmetry, reflection, hot/cold/domain consistency, unit norms, constraint | PASS |

Both score components are normalized by baseline error, not by an inflated
uncertainty floor. The weak baseline scores approximately 0.5. The independent
strong trajectory set is disjoint from the gold set; no untrusted submission
is imported by the analyzer or evaluator.

`reference/results/ce_surface_compensation/` contains `reference.json`,
`strong_prediction.json`, `strong_reference_scores.json`, `baseline_scores.json`,
`validation.json`, and `full_comparison.json`. Free energy is obtained by
independent composite-Simpson integration of source torque on the refined grid,
not by reusing the submission's MBAR implementation.

## Why the suspected mechanisms did not produce a CE

The completed solver combines global-projection Wolff, heat-bath and
overrelaxation proposals with an anisotropy Metropolis filter
(`../../pilots/free_energy/attempt/sampler.cpp:249`). It carries configurations
through angular windows and subsequently solves MBAR. These are plausible
extensive-acceptance, slow-mode and angular-overlap risks, not demonstrated bugs.

In the exact-compensation scout, heat-bath acceptance fell to 0.000111, but
cluster acceptance remained 0.463–0.470 and overrelaxation remained active.
Raw torque still agreed with source. Low acceptance of one proposal type is
therefore not evidence that the mixture fails. The full surface run also
agrees with independently integrated source free energy. Its reported target
MBAR ESS is 7140–30107; these correlated-configuration counts are diagnostic,
not independent sample sizes or a proof of overlap/mixing.

## Primary grounding and physical contract

- Asselin et al.: https://arxiv.org/pdf/1006.3507 . Eq. (1), Sec. V Eq. (3),
  and Sec. VI ground bulk/surface and single-/two-ion competition, constrained
  torque integration, and hard-axis magnetization/free-energy behavior.
- Evans et al.: https://arxiv.org/pdf/2002.02548 . Eqs. (1), (5), (10), (11)
  and the p. 3 discussion following Fig. 2 describe cancellation at zero
  temperature with finite anisotropy at finite temperature. These stress-model
  coefficients are not a fit to that paper's weak-anisotropy material parameters.
- Exchange-spring motivation: https://www.nature.com/articles/ncomms11931 .
  This motivates testing spatial profiles; it does not rescue the rejected
  unconverged weak-interface reference.

The Hamiltonian, equal fixed spin moments, slab size/boundaries, total-M
directional solid-angle ensemble, and output grid are unchanged. In particular,
tau_y/N = -df/dtheta. For the final compensation scout, algebra gives

    H_anis = constant + (b/2) sum_bonds (s_iz - s_jz)^2.

Thus coherent uniform spins have no orientation-dependent energy, while thermal
spin gradients can produce directional free energy. `analysis_checks.json`
checks this identity numerically and checks Simpson integration independently.

## Limits, reproduction and handoff

Block SEM and 1.96-SEM envelopes are nominal pointwise normal approximations,
not simultaneous confidence bands or rigorous global mixing/truncation bounds.
The quoted refinement envelope is the RMS of pointwise envelopes, normalized
by baseline error. Finite multi-start chains and refinement provide evidence,
not a theorem of equilibrium or an exhaustive search of physical parameters.
The earlier two-spin exact audit is not used to certify large-system mixing.
Only the surface follow-up has a certified full reference in this sidecar.

From this directory, stored-data analysis can be reproduced without new runs:

```sh
export PYTHONPATH="$PWD/../python_runtime"
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python inventory.py
python analyze_scouts.py
python validate_full.py ce_surface_compensation
python summarize.py
```

Native generation is in `reference/run.py` and `refine.py`; the isolated
unchanged submission launcher is `run_isolated.py` and requires the escalated
bubblewrap environment. No global dependency installation is needed.

`STATUS.json` is the machine-readable rejection/handoff. `source_provenance.json`,
`manifest.json`, `immutability_checks.json`, and `ARTIFACT_HASHES.json` preserve
source/input integrity and evidence. Original reserved cases/seeds are untouched.
