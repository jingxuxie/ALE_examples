import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def table(name):
    return {row['row_id']: row for row in csv.DictReader((ROOT / name).open())}


scaling = table('scaling.csv')
ablation = table('ablation.csv')
results = table('results.csv')
spectral = table('spectral_checks.csv')
preparation = {}
production_path = ROOT / 'runs/spin_orbit_scale_14_production/stats.json'
pilot_path = ROOT / 'runs/spin_orbit_scale_14_spatial192_hybrid/run.log'
if production_path.exists() and pilot_path.exists():
    for line in pilot_path.read_text().splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get('phase') == 'prepared':
            production_energy = json.loads(production_path.read_text())['initial_energy']
            comparison = dict(row_id='spin_orbit14_variational_bound', case='spin_orbit_scale_14',
                              left_run='spin_orbit_scale_14_production', right_run='spin_orbit_scale_14_spatial192_hybrid',
                              production_initial_energy=production_energy, lower_variational_energy=record['energy'],
                              initial_energy_error_lower_bound=max(0.0, production_energy - record['energy']),
                              pilot_preparation_seconds=record['seconds'])
            preparation[comparison['row_id']] = comparison
            with (ROOT / 'preparation_comparisons.csv').open('w') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(comparison))
                writer.writeheader()
                writer.writerow(comparison)
            break


def value(rows, identifier, column):
    return float(rows[identifier][column])


claims = []


def claim(text, filename, row, column, comparison, threshold=None, other=None):
    rhs = {'value': threshold} if other is None else {'row_id': other[0], 'column': other[1]}
    selected = {'scaling.csv': scaling, 'ablation.csv': ablation, 'results.csv': results,
                'spectral_checks.csv': spectral, 'preparation_comparisons.csv': preparation}[filename]
    left_value = value(selected, row, column)
    right_value = threshold if other is None else value(selected, *other)
    assert (left_value < right_value if comparison == 'lt' else left_value > right_value), text
    claims.append(dict(text=text, table=filename, lhs=dict(row_id=row, column=column), op=comparison, rhs=rhs))


claim('The legacy impurity trajectory has regional integrated-continuity error above 0.1.',
      'scaling.csv', 'impurity_dev_legacy', 'continuity_quadrature_residual', 'gt', 0.1)
claim('Fixing the elapsed-time argument reduces the impurity continuity residual without fixing its Hamiltonian.',
      'scaling.csv', 'impurity_dev_legacy_clock', 'continuity_quadrature_residual', 'lt',
      other=('impurity_dev_legacy', 'continuity_quadrature_residual'))
claim('The repaired integer-input dimer agrees with 1-sqrt(5) within 1e-10.',
      'scaling.csv', 'dimer_calibration_production', 'calibration_energy_error', 'lt', 1e-10)
claim('Increasing the ladder bond/layout resources reduces RMS observable error by more than 1000-fold.',
      'ablation.csv', 'ladder_dev_baseline_vs_exact', 'refinement_error_ratio', 'gt', 1000)
claim('Pairing changes total electronic number by more than 0.05 on this closed-system development trace.',
      'scaling.csv', 'paired_dev_production', 'number_change', 'gt', 0.05)
claim('Including the pairing source gives a smaller paired-contact continuity residual than using transport alone.',
      'scaling.csv', 'paired_dev_production', 'continuity_quadrature_residual', 'lt',
      other=('paired_dev_production', 'continuity_without_source'))
claim('A finer output grid reduces the paired-contact trapezoidal continuity residual.',
      'scaling.csv', 'paired_dev_dense_grid', 'continuity_quadrature_residual', 'lt',
      other=('paired_dev_production', 'continuity_quadrature_residual'))
claim('Independent dense spectral propagation agrees with the paired sparse trajectory to better than 1e-9.',
      'spectral_checks.csv', 'paired_dense_spectral', 'max_observable_error', 'lt', 1e-9)
claim('The mixed odd-parity oscillator case agrees between independent sparse and tensor assemblies within 1e-5.',
      'ablation.csv', 'mixed_boson_parity_layout', 'observable_max_difference', 'lt', 1e-5)
claim('A broad initial virtual space reduces the six-oscillator ground-state variance relative to low-bond warmup.',
      'scaling.csv', 'vibronic_scale_6_levels3_wide_start', 'initial_variance', 'lt',
      other=('vibronic_scale_6_levels3_variance', 'initial_variance'))
