# Transient transport release audit

## Recommendation

**Reject the supplied candidate. Conditionally release the repaired solver for the pulse-response study, with per-case refinement and spectral diagnostics.** The supplied families and independent controls support local-observable accuracy much better than 1e-4 on these measured cases. They do not prove uniform accuracy or throughput at every simultaneous extreme of the documented envelope.

The executable is `run.sh`; all active imports are under `workspace/transport`. It reads arbitrary input cases, never branches on IDs or families, and writes absolute densities and oriented absolute currents. Only installed Python/NumPy/SciPy are needed for simulation; Pillow is used for figures.

```sh
bash /submission/run.sh --cases /cases.json --output /output --config production
```

## Failure, diagnosis, revision, rerun

1. **Reproduce:** `runs/baseline/` retains the original executable results. The undriven control loses 0.379441 in a local density and its central charge falls from 5.83395 to 2.43975. Both original convention tests pass. Thus their success and smooth traces do not qualify the workflow.
2. **Discriminate:** `qualification.csv` rows `stationary_control:legacy_half_step` and `stationary_control:legacy_no_absorber` change one candidate parameter each. Halving the step barely changes the large drift; removing absorption removes almost all drift but does not repair the finite, averaged-occupation preparation. The original absorber destroys the occupied stationary sea, not merely outgoing perturbations. The candidate also replaces independently occupied contacts and bound states by one Fermi function.
3. **First repair fails a different control:** `runs/revision1/` contains scattering/source evolution with an insufficient 64-cell localized-state search. Its ring spectral-identity error is 0.120017; its initial charge is 3.22667175. No-drive source propagation would still be stationary. The flake and side branch also have missing spectral weight. This explicitly reconciles apparently stable traces with an incorrect initial state.
4. **Revise and rerun:** `runs/revision2/` enlarges the bound calculation independently of propagation. Final production additionally polishes unresolved shallow bound roots and normalizes their infinite tails using the self-energy derivative. The ring initial charge becomes 3.8188371. Maximum development active-space spectral-identity error is 1.32e-09. `history.csv` is recomputed from retained iteration traces, not invented retrospective targets.
5. **Additional regression loops:** a channel-basis/gap test exposed imaginary-broadening tails being misread as continuum weight near bound poles. Final preparation excludes lead band gaps and distinguishes propagating from regularization-dependent closed-channel weight. The larger generic-hopping stress subsequently exposed overflow in iterative surface decimation (`runs/failed_decimation_stress.log`). The final general surface solver uses a retarded generalized-Schur invariant subspace instead; the stress is rerun with this replacement. Tests include a gapped sector embedded inside another channel’s band.

## Connected numerical method

- Enlarge the active region by the first cell of each lead. Retarded lead surfaces obey `g = [E-Hcell-V† g V]^-1`, with the supplied outward-hop convention. Scalar intercell hoppings use an exact surface formula. General, complex and singular hoppings use the stable subspace of the quadratic Bloch pencil, ordered by a generalized Schur decomposition; no inverse of the possibly singular hopping is taken. Bloch extrema define continuum integration intervals.
- For each incoming lead, form `Psi_A = G_A sqrt(Gamma_lead/(2*pi))`. Integrate its outer product with that lead’s specified Fermi function. Adaptive 8/16-point Gauss comparisons use endpoint-smoothing coordinates, occupation matrices and a horizon-frequency kernel; zero-temperature chemical potentials are explicit breakpoints. Localized finite-spectrum candidates also seed narrow resonances. Report quadrature depth/error and the unoccupied spectral identity, including bound states.
- Normalizable states use `bound_mu` and `bound_temperature`, without imposed initial coherences. The usual bound search uses 128 cells (192 conservative), rejects large outer-tail weight, and resolves degenerate localized subspaces. A spectral deficit triggers a nonlinear bound-state search with normalization `phi†[I-dSigma/dE]phi`; this repairs shallow infinite tails. Bound states in a gap and symmetry-dark states inside a continuum are included separately.
- Evolve only `delta_psi`, initially zero: `i*d(delta_psi)/dt = H(t)*delta_psi + delta_H(t)*psi_initial*exp(-i*E*t)`. Reconstruct the absolute state at observation times. All additive, bond-phase, contact-phase and overlapping/noncommuting drive terms are included with their specified time profiles. The reservoir Fermi functions are never shifted by a contact phase.
- DOP853 evolves independent batches of 128 weighted states. Normally, hard walls lie past the round-trip propagation front, using `2*||V||` as a velocity upper estimate and a guard region. Very long/fast cases use a smooth quartic absorber **only on the driven correction**, never on the stationary sea. Production caps lead length at 112 cells; conservative uses 168 and a longer absorber. The hard-wall/absorber comparison is independent evidence, not a proof for all possible modes.
- Conservative tightens energy quadrature, bound localization, time tolerances and boundaries. Ablation keeps the production numerical design but replaces all initial occupations by a common mean chemical potential and maximum lead temperature. It is a preparation ablation, not a refinement. It is intentionally unchanged on equal-occupation cases where the occupied bound sector is also unchanged.

