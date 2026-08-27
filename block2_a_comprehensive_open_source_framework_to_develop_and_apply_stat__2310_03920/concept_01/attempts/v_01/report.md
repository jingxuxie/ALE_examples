# Are the transport traces physical? A bounded repair and validation study

## Reproduce

From this output directory: `ALE_ASSETS=/absolute/path/to/assets bash run.sh CASE.json RUN_DIRECTORY production`.
`baseline` and `refined` select distinct numerical policies. The input path and identifier are unrestricted; neither identifier nor family selects physics. The entry point sources the supplied numerical environment, limits each simulation to two numerical CPU threads, and never accesses the network or modifies assets.
Each successful `runs/<experiment>/replay.sh NEW_DIRECTORY` freezes its recorded configuration and tensor order. `ALE_ASSETS=... bash build_evidence.sh` rebuilds tables, figures, spectral checks, claims, and this report from the saved runs. The `workspace/*experiments.py` sources document case construction and the actual experimental sequence; replay scripts, rather than current defaults, reproduce historical candidates.

## Diagnosis: several independent failures

1. **The clock is wrong.** The legacy call supplies the complete sampling interval as `delta_t` and also supplies a substep count. The API evolves for their product. On the supplied 0.2 grid with legacy step 0.1, reported t=1.2 is physical t=2.4. Norm drift is 1.85e-06 and energy drift 3.98e-07, yet the integrated regional-continuity residual is 0.192834. Correcting only the clock reduces that residual to 0.000475023; it does not repair the initial Hamiltonian. See scaling rows `impurity_dev_legacy` and `impurity_dev_legacy_clock`.
2. **The interaction convention was not rederived.** Carrying U/2 into the spin-resolved integral interface implements half the stated onsite interaction. The integer-input dimer gives -1.561552812809 in legacy, the U=1 answer, rather than 1-sqrt(5)=-1.236067977500. The repaired result is -1.236067977500. Fixing both clock and U in the otherwise legacy impurity implementation reduces its observable RMS disagreement to 4.38e-07. The dimer also caught an integer-array casting bug in the first sparse implementation; that bug is fixed, and its failed pilot is retained.
3. **The extended models were projected onto a different problem.** Legacy averages real diagonal hopping entries, discards their imaginary parts and spin mixing, omits Zeeman, density interactions, pairing and every oscillator, and fixes N and Sz even when only N or parity is allowed. It therefore cannot answer the extended physical questions. Separate changed-Hamiltonian runs remove imaginary hopping components, density interactions, pairing or electron-phonon coupling. These are physical ablations, not numerical convergence tests; see the `*_physics_*` ablation rows.
4. **The measurements were incomplete.** All crossing hopping terms contribute, not a chosen bond or spin channel. Pairing contributes a distinct local/nonlocal electron source, and oscillator occupation is not zero by definition. The migrated current builder also discards matrix components. Regional indices must remain physical indices under tensor reordering.
5. **Energy convergence is not state convergence.** A two-site local DMRG eigenvalue is evaluated before the final truncation. The submitted `initial_energy` is instead the normalized expectation in the actual prepared state. Sweep eigenvalues and discarded weights are retained separately. Fixed small bonds can yield apparently stable local energies and still biased initial observables and subsequent current.

## Physical representation and numerical policies

Sparse assembly applies ordered fermionic creation/annihilation strings to occupation bitstrings in the stated interleaved spin convention. It enumerates only the specified N/Sz, N, or parity sector, tensors in the specified finite oscillator levels, and adds every record and its Hermitian conjugate exactly once. A separate MPO implementation uses local fermion matrices, exact graded ordering, neutral boson quantum numbers, and complete operator terms; it does not reuse the sparse assembler.
The actual operator definitions are J = i[H_hop,Q] and S = i[H_pair,Q]. For c†_i c_j the coefficient in J is -i(q_i-q_j)t; for c†_i c†_j the coefficient in S is -i(q_i+q_j)Delta, with conjugate terms. Onsite pairs inside the region thus carry a factor two. Onsite, density, and electron-phonon terms commute with Q. Expectations are divided by the actual norm; propagated states are not deliberately renormalized.
Production uses sparse Hermitian eigensolvers plus exponential action when the allowed-sector dimension is at most 1,000,000 and a conservative sparse-memory estimate is below 2,600 MiB. Real matrices use real eigensolvers without removing any nonzero imaginary coefficient. This is much faster and more accurate than forcing a tensor method on small and moderate cases. The cap was increased after the 12-site impurity sparse pilot proved both faster and more accurate than its tensor approximation while using about 1.6 GiB. Refined raises the dimension cap to 1,200,000, subject to the same memory gate.
Otherwise, production uses two-site DMRG and TDVP: fixed N/Sz uses four-state electronic sites and specialized Abelian blocks (bond 128, or 96 for vibrational systems with more than eight electrons sites), with step at most 0.1. N-only uses two-state spin orbitals, U(1) symmetry and bond 160; parity uses two-state modes, Z2 fermion symmetry and bond 96. These two latter policies use step at most 0.15 and switch from two-site to one-site TDVP at physical time 0.25, independently of the output grid. This is a measured cost compromise, not exact evolution. Tensor ordering compares the supplied order, natural order and reverse-Cuthill-McKee order, then reduces graph spans; each oscillator is adjacent to its host when layout optimization is enabled.
Baseline keeps the correct physics but uses bond 16, at most eight ground sweeps, coarse step 0.12 and the supplied layout. Refined uses larger bonds, smaller steps, tighter local solvers and two-site propagation throughout. Every actual choice, including deviations used in ablations, is recorded in stats.json. No extra physical Sz conservation is imposed on N-only or parity states. A tested redundant-charge SZ encoding is retained only as an experimental alternative, not the production N-only representation.