claim('The repaired six-electron, six-four-level-oscillator tensor trajectory agrees with its 1,638,400-state sparse reference within 1e-6.',
      'ablation.csv', 'vibronic_scale_6_levels4_production_vs_exact', 'observable_max_difference', 'lt', 1e-6)
if preparation:
    claim('The production 14-site SOC initial energy has a variational error lower bound exceeding 0.004; it is not precision-converged.',
          'preparation_comparisons.csv', 'spin_orbit14_variational_bound', 'initial_energy_error_lower_bound', 'gt', 0.004)
(ROOT / 'claims.json').write_text(json.dumps(dict(schema='numeric-comparisons-v1', claims=claims), indent=2))

legacy = scaling['impurity_dev_legacy']
clock = scaling['impurity_dev_legacy_clock']
paired = scaling['paired_dev_production']
dense_paired = scaling['paired_dev_dense_grid']
regimes = ['impurity', 'ladder', 'spin_orbit', 'paired', 'vibronic']
lines = [
    '# Are the transport traces physical? A bounded repair and validation study',
    '',
    '## Reproduce',
    '',
    'From this output directory: `ALE_ASSETS=/absolute/path/to/assets bash run.sh CASE.json RUN_DIRECTORY production`.',
    '`baseline` and `refined` select distinct numerical policies. The input path and identifier are unrestricted; neither identifier nor family selects physics. The entry point sources the supplied numerical environment, limits each simulation to two numerical CPU threads, and never accesses the network or modifies assets.',
    'Each successful `runs/<experiment>/replay.sh NEW_DIRECTORY` freezes its recorded configuration and tensor order. `ALE_ASSETS=... bash build_evidence.sh` rebuilds tables, figures, spectral checks, claims, and this report from the saved runs. The `workspace/*experiments.py` sources document case construction and the actual experimental sequence; replay scripts, rather than current defaults, reproduce historical candidates.',
    '',
    '## Diagnosis: several independent failures',
    '',
    f"1. **The clock is wrong.** The legacy call supplies the complete sampling interval as `delta_t` and also supplies a substep count. The API evolves for their product. On the supplied 0.2 grid with legacy step 0.1, reported t=1.2 is physical t=2.4. Norm drift is {float(legacy['norm_drift']):.3g} and energy drift {float(legacy['energy_drift']):.3g}, yet the integrated regional-continuity residual is {float(legacy['continuity_quadrature_residual']):.6g}. Correcting only the clock reduces that residual to {float(clock['continuity_quadrature_residual']):.6g}; it does not repair the initial Hamiltonian. See scaling rows `impurity_dev_legacy` and `impurity_dev_legacy_clock`.",
    f"2. **The interaction convention was not rederived.** Carrying U/2 into the spin-resolved integral interface implements half the stated onsite interaction. The integer-input dimer gives {value(scaling, 'dimer_calibration_legacy', 'initial_energy'):.12f} in legacy, the U=1 answer, rather than 1-sqrt(5)={1-math.sqrt(5):.12f}. The repaired result is {value(scaling, 'dimer_calibration_production', 'initial_energy'):.12f}. Fixing both clock and U in the otherwise legacy impurity implementation reduces its observable RMS disagreement to {value(ablation, 'impurity_dev_legacy_clock_U_vs_exact', 'observable_rms_difference'):.3g}. The dimer also caught an integer-array casting bug in the first sparse implementation; that bug is fixed, and its failed pilot is retained.",
    '3. **The extended models were projected onto a different problem.** Legacy averages real diagonal hopping entries, discards their imaginary parts and spin mixing, omits Zeeman, density interactions, pairing and every oscillator, and fixes N and Sz even when only N or parity is allowed. It therefore cannot answer the extended physical questions. Separate changed-Hamiltonian runs remove imaginary hopping components, density interactions, pairing or electron-phonon coupling. These are physical ablations, not numerical convergence tests; see the `*_physics_*` ablation rows.',
    '4. **The measurements were incomplete.** All crossing hopping terms contribute, not a chosen bond or spin channel. Pairing contributes a distinct local/nonlocal electron source, and oscillator occupation is not zero by definition. The migrated current builder also discards matrix components. Regional indices must remain physical indices under tensor reordering.',
    '5. **Energy convergence is not state convergence.** A two-site local DMRG eigenvalue is evaluated before the final truncation. The submitted `initial_energy` is instead the normalized expectation in the actual prepared state. Sweep eigenvalues and discarded weights are retained separately. Fixed small bonds can yield apparently stable local energies and still biased initial observables and subsequent current.',
    '',
    '## Physical representation and numerical policies',
    '',
    'Sparse assembly applies ordered fermionic creation/annihilation strings to occupation bitstrings in the stated interleaved spin convention. It enumerates only the specified N/Sz, N, or parity sector, tensors in the specified finite oscillator levels, and adds every record and its Hermitian conjugate exactly once. A separate MPO implementation uses local fermion matrices, exact graded ordering, neutral boson quantum numbers, and complete operator terms; it does not reuse the sparse assembler.',
    'The actual operator definitions are J = i[H_hop,Q] and S = i[H_pair,Q]. For c†_i c_j the coefficient in J is -i(q_i-q_j)t; for c†_i c†_j the coefficient in S is -i(q_i+q_j)Delta, with conjugate terms. Onsite pairs inside the region thus carry a factor two. Onsite, density, and electron-phonon terms commute with Q. Expectations are divided by the actual norm; propagated states are not deliberately renormalized.',
    'Production uses sparse Hermitian eigensolvers plus exponential action when the allowed-sector dimension is at most 1,000,000 and a conservative sparse-memory estimate is below 2,600 MiB. Real matrices use real eigensolvers without removing any nonzero imaginary coefficient. This is much faster and more accurate than forcing a tensor method on small and moderate cases. The cap was increased after the 12-site impurity sparse pilot proved both faster and more accurate than its tensor approximation while using about 1.6 GiB. Refined raises the dimension cap to 1,200,000, subject to the same memory gate.',
    'Otherwise, production uses two-site DMRG and TDVP: fixed N/Sz uses four-state electronic sites and specialized Abelian blocks (bond 128, or 96 for vibrational systems with more than eight electrons sites), with step at most 0.1. N-only uses two-state spin orbitals, U(1) symmetry and bond 160; parity uses two-state modes, Z2 fermion symmetry and bond 96. These two latter policies use step at most 0.15 and switch from two-site to one-site TDVP at physical time 0.25, independently of the output grid. This is a measured cost compromise, not exact evolution. Tensor ordering compares the supplied order, natural order and reverse-Cuthill-McKee order, then reduces graph spans; each oscillator is adjacent to its host when layout optimization is enabled.',
    'Baseline keeps the correct physics but uses bond 16, at most eight ground sweeps, coarse step 0.12 and the supplied layout. Refined uses larger bonds, smaller steps, tighter local solvers and two-site propagation throughout. Every actual choice, including deviations used in ablations, is recorded in stats.json. No extra physical Sz conservation is imposed on N-only or parity states. A tested redundant-charge SZ encoding is retained only as an experimental alternative, not the production N-only representation.',
    '',
    '## Calibration, refinement, and independent checks',
    '',
    'The table below uses the six observable columns charge/current/source/number/spin/phonon, equally weighted over the requested times. Sparse-versus-tensor comparisons test independent assembly and different state/evolution algorithms; they are stronger evidence than conservation. Dense full spectral propagation independently checks the exponential-action propagator in four development regimes (`spectral_checks.csv`). Sparse ground residuals and operator-level Hermiticity/continuity residuals are recorded in stats.json.',
    '',
    '| Regime | E_before (production) | baseline RMS error | final tensor RMS vs sparse | production seconds | peak MiB |',
    '|---|---:|---:|---:|---:|---:|',
]
for regime in regimes:
    case = regime + '_dev'
    data = scaling[case + '_production']
    lines.append(f"| {regime} | {float(data['initial_energy']):.10f} | {value(ablation, case+'_baseline_vs_exact', 'observable_rms_difference'):.3g} | {value(ablation, case+'_final_tensor_vs_exact', 'observable_rms_difference'):.3g} | {float(data['seconds']):.3f} | {float(data['peak_rss_mb']):.1f} |")