## Measured trace comparisons

Each number is a maximum absolute difference across all supplied times and requested orbitals/bonds. See `comparisons.csv`; a refinement difference is not a reference error.

| Case | density: conservative | current: conservative | current: occupation ablation |
|---|---:|---:|---:|
| fp_development | 9.54e-08 | 1.15e-08 | 0 |
| sidebranch_development | 8.13e-08 | 2.25e-08 | 0.0284 |
| ring_development | 2.1e-07 | 4.07e-07 | 0.0958 |
| spin_development | 1.34e-07 | 4.31e-08 | 0 |
| flake_development | 3.32e-07 | 1.78e-07 | 0 |
| dimer_development | 3.8e-07 | 5.01e-07 | 0.0719 |

- **Stationarity (C1):** repaired undriven density drift is 1.11e-16. This is expected by construction and does not independently validate occupations.
- **Independent initial state and evolution (C7):** `qualification.csv` has four `finite_reference` rows: equilibrium infinite-lead preparation is checked against a 128-cell coupled Hermitian spectrum, with specified bound occupations, followed by direct full-state Schrodinger evolution. This uses neither the source ansatz nor continuum energy quadrature. The finite reference is itself a controlled approximation and shares Hamiltonian/drive decoding and observation conventions.
- **Unequal occupations (C8):** stationary ring total outward current differs from an independently integrated Landauer transmission by 1.83e-12. The mean-occupation ablation is stationary too, but has wrong transport and density. Persistent equilibrium ring circulation is not confused with net transport.
- **Separated numerical axes:** `energy_only`, `time_only` and `boundary_only` rows vary one intended accuracy axis. Boundary enlargement also changes the adaptive integrator RMS norm, so its tiny residual difference cannot be uniquely attributed to reflections. The coupled conservative comparison alone is not used as an accuracy certificate (C2, C3).
- **Localized dynamics:** changing only the initial dark-state occupation produces a current difference of 0.215. The 80-unit side-branch control has a late branch-current peak 0.00151 for t>=50, with a distant hard wall. These controls support a physical localized contribution to persistent oscillations, not an attribution of every oscillation to one eigenstate.
- **Boundary stress (C9):** at horizon 80 and lead hopping 3.5, CAP versus a distant hard wall differs by 6.49e-07 in density and 6.79e-07 in current.
- **Model-envelope stress:** the retained three-lead, four-orbital, complex noncommuting-hopping case at horizon 40 takes 133 s in production. Its spectral identity residual is 2.4e-09, but it reaches a local quadrature-depth cap. No completed additional refinement is claimed for this case; it remains outside the qualified accuracy subset.
- **Conventions and edge cases:** 15/15 executable assertion tests pass (`runs/tests.jsonl`): zero-temperature analytic density/Landauer current; isolated noncommuting drives; dark occupation; complex singular-lead basis covariance; zero intercell hopping; shallow bound normalization; narrow resonance versus bound state; overlapping conducting/gapped sectors; current sign and surface/phase conventions. `python3 -m pytest` is unavailable in this interpreter, so `check_tests.py` runs the same pytest-compatible test functions directly.