## Calibration, refinement, and independent checks

The table below uses the six observable columns charge/current/source/number/spin/phonon, equally weighted over the requested times. Sparse-versus-tensor comparisons test independent assembly and different state/evolution algorithms; they are stronger evidence than conservation. Dense full spectral propagation independently checks the exponential-action propagator in four development regimes (`spectral_checks.csv`). Sparse ground residuals and operator-level Hermiticity/continuity residuals are recorded in stats.json.

| Regime | E_before (production) | baseline RMS error | final tensor RMS vs sparse | production seconds | peak MiB |
|---|---:|---:|---:|---:|---:|
| impurity | -6.0036660730 | 0.000366 | 4.11e-10 | 0.091 | 59.6 |
| ladder | -4.2306738857 | 0.00838 | 1.15e-09 | 0.090 | 58.4 |
| spin_orbit | -5.3517241281 | 0.00137 | 3.62e-06 | 0.101 | 60.3 |
| paired | -6.2553413856 | 0.000511 | 2.75e-09 | 0.119 | 62.7 |
| vibronic | -5.2654387209 | 0.000274 | 1.13e-10 | 0.162 | 68.3 |

The actual loop changed timestep alone, sweep count at fixed bond, and bond/layout on ladder, paired and vibrational development cases. Reducing the timestep at bond 16 does not remove the preparation/truncation bias. Increasing sweeps can change which truncated state is returned without delivering the missing variational space. Raising the bond to 48 sharply reduces the disagreement:

| Case | bond 16 RMS | smaller-step RMS | more-sweeps RMS | bond 48 RMS |
|---|---:|---:|---:|---:|
| ladder | 0.00838 | 0.0087 | 0.00403 | 1.97e-08 |
| paired | 0.000511 | 0.000492 | 0.000515 | 4.84e-08 |
| vibronic | 0.000274 | 0.000275 | 0.000274 | 2.22e-08 |

A further six-oscillator check exposed a preparation failure that larger final bonds alone did not cure: low-bond warmup left a ground-energy bias of about 6.9e-7 at both bonds 128 and 192. Its H_before variance was 5.16e-06. Starting and sweeping at the full target bond reduced this to 3.67e-09, with the same answer from specialized and general symmetry backends. Production and refined oscillator MPS runs now start in the full target virtual space. The comparison changes preparation only, not the Hamiltonian, oscillator cutoff or propagator. Historical warmup trajectories and the repaired full trajectories are retained.

The extra `renamed_mixed_contact` has a deliberately uninformative family annotation, odd parity, nonlocal same-spin pairing, spin mixing, density interaction, four oscillators, a scrambled layout and an irregular grid. Independent assemblies agree to 5.31e-07 maximum observable difference. This directly exercises mixed fermion/boson signs and original-site measurements, rather than relying on family-specific answers.

## Supported transport interpretation

In the paired development case, total N changes by 0.0972771. Integrating transport alone misses the regional charge change by 0.45355; including the source reduces the residual to 0.00678718 on the 0.2 grid. On the 0.025 grid it is 0.000105735, a reduction of 64.19, consistent with second-order quadrature. The operator identity itself holds to roundoff. The remaining coarse-grid residual is not evidence for particle loss.
The spin-orbit development trace changes physical Sz by 0.00225522 while conserving N. Oscillator occupation and its response are nonzero in the vibrational case; removing the electron-phonon coupling changes the trace. Pair source, total N, physical Sz and boson occupation are all in results.csv, not inferred from a current curve. `primary_result.png` contrasts legacy, low-bond and repaired currents and explicitly separates paired transport from source.

## Size, resource cost, and the worst regime