lines += [
    '',
    'The actual loop changed timestep alone, sweep count at fixed bond, and bond/layout on ladder, paired and vibrational development cases. Reducing the timestep at bond 16 does not remove the preparation/truncation bias. Increasing sweeps can change which truncated state is returned without delivering the missing variational space. Raising the bond to 48 sharply reduces the disagreement:',
    '',
    '| Case | bond 16 RMS | smaller-step RMS | more-sweeps RMS | bond 48 RMS |',
    '|---|---:|---:|---:|---:|',
]
for regime in ['ladder', 'paired', 'vibronic']:
    identifiers = [regime + '_dev_' + label + '_vs_exact' for label in ['baseline', 'smallstep16', 'more_sweeps16', 'bond48']]
    lines.append('| ' + regime + ' | ' + ' | '.join(f"{value(ablation, identifier, 'observable_rms_difference'):.3g}" for identifier in identifiers) + ' |')
lines += [
    '',
    f"A further six-oscillator check exposed a preparation failure that larger final bonds alone did not cure: low-bond warmup left a ground-energy bias of about 6.9e-7 at both bonds 128 and 192. Its H_before variance was {value(scaling, 'vibronic_scale_6_levels3_variance', 'initial_variance'):.3g}. Starting and sweeping at the full target bond reduced this to {value(scaling, 'vibronic_scale_6_levels3_wide_start', 'initial_variance'):.3g}, with the same answer from specialized and general symmetry backends. Production and refined oscillator MPS runs now start in the full target virtual space. The comparison changes preparation only, not the Hamiltonian, oscillator cutoff or propagator. Historical warmup trajectories and the repaired full trajectories are retained.",
    '',
    f"The extra `renamed_mixed_contact` has a deliberately uninformative family annotation, odd parity, nonlocal same-spin pairing, spin mixing, density interaction, four oscillators, a scrambled layout and an irregular grid. Independent assemblies agree to {value(ablation, 'mixed_boson_parity_layout', 'observable_max_difference'):.3g} maximum observable difference. This directly exercises mixed fermion/boson signs and original-site measurements, rather than relying on family-specific answers.",
    '',
    '## Supported transport interpretation',
    '',
    f"In the paired development case, total N changes by {float(paired['number_change']):.6g}. Integrating transport alone misses the regional charge change by {float(paired['continuity_without_source']):.6g}; including the source reduces the residual to {float(paired['continuity_quadrature_residual']):.6g} on the 0.2 grid. On the 0.025 grid it is {float(dense_paired['continuity_quadrature_residual']):.6g}, a reduction of {float(paired['continuity_quadrature_residual']) / float(dense_paired['continuity_quadrature_residual']):.2f}, consistent with second-order quadrature. The operator identity itself holds to roundoff. The remaining coarse-grid residual is not evidence for particle loss.",
    f"The spin-orbit development trace changes physical Sz by {value(scaling, 'spin_orbit_dev_production', 'spin_change'):.6g} while conserving N. Oscillator occupation and its response are nonzero in the vibrational case; removing the electron-phonon coupling changes the trace. Pair source, total N, physical Sz and boson occupation are all in results.csv, not inferred from a current curve. `primary_result.png` contrasts legacy, low-bond and repaired currents and explicitly separates paired transport from source.",
    '',
    '## Size, resource cost, and the worst regime',
    '',
    'The first large-system policy (bond 160, step 0.04, general four-state electronic sites) was too expensive. Timed-out pilots are retained in failed_runs.csv and their run logs. This motivated the dimension/memory-based sparse dispatch, compact spin-orbital representation for weaker symmetries, and the explicit hybrid-TDVP compromise. The difficult enlarged flux/SOC ring, not the impurity, controls the electronic accuracy/cost concern. A six-oscillator and a doped-ladder scaling study are also included.',
    '',
    '| Final size run | allowed dimension | seconds | peak MiB |',
    '|---|---:|---:|---:|',
]
size_rows = [row for row in scaling.values() if '_scale_' in row['case'] and row['row_id'] == row['case'] + '_production']
for data in sorted(size_rows, key=lambda row: row['case']):
    lines.append(f"| {data['case']} | {data['sector_dimension']} | {float(data['seconds']):.2f} | {float(data['peak_rss_mb']):.1f} |")