## Runtime, memory, and figures

The six production development simulations total 23.881 s and reach 100.789 MiB measured batch high-water RSS (C6, C11). The spin horizon increases from 12 to 48: measured time 2.256 -> 10.453 s, ratio 4.634 (C5). All numerical libraries are restricted to one thread. RSS is `ru_maxrss`, cumulative within each batch process, not a per-case incremental allocation. Configurations and scaling run in separate processes. Times exclude output compression; no speedup or universal asymptotic law is claimed.
The primary figure plots absolute first-bond currents, including the stationary offsets, for all six cases. `figures/primary_result.csv` contains the exact raw-trace times, total densities and first currents. `figures/robustness_or_scaling.csv` copies measured resource cells from `scaling.csv`; its PNG plots those runtimes. `audit_artifacts.py` recomputes summaries, source data and every claim comparison.

## Limits and release gate

- Spectral completeness, stationarity, conservation and refinement agreement are necessary controls here, not independent universal proofs. A wrong occupation can pass completeness and stationarity. Narrow resonances, nearly decoupled states, threshold states, partially flat bands and ill-conditioned spectral pencils can defeat finite quadrature/root tolerances; `accuracy_warning` flags large spectral deficits or exhausted quadrature depth but is not an exhaustive error estimator.
- The finite bound candidate search and nonlinear polishing are not a theorem that every normalizable sector is found. Extremely weak couplings comparable to numerical retarded regularization remain a limitation. Threshold/channel filtering and absorber quality need per-case convergence checks. No certified transient oracle was available for arbitrary nonequilibrium multichannel systems; the independent finite control is limited to equal reservoir occupations.
- The supplied current grids define trapezoidal summary charge only; those integrals are not separately time-grid-converged physical transported charges. Absolute small currents, not only large density offsets, were compared.
- Runtime/memory evidence covers the supplied batch plus the stated stresses, not all cases simultaneously at N=56, three four-orbital leads, scale 3.5 and horizon 80. Do not interpret the observed throughput as a worst-envelope guarantee.
- For a new pulse study: inspect metadata warnings and bound spectrum, compare production/conservative local traces (not only summary charges), perform a stationary/occupation control, and refine the observation grid if the integrated current is a scientific endpoint. Escalate unresolved deficits or model-sensitive discrepancies rather than trusting a smooth trace.

## Reproducibility and evidence map

`results.csv`, `ablation.csv`, and `scaling.csv` are backed by `runs/{production,conservative,ablation,scaling}`. `qualification.csv` is backed by `runs/qualification`; generated cases are defined deterministically in `qualification.py`. `comparisons.csv` is recomputed from the paired traces. `history.csv` links the archived before/revision runs. `claims.json` gives the machine-checkable bounded statements. `report.md` is generated from those measurements.
Run `bash reproduce.sh` to regenerate final experiments, qualification, tests, figures, claims and audits with the bundled inputs. Historical intermediate traces remain archived; the original candidate is independently rerunnable through `workspace/legacy_driver.py` and `legacy_transport`. Historical upstream examples and their original license remain provenance only and are never imported.

The minimal copied submission is also replayed on all six development cases with both production and ablation (`runs/replay`, `replay.json`): maximum density/current difference is 0. This demonstrates portability and reproducibility, not independent physical accuracy.

The finite-reference occupation override uses the production bound-energy list to identify finite eigenvectors; that control does not independently certify bound-state identification. Analytic dark/shallow-bound tests supply separate controls. Delayed/short pulse boundaries constrain integration steps and have a dedicated regression test.

The optional large-stress conservative run was voluntarily interrupted at the research-budget guard (`optional_refinement_status.json`). All required development conservative runs are complete; no partial optional trace or guessed accuracy is reported.
