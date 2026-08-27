# Release audit: conditional approval of the replacement

## Decision and scope

**Do not release the legacy forecast as a general process predictor. Release the new
`selected` implementation with its method/convergence diagnostics.** All seven public
cases pass the audit; all 17 exact/invariance tests pass. No parameters were fitted
to lab checks. A result marked `converged: false`, `accuracy_warning`, or
`resource_warning` is an explicitly uncertified finite-noise prediction, not a scientific
accuracy guarantee. `k2` has a separate deterministic calculation.

| Case | Baseline infidelity | Selected infidelity | Selected/refined channel difference | Seconds | Peak MiB |
|---|---:|---:|---:|---:|---:|
| calibration_static | 0.013901375 | 0.038441827 | 7.2e-15 | 0.004 | 57.8 |
| driven_static | 0.090613926 | 0.32308586 | 3.1e-11 | 0.014 | 58.3 |
| switching_echo | 0.13870014 | 0.10978303 | 8.8e-16 | 0.025 | 57.1 |
| memory_ou | 0.12902683 | 0.24193525 | 3.2e-14 | 1.666 | 57.7 |
| white_gate | 0.038384294 | 0.074703571 | 2.2e-14 | 0.026 | 55.9 |
| leakage_static | 0.0011354948 | 0.0022952204 | 4.1e-13 | 1.144 | 60.8 |
| broadband_entangler | 4.5173085e-07 | 9.160816e-07 | 1.2e-07 | 4.832 | 60.9 |

Differences use the contract's full complex Frobenius normalization, not just fidelity.
`results.csv` has all 14 required public comparisons; `ablation.csv` has 21 separately
executed selected/refined/restart rows, including a white-noise control. Artifact paths
lead to the actual process arrays. The largest selected time is
4.832 seconds and largest selected peak RSS is
60.9 MiB. Fresh-process wall times, rather than
only predictor timings, are also recorded in `scaling.csv` and `launches.json`.

## Competing explanations and discriminating experiments

1. **Representation error? Not found in the tested conversions.** Complex Hamiltonian,
   column-vectorization, Choi normalization, ideal segment splitting, and vendor-basis
   conversion tests pass. The latter residual is
   7.92e-16.
   This is evidence against a transpose/normalization explanation, not proof of every
   unused vendor path.
2. **Spectral convention and quadrature error? Yes.** The baseline uses a two-sided PSD
   on positive frequencies only, without folding. At the same cutoffs, the response
   doubles when the negative half is included. Its artificial Lorentzian static model
   also loses low-frequency weight: dense positive integration recovers only 0.352084
   of the exact static response; two-sided integration gives 0.704168; lowering the
   cutoff gives 0.999306. The remaining discrepancy reflects finite regularization and
   quadrature. Refining the original 160-point mesh alone does not repair the model.
   See the `static_spectrum_*` rows in `experiments.csv`.
3. **Bath memory mistaken for a gate-library operation? Yes.** Baseline regrouping of
   identical driven controls changes infidelity from
   0.09061393 to
   0.18725451; selected is invariant.
   Independent bath restarts change selected driven-static infidelity by
   -0.08677763
   and OU infidelity by
   -0.00801216.
   White-noise restart and continuous predictions agree. `blocks` never changes the
   physical selected target.
4. **Missing coherent response? Yes.** `second_order=False` discards ordered frequency
   shifts. The replacement retains the anti-Hermitian part of `k2`; omitting it is
   independently tested in `*_symmetric_cumulant` rows. The five finite-difference
   response tests in `validation/response.csv` have relative errors at most
   3.62e-07.
5. **Second-cumulant closure invalid at finite noise? Also yes.** With the *correct full*
   `k2`, `Phi0 exp(k2)` still has
   28.109%
   full-channel error on driven Gaussian static noise. Scalar Gaussianity does not
   terminate the ordered noncommuting operator cumulants. A Gaussian OU replacement
   for switching noise with exactly the same covariance has identical `k2` but
   3.242%
   different finite-noise channel. Neither PSD, complete positivity, nor one fidelity
   identifies the full target.

## Replacement and controlled approximation

Static Gaussian noise uses converged Gaussian quadrature over stationary latent draws;
OU uses normalized Hermite stochastic-Liouville dynamics; telegraph uses its discrete
Markov/Walsh dynamics; white noise uses the exact Stratonovich Lindblad generator.
Latent mixing, segment-dependent sensitivity, initial stationarity, time ordering and
all Hilbert-space states are retained. Six-state records are never projected to four
states. The synthetic leakage test actually transfers population outside its two-state
computational subspace; the public six-state static case happens to have zero leakage.