The first large-system policy (bond 160, step 0.04, general four-state electronic sites) was too expensive. Timed-out pilots are retained in failed_runs.csv and their run logs. This motivated the dimension/memory-based sparse dispatch, compact spin-orbital representation for weaker symmetries, and the explicit hybrid-TDVP compromise. The difficult enlarged flux/SOC ring, not the impurity, controls the electronic accuracy/cost concern. A six-oscillator and a doped-ladder scaling study are also included.

| Final size run | allowed dimension | seconds | peak MiB |
|---|---:|---:|---:|
| impurity_scale_10 | 63504 | 0.89 | 152.4 |
| impurity_scale_12 | 853776 | 17.70 | 1472.4 |
| impurity_scale_14 | 11778624 | 44.64 | 208.9 |
| ladder_scale_10 | 14400 | 0.39 | 92.0 |
| ladder_scale_14 | 1002001 | 52.40 | 218.3 |
| paired_scale_10 | 524288 | 16.59 | 1545.1 |
| paired_scale_14 | 134217728 | 93.05 | 210.3 |
| spin_orbit_scale_10 | 125970 | 4.25 | 399.9 |
| spin_orbit_scale_14 | 30421755 | 137.63 | 225.3 |
| vibronic_scale_10_levels4 | 260112384 | 38.40 | 207.4 |
| vibronic_scale_6_levels3 | 291600 | 3.04 | 417.1 |
| vibronic_scale_6_levels4 | 1638400 | 45.51 | 241.6 |

The slowest successful final size run is spin_orbit_scale_14 at 137.63 s; the largest final size-run memory is 1545.1 MiB in paired_scale_10. These are measured solver-wall times, not a promise about every unseen graph. Exploratory jobs sometimes overlapped on this machine, so small timing differences are not meaningful microbenchmarks.

There is a quantitative worst-regime limitation, not just missing evidence: a higher-bond spatial SOC pilot completed preparation at E=-11.6433787103 before timing out during propagation. The production 14-site SOC state has E=-11.6389645950. Rayleigh-Ritz therefore bounds its initial-energy error from below by 0.00441412. The incomplete pilot is not used as a converged trajectory. Its preparation log and this comparison are linked in preparation_comparisons.csv. Large-ring transport is consequently not certified to the development-case precision.

The 10-site SOC and paired cases have independent sparse checks, and the six-site/six-oscillator three-level case has an independent sparse check as well. The four-level oscillator cutoff is a different Hamiltonian, not a convergence parameter silently changed in production. Resource comparisons on larger systems measure changes, not rigorous error bounds. See all named left/right runs in ablation.csv, including tensor candidates that were rejected on cost or accuracy.
A subsequent explicit sparse reference also solved the six-electron/six-four-level-oscillator problem (1,638,400 allowed states) in 29.19 s at 1917.8 MiB. The full-space initialization reduces its tensor initial-energy error from 2.56e-05 to 6.33e-10, and the maximum trajectory discrepancy is 6.21e-07. That reference deliberately overrides the conservative dispatch/memory estimate; its measured memory remains below the 4-GiB limit.

## Limits and audit trail

- Development sparse results are verified to high precision in the specified finite Hilbert space. No independently converged reference is claimed for every largest MPS case, especially the 14-site spin-orbit ring. Convergence of local energy, small discarded weight, norm or energy conservation cannot replace the observed cross-method and refinement errors.
- One-site TDVP after the initial two-site interval fixes the available virtual spaces. It can miss subsequent entanglement growth, particularly after strong or connectivity-changing quenches. This production speed tradeoff is disclosed; refined retains two-site evolution. Some high-resource candidates exceeded the study timeout and do not count as converged references.
- Oscillator cutoffs are exactly the input model. No continuum-boson extrapolation, long-lead limit, temperature averaging or dissipative reservoir is modeled. An exactly degenerate ground space does not specify a unique physical pure state without additional preparation information.
- These short, closed-system transients establish neither an infinite-lead steady current nor a conductance plateau. Initial-state bias, finite size, recurrences, source terms, and finite-time quadrature all have separate roles.
- results.csv, ablation.csv and scaling.csv have unique row identifiers. Figures have CSV source data. claims.json contains machine-checkable numeric comparisons; verification.json records spectral and packaging checks. Each successful run contains its input, profile, trajectory, actual settings, diagnostics, log and replay command. Failed candidates retain their input and failure log.

An additional analytic one-site pairing quench tests the source sign and factor two directly: N(t)=1-sin(2t), source(t)=-2 cos(2t), current=0. Its maximum error is 5.55e-16 (analytic_checks.json and the onsite_pair_analytic run). Seven selected fresh replays reproduce saved trajectories within 5.3e-9; see replay_checks.csv.