if size_rows:
    worst_time = max(size_rows, key=lambda row: float(row['seconds']))
    worst_memory = max(size_rows, key=lambda row: float(row['peak_rss_mb']))
    lines.append(f"\nThe slowest successful final size run is {worst_time['case']} at {float(worst_time['seconds']):.2f} s; the largest final size-run memory is {float(worst_memory['peak_rss_mb']):.1f} MiB in {worst_memory['case']}. These are measured solver-wall times, not a promise about every unseen graph. Exploratory jobs sometimes overlapped on this machine, so small timing differences are not meaningful microbenchmarks.")
if preparation:
    bound = preparation['spin_orbit14_variational_bound']
    lines.append(f"\nThere is a quantitative worst-regime limitation, not just missing evidence: a higher-bond spatial SOC pilot completed preparation at E={bound['lower_variational_energy']:.10f} before timing out during propagation. The production 14-site SOC state has E={bound['production_initial_energy']:.10f}. Rayleigh-Ritz therefore bounds its initial-energy error from below by {bound['initial_energy_error_lower_bound']:.6g}. The incomplete pilot is not used as a converged trajectory. Its preparation log and this comparison are linked in preparation_comparisons.csv. Large-ring transport is consequently not certified to the development-case precision.")
lines += [
    '',
    'The 10-site SOC and paired cases have independent sparse checks, and the six-site/six-oscillator three-level case has an independent sparse check as well. The four-level oscillator cutoff is a different Hamiltonian, not a convergence parameter silently changed in production. Resource comparisons on larger systems measure changes, not rigorous error bounds. See all named left/right runs in ablation.csv, including tensor candidates that were rejected on cost or accuracy.',
    f"A subsequent explicit sparse reference also solved the six-electron/six-four-level-oscillator problem (1,638,400 allowed states) in {value(scaling, 'vibronic_scale_6_levels4_exact', 'seconds'):.2f} s at {value(scaling, 'vibronic_scale_6_levels4_exact', 'peak_rss_mb'):.1f} MiB. The full-space initialization reduces its tensor initial-energy error from {value(ablation, 'vibronic_scale_6_levels4_warmup_vs_exact', 'initial_energy_difference'):.3g} to {value(ablation, 'vibronic_scale_6_levels4_production_vs_exact', 'initial_energy_difference'):.3g}, and the maximum trajectory discrepancy is {value(ablation, 'vibronic_scale_6_levels4_production_vs_exact', 'observable_max_difference'):.3g}. That reference deliberately overrides the conservative dispatch/memory estimate; its measured memory remains below the 4-GiB limit.",
    '',
    '## Limits and audit trail',
    '',
    '- Development sparse results are verified to high precision in the specified finite Hilbert space. No independently converged reference is claimed for every largest MPS case, especially the 14-site spin-orbit ring. Convergence of local energy, small discarded weight, norm or energy conservation cannot replace the observed cross-method and refinement errors.',
    '- One-site TDVP after the initial two-site interval fixes the available virtual spaces. It can miss subsequent entanglement growth, particularly after strong or connectivity-changing quenches. This production speed tradeoff is disclosed; refined retains two-site evolution. Some high-resource candidates exceeded the study timeout and do not count as converged references.',
    '- Oscillator cutoffs are exactly the input model. No continuum-boson extrapolation, long-lead limit, temperature averaging or dissipative reservoir is modeled. An exactly degenerate ground space does not specify a unique physical pure state without additional preparation information.',
    '- These short, closed-system transients establish neither an infinite-lead steady current nor a conductance plateau. Initial-state bias, finite size, recurrences, source terms, and finite-time quadrature all have separate roles.',
    '- results.csv, ablation.csv and scaling.csv have unique row identifiers. Figures have CSV source data. claims.json contains machine-checkable numeric comparisons; verification.json records spectral and packaging checks. Each successful run contains its input, profile, trajectory, actual settings, diagnostics, log and replay command. Failed candidates retain their input and failure log.',
]
if (ROOT / 'analytic_checks.json').exists():
    analytic = json.loads((ROOT / 'analytic_checks.json').read_text())
    lines.append(f"\nAn additional analytic one-site pairing quench tests the source sign and factor two directly: N(t)=1-sin(2t), source(t)=-2 cos(2t), current=0. Its maximum error is {analytic['onsite_pair_max_error']:.3g} (analytic_checks.json and the onsite_pair_analytic run). Seven selected fresh replays reproduce saved trajectories within 5.3e-9; see replay_checks.csv.")
(ROOT / 'report.md').write_text('\n'.join(lines) + '\n')
print('Wrote report.md and', len(claims), 'checked claims')