The separate quadratic response propagates the ideal channel, first-order bath memories,
and their ordered second-order return, then transforms to the **initial** interaction
frame. This includes coherent effects and does not approximate static noise by a narrow
spectral line. See `workspace/METHODS.md` for equations, error bounds and limits.

The fast exponential is retained only when a covariance-envelope Dyson bound certifies
relative error below 2e-4. For the 250-segment broadband record its conservative bound is
2e-05; observed selected/refined
channel difference is 1.22e-07.
Refinement uses a degree-two Hermite bath, exact through fourth order, with analytic
omitted-tail bound 1.55e-11
before floating-point error. This is evidence for a weak-noise approximation, not an
assumption that a many-rate bath is white or static.

## Chronological run → diagnosis → revision → rerun

- **11:31 UTC:** Executed the requested original calibration command.
  `initial_static/process.npz` and `initial_static/metrics.json` record infidelity
  0.013901375 versus the exact 0.038441827 and the noisy lab check 0.039203308.
- **11:33–11:41:** Inspected the multi-file package and pipeline; preserved baseline
  unchanged in `workspace/pipeline/baseline.py`. Implemented law-specific solvers and
  ordered response. First public results are retained under `iterations/pre_final/`;
  spectral, partition, and closure experiments isolate distinct causes.
- **11:41–11:45:** Initial high-order broadband refinement took 127.464 seconds and
  failed its very tight convergence threshold. Its actual arrays and metrics remain
  in `iterations/broadband_refined_v1_slow/`; this version was not released.
- **11:45–11:48:** Replaced repeated high-order weak-bath solves by a fourth-order
  tail-controlled calculation. Propagated the deviation from the ideal channel to
  prevent large ideal-channel roundoff from dominating tiny weak-noise differences.
  The rerun took 21.178 seconds (`logs/broadband_entangler_refined_v2.log`).
- **Final rerun:** `launches.json` records UTC start times, commands, wall time and
  successful exits for all 28 fresh invocations from a different working directory.
  The final broadband refinement takes 20.311
  seconds. `logs/tests.log`, `logs/experiments.log`, `diagnostics/*.json`, and the
  evidence tables retain the subsequent validation, rather than just a method summary.

Independent trajectory diagnostics were rerun with seed 4217: static, OU, and coarse/fine
switching checks (`diagnostics.csv`). Their sampling errors and time-discretization
errors are distinct. The switching coarse/fine estimates change with their random
realizations as well as step size; this is not treated as deterministic convergence.
The supplied lab checks agree with selected within two reported standard errors in
infidelity, but these checks alone do not certify process accuracy.

## Figures and limitations

`figures/primary_result.png` separates agreement with noisy scalar observations from
full-channel convergence. Green crosses show why repairing `k2` alone is insufficient.
`figures/robustness_or_scaling.png` shows memory effects, measured accuracy/resource
tradeoffs, and the weak-amplitude scaling of the closure error. All plotted source rows
and transformations are identified in `figures/sources.json`. `claims.json` contains
machine-recomputable quantitative claims, including memory and validity claims.

Finite Hermite/Walsh truncation is not automatically CP and adjacent-order agreement is
an empirical check, not a universal error theorem. Strong, high-rank baths can exhaust
the state/work budget; these emit warnings and retain the last completed prediction
(or explicitly labeled cumulant fallback), never a silently truncated time record.
An 85-second refinement deadline is checked between segments; a single expensive
matrix-exponential action and the separate response calculation are not hard preempted.
The public release stays below 60 seconds and far below 1.5 GiB, but arbitrary input
sizes outside these measurements are not certified. Analytic weak-bath bounds exclude
floating-point errors; refinements below about 1e-10 absolute channel norm are
roundoff-sensitive. The scaling rows are heterogeneous workloads, not a controlled
fit of asymptotic segment-count complexity. No supplied controls, covariance laws, or leakage geometry may be
replaced by a name-based assumption.

## Reproduction

Run `bash run.sh input/cases/driven_static.json DEST --mode selected` from this directory,
or use absolute paths from elsewhere. `baseline`, `refined`, and `no_memory` are supported.
`bash workspace/audit.sh` reruns tests, all public modes, diagnostics, experiments and
evidence checks. It uses only copied inputs, supplied dependencies, and local output paths.
