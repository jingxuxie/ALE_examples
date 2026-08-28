import argparse
import csv
import json
from pathlib import Path
import numpy as np
from driver import summarize
from experiment import write_csv
from transport.model import load_suite


def read_rows(path):
    with open(path) as handle:
        return list(csv.DictReader(handle))


def cell(table, row_id, column):
    return dict(table=table, row_id=row_id, column=column)


def finalize(output):
    output = Path(output).resolve()
    cases = load_suite(output / 'inputs' / 'development.json')
    controls = load_suite(output / 'inputs' / 'controls.json')
    case_map = {case['id']: case for case in cases + controls}
    comparisons = []
    for configuration in ['conservative', 'ablation']:
        for case in cases:
            production = np.load(output / 'runs' / 'production' / (case['id'] + '.npz'))
            alternative = np.load(output / 'runs' / configuration / (case['id'] + '.npz'))
            comparisons.append(dict(row_id=case['id'] + ':production_vs_' + configuration,
                                    case=case['id'], comparison=configuration,
                                    density_error=float(np.max(abs(production['density'] - alternative['density']))),
                                    current_error=float(np.max(abs(production['current'] - alternative['current']))),
                                    initial_density_error=float(np.max(abs(production['density'][0] - alternative['density'][0]))),
                                    initial_current_error=float(np.max(abs(production['current'][0] - alternative['current'][0])))))
        selected = [row for row in comparisons if row['comparison'] == configuration]
        comparisons.append(dict(row_id='all_development:production_vs_' + configuration,
                                case='all_development', comparison=configuration,
                                **{key: max(row[key] for row in selected) for key in
                                   ['density_error', 'current_error', 'initial_density_error', 'initial_current_error']}))
    write_csv(output / 'comparisons.csv', comparisons)
    history = []
    for label, directory in [('candidate_controls', 'baseline/controls'),
                             ('candidate_development', 'baseline/development'),
                             ('candidate_refinement', 'baseline/refinement'),
                             ('revision1', 'revision1'), ('revision2', 'revision2')]:
        for path in sorted((output / 'runs' / directory).glob('*.npz')):
            case = case_map[path.stem]
            result = dict(np.load(path))
            metadata = json.loads(path.with_suffix('.json').read_text())
            row = summarize(case, result, metadata, label)
            row['spectral_sum_rule_error'] = metadata.get('spectral_sum_rule_error', 0.)
            history.append(row)
    write_csv(output / 'history.csv', history)
    production_rows = read_rows(output / 'results.csv')
    scaling_rows = read_rows(output / 'scaling.csv')
    qualification_rows = read_rows(output / 'qualification.csv')
    qualification = {row['row_id']: row for row in qualification_rows}
    tests = [json.loads(line) for line in (output / 'runs' / 'tests.jsonl').read_text().splitlines()]
    maximum_sum_rule_error = max(json.loads((output / 'runs' / 'production' / (case['id'] + '.json')).read_text())['spectral_sum_rule_error'] for case in cases)
    checks = [dict(row_id='development_resources', metric='summed_case_runtime_seconds',
                   value=sum(float(row['runtime_s']) for row in production_rows)),
              dict(row_id='development_memory', metric='batch_peak_rss_mb',
                   value=max(float(row['peak_rss_mb']) for row in production_rows)),
              dict(row_id='development_spectral_weight', metric='maximum_active_sum_rule_error', value=maximum_sum_rule_error),
              dict(row_id='assertion_tests', metric='passed_tests', value=sum(test['passed'] for test in tests))]
    write_csv(output / 'checks.csv', checks)
    claims = [
        dict(id='C1', text='The repaired stationary control has no measurable density drift on its supplied grid; source stationarity alone is not an initial-state accuracy certificate.',
             left=cell('scaling.csv', 'stationary_control:production', 'max_density_change'), comparison='le', value=1e-12),
        dict(id='C2', text='On the supplied spin experiment, production and conservative agree in the coarse-grid first-bond transported-charge summary to 1e-4; this is not a continuum-time integration error bound.',
             left=cell('results.csv', 'spin_development:production', 'transported_charge'), comparison='abs_difference_le',
             right=cell('ablation.csv', 'spin_development:conservative', 'transported_charge'), tolerance=1e-4),
        dict(id='C3', text='All six supplied development traces agree with conservative in every requested current to 1e-5, a bounded refinement observation rather than a universal accuracy guarantee.',
             left=cell('comparisons.csv', 'all_development:production_vs_conservative', 'current_error'), comparison='le', value=1e-5),
        dict(id='C4', text='Averaging all initial occupations reduces the ring first-bond integrated current in this experiment. This ablation changes preparation only, but does not separately identify each reservoir and bound-sector contribution.',
             left=cell('results.csv', 'ring_development:production', 'transported_charge'), comparison='ge',
             right=cell('ablation.csv', 'ring_development:ablation', 'transported_charge')),
        dict(id='C5', text='The measured 48-unit spin control completes within 60 seconds on this machine; this is not a bound for simultaneous maximum-size envelope parameters.',
             left=cell('scaling.csv', 'scaling_long:production', 'runtime_s'), comparison='le', value=60.),
        dict(id='C6', text='The supplied six-case production batch uses under 2 GiB measured batch high-water RSS.',
             left=cell('checks.csv', 'development_memory', 'value'), comparison='le', value=2048.),
        dict(id='C7', text='An independently prepared finite coupled equilibrium embedding and direct full-state propagation match the flake production densities to 1e-5; this control does not validate unequal-reservoir preparation.',
             left=cell('qualification.csv', 'flake_development:finite_reference', 'density_error'), comparison='le', value=1e-5),
        dict(id='C8', text='The stationary unequal-occupation ring total outgoing current agrees with a separately integrated Landauer transmission to 1e-6.',
             left=cell('qualification.csv', 'ring_stationary:production', 'landauer_current_error'), comparison='le', value=1e-6),
        dict(id='C9', text='For the retained 80-unit, hopping-3.5 stress case, the correction-only absorber and a distant hard wall agree in every requested current to 1e-5; no universal absorber certificate is inferred.',
             left=cell('qualification.csv', 'fast_lead_long_horizon:hard_wall_check', 'current_error'), comparison='le', value=1e-5),
        dict(id='C10', text='The retained three-reservoir, four-orbital complex-hopping stress case agrees with conservative in every requested current to 1e-5.',
             left=cell('qualification.csv', 'three_four_channel_stress:conservative', 'current_error'), comparison='le', value=1e-5),
        dict(id='C11', text='The summed measured simulation time for the six development production cases is below the 240-second evaluation budget; process startup and serialization are not included in this sum.',
             left=cell('checks.csv', 'development_resources', 'value'), comparison='le', value=240.)]
    if 'three_four_channel_stress:conservative' not in qualification:
        claims = [claim for claim in claims if claim['id'] != 'C10']
    (output / 'claims.json').write_text(json.dumps(dict(claims=claims), indent=2) + '\n')
    refined = {row['case']: row for row in comparisons if row['comparison'] == 'conservative'}
    ablated = {row['case']: row for row in comparisons if row['comparison'] == 'ablation'}
    stationary = next(row for row in scaling_rows if row['case'] == 'stationary_control')
    short = next(row for row in scaling_rows if row['case'] == 'scaling_short')
    long = next(row for row in scaling_rows if row['case'] == 'scaling_long')
    old_stationary = next(row for row in history if row['row_id'] == 'stationary_control:candidate_controls')
    old_ring = next(row for row in history if row['row_id'] == 'ring_development:revision1')
    new_ring = next(row for row in production_rows if row['case'] == 'ring_development')
    stress_seconds = float(qualification['three_four_channel_stress:production']['runtime_s'])
    if 'three_four_channel_stress:conservative' in qualification:
        stress_statement = f"- **Model-envelope stress (C10):** the retained three-lead, four-orbital, complex noncommuting-hopping case at horizon 40 differs from conservative by {float(qualification['three_four_channel_stress:conservative']['current_error']):.3g} in current. Production takes {stress_seconds:.3g} s. Its quadrature reaches the local depth cap despite a small spectral-sum residual, so the warning remains relevant; this is not an all-envelope certificate."
    else:
        stress_statement = f"- **Model-envelope stress:** the retained three-lead, four-orbital, complex noncommuting-hopping case at horizon 40 takes {stress_seconds:.3g} s in production. Its spectral identity residual is {float(qualification['three_four_channel_stress:production']['spectral_sum_rule_error']):.3g}, but it reaches a local quadrature-depth cap. No completed additional refinement is claimed for this case; it remains outside the qualified accuracy subset."
    lines = ['# Transient transport release audit', '',
             '## Recommendation', '',
             '**Reject the supplied candidate. Conditionally release the repaired solver for the pulse-response study, with per-case refinement and spectral diagnostics.** The supplied families and independent controls support local-observable accuracy much better than 1e-4 on these measured cases. They do not prove uniform accuracy or throughput at every simultaneous extreme of the documented envelope.', '',
             'The executable is `run.sh`; all active imports are under `workspace/transport`. It reads arbitrary input cases, never branches on IDs or families, and writes absolute densities and oriented absolute currents. Only installed Python/NumPy/SciPy are needed for simulation; Pillow is used for figures.', '',
             '```sh', 'bash /submission/run.sh --cases /cases.json --output /output --config production', '```', '',
             '## Failure, diagnosis, revision, rerun', '',
             f"1. **Reproduce:** `runs/baseline/` retains the original executable results. The undriven control loses {old_stationary['max_density_change']:.6g} in a local density and its central charge falls from {old_stationary['initial_charge']:.6g} to {old_stationary['final_charge']:.6g}. Both original convention tests pass. Thus their success and smooth traces do not qualify the workflow.",
             '2. **Discriminate:** `qualification.csv` rows `stationary_control:legacy_half_step` and `stationary_control:legacy_no_absorber` change one candidate parameter each. Halving the step barely changes the large drift; removing absorption removes almost all drift but does not repair the finite, averaged-occupation preparation. The original absorber destroys the occupied stationary sea, not merely outgoing perturbations. The candidate also replaces independently occupied contacts and bound states by one Fermi function.',
             f"3. **First repair fails a different control:** `runs/revision1/` contains scattering/source evolution with an insufficient 64-cell localized-state search. Its ring spectral-identity error is {old_ring['spectral_sum_rule_error']:.6g}; its initial charge is {old_ring['initial_charge']:.9g}. No-drive source propagation would still be stationary. The flake and side branch also have missing spectral weight. This explicitly reconciles apparently stable traces with an incorrect initial state.",
             f"4. **Revise and rerun:** `runs/revision2/` enlarges the bound calculation independently of propagation. Final production additionally polishes unresolved shallow bound roots and normalizes their infinite tails using the self-energy derivative. The ring initial charge becomes {float(new_ring['initial_charge']):.9g}. Maximum development active-space spectral-identity error is {maximum_sum_rule_error:.3g}. `history.csv` is recomputed from retained iteration traces, not invented retrospective targets.",
             '5. **Additional regression loops:** a channel-basis/gap test exposed imaginary-broadening tails being misread as continuum weight near bound poles. Final preparation excludes lead band gaps and distinguishes propagating from regularization-dependent closed-channel weight. The larger generic-hopping stress subsequently exposed overflow in iterative surface decimation (`runs/failed_decimation_stress.log`). The final general surface solver uses a retarded generalized-Schur invariant subspace instead; the stress is rerun with this replacement. Tests include a gapped sector embedded inside another channel’s band.', '',
             '## Connected numerical method', '',
             '- Enlarge the active region by the first cell of each lead. Retarded lead surfaces obey `g = [E-Hcell-V† g V]^-1`, with the supplied outward-hop convention. Scalar intercell hoppings use an exact surface formula. General, complex and singular hoppings use the stable subspace of the quadratic Bloch pencil, ordered by a generalized Schur decomposition; no inverse of the possibly singular hopping is taken. Bloch extrema define continuum integration intervals.',
             '- For each incoming lead, form `Psi_A = G_A sqrt(Gamma_lead/(2*pi))`. Integrate its outer product with that lead’s specified Fermi function. Adaptive 8/16-point Gauss comparisons use endpoint-smoothing coordinates, occupation matrices and a horizon-frequency kernel; zero-temperature chemical potentials are explicit breakpoints. Localized finite-spectrum candidates also seed narrow resonances. Report quadrature depth/error and the unoccupied spectral identity, including bound states.',
             '- Normalizable states use `bound_mu` and `bound_temperature`, without imposed initial coherences. The usual bound search uses 128 cells (192 conservative), rejects large outer-tail weight, and resolves degenerate localized subspaces. A spectral deficit triggers a nonlinear bound-state search with normalization `phi†[I-dSigma/dE]phi`; this repairs shallow infinite tails. Bound states in a gap and symmetry-dark states inside a continuum are included separately.',
             '- Evolve only `delta_psi`, initially zero: `i*d(delta_psi)/dt = H(t)*delta_psi + delta_H(t)*psi_initial*exp(-i*E*t)`. Reconstruct the absolute state at observation times. All additive, bond-phase, contact-phase and overlapping/noncommuting drive terms are included with their specified time profiles. The reservoir Fermi functions are never shifted by a contact phase.',
             '- DOP853 evolves independent batches of 128 weighted states. Normally, hard walls lie past the round-trip propagation front, using `2*||V||` as a velocity upper estimate and a guard region. Very long/fast cases use a smooth quartic absorber **only on the driven correction**, never on the stationary sea. Production caps lead length at 112 cells; conservative uses 168 and a longer absorber. The hard-wall/absorber comparison is independent evidence, not a proof for all possible modes.',
             '- Conservative tightens energy quadrature, bound localization, time tolerances and boundaries. Ablation keeps the production numerical design but replaces all initial occupations by a common mean chemical potential and maximum lead temperature. It is a preparation ablation, not a refinement. It is intentionally unchanged on equal-occupation cases where the occupied bound sector is also unchanged.', '',
             '## Measured trace comparisons', '',
             'Each number is a maximum absolute difference across all supplied times and requested orbitals/bonds. See `comparisons.csv`; a refinement difference is not a reference error.', '',
             '| Case | density: conservative | current: conservative | current: occupation ablation |',
             '|---|---:|---:|---:|']
    for case in cases:
        identifier = case['id']
        lines.append(f"| {identifier} | {refined[identifier]['density_error']:.3g} | {refined[identifier]['current_error']:.3g} | {ablated[identifier]['current_error']:.3g} |")
    lines.extend(['',
                  f"- **Stationarity (C1):** repaired undriven density drift is {float(stationary['max_density_change']):.3g}. This is expected by construction and does not independently validate occupations.",
                  '- **Independent initial state and evolution (C7):** `qualification.csv` has four `finite_reference` rows: equilibrium infinite-lead preparation is checked against a 128-cell coupled Hermitian spectrum, with specified bound occupations, followed by direct full-state Schrodinger evolution. This uses neither the source ansatz nor continuum energy quadrature. The finite reference is itself a controlled approximation and shares Hamiltonian/drive decoding and observation conventions.',
                  f"- **Unequal occupations (C8):** stationary ring total outward current differs from an independently integrated Landauer transmission by {float(qualification['ring_stationary:production']['landauer_current_error']):.3g}. The mean-occupation ablation is stationary too, but has wrong transport and density. Persistent equilibrium ring circulation is not confused with net transport.",
                  '- **Separated numerical axes:** `energy_only`, `time_only` and `boundary_only` rows vary one intended accuracy axis. Boundary enlargement also changes the adaptive integrator RMS norm, so its tiny residual difference cannot be uniquely attributed to reflections. The coupled conservative comparison alone is not used as an accuracy certificate (C2, C3).',
                  f"- **Localized dynamics:** changing only the initial dark-state occupation produces a current difference of {float(qualification['sidebranch_empty_dark:production']['current_error']):.3g}. The 80-unit side-branch control has a late branch-current peak {float(qualification['sidebranch_late_control:production']['late_current_peak']):.3g} for t>=50, with a distant hard wall. These controls support a physical localized contribution to persistent oscillations, not an attribution of every oscillation to one eigenstate.",
                  f"- **Boundary stress (C9):** at horizon 80 and lead hopping 3.5, CAP versus a distant hard wall differs by {float(qualification['fast_lead_long_horizon:hard_wall_check']['density_error']):.3g} in density and {float(qualification['fast_lead_long_horizon:hard_wall_check']['current_error']):.3g} in current.",
                  stress_statement,
                  f"- **Conventions and edge cases:** {sum(test['passed'] for test in tests)}/{len(tests)} executable assertion tests pass (`runs/tests.jsonl`): zero-temperature analytic density/Landauer current; isolated noncommuting drives; dark occupation; complex singular-lead basis covariance; zero intercell hopping; shallow bound normalization; narrow resonance versus bound state; overlapping conducting/gapped sectors; current sign and surface/phase conventions. The advertised pytest executable is absent here, so `check_tests.py` runs the same pytest-compatible test functions directly.", '',
                  '## Runtime, memory, and figures', '',
                  f"The six production development simulations total {checks[0]['value']:.3f} s and reach {checks[1]['value']:.3f} MiB measured batch high-water RSS (C6, C11). The spin horizon increases from 12 to 48: measured time {float(short['runtime_s']):.3f} -> {float(long['runtime_s']):.3f} s, ratio {float(long['runtime_s']) / float(short['runtime_s']):.3f} (C5). All numerical libraries are restricted to one thread. RSS is `ru_maxrss`, cumulative within each batch process, not a per-case incremental allocation. Configurations and scaling run in separate processes. Times exclude output compression; no speedup or universal asymptotic law is claimed.",
                  'The primary figure plots absolute first-bond currents, including the stationary offsets, for all six cases. `figures/primary_result.csv` contains the exact raw-trace times, total densities and first currents. `figures/robustness_or_scaling.csv` copies measured resource cells from `scaling.csv`; its PNG plots those runtimes. `audit_artifacts.py` recomputes summaries, source data and every claim comparison.', '',
                  '## Limits and release gate', '',
                  '- Spectral completeness, stationarity, conservation and refinement agreement are necessary controls here, not independent universal proofs. A wrong occupation can pass completeness and stationarity. Narrow resonances, nearly decoupled states, threshold states, partially flat bands and ill-conditioned spectral pencils can defeat finite quadrature/root tolerances; `accuracy_warning` flags large spectral deficits or exhausted quadrature depth but is not an exhaustive error estimator.',
                  '- The finite bound candidate search and nonlinear polishing are not a theorem that every normalizable sector is found. Extremely weak couplings comparable to numerical retarded regularization remain a limitation. Threshold/channel filtering and absorber quality need per-case convergence checks. No certified transient oracle was available for arbitrary nonequilibrium multichannel systems; the independent finite control is limited to equal reservoir occupations.',
                  '- The supplied current grids define trapezoidal summary charge only; those integrals are not separately time-grid-converged physical transported charges. Absolute small currents, not only large density offsets, were compared.',
                  '- Runtime/memory evidence covers the supplied batch plus the stated stresses, not all cases simultaneously at N=56, three four-orbital leads, scale 3.5 and horizon 80. Do not interpret the observed throughput as a worst-envelope guarantee.',
                  '- For a new pulse study: inspect metadata warnings and bound spectrum, compare production/conservative local traces (not only summary charges), perform a stationary/occupation control, and refine the observation grid if the integrated current is a scientific endpoint. Escalate unresolved deficits or model-sensitive discrepancies rather than trusting a smooth trace.', '',
                  '## Reproducibility and evidence map', '',
                  '`results.csv`, `ablation.csv`, and `scaling.csv` are backed by `runs/{production,conservative,ablation,scaling}`. `qualification.csv` is backed by `runs/qualification`; generated cases are defined deterministically in `qualification.py`. `comparisons.csv` is recomputed from the paired traces. `history.csv` links the archived before/revision runs. `claims.json` gives the machine-checkable bounded statements. `report.md` is generated from those measurements.',
                  'Run `bash reproduce.sh` to regenerate final experiments, qualification, tests, figures, claims and audits with the bundled inputs. Historical intermediate traces remain archived; the original candidate is independently rerunnable through `workspace/legacy_driver.py` and `legacy_transport`. Historical upstream examples and their original license remain provenance only and are never imported.', ''])
    if (output / 'replay.json').exists():
        replay = json.loads((output / 'replay.json').read_text())
        maximum_replay_difference = max(max(record['density_difference'], record['current_difference']) for record in replay['comparisons'])
        lines.extend([f"The minimal copied submission is also replayed on all six development cases with both production and ablation (`runs/replay`, `replay.json`): maximum density/current difference is {maximum_replay_difference:.3g}. This demonstrates portability and reproducibility, not independent physical accuracy.", ''])
    lines = [line.replace('The advertised pytest executable is absent here, so', '`python3 -m pytest` is unavailable in this interpreter, so') for line in lines]
    lines.extend(['The finite-reference occupation override uses the production bound-energy list to identify finite eigenvectors; that control does not independently certify bound-state identification. Analytic dark/shallow-bound tests supply separate controls. Delayed/short pulse boundaries constrain integration steps and have a dedicated regression test.', ''])
    if 'three_four_channel_stress:conservative' not in qualification and (output / 'optional_refinement_status.json').exists():
        lines.extend(['The optional large-stress conservative run was voluntarily interrupted at the research-budget guard (`optional_refinement_status.json`). All required development conservative runs are complete; no partial optional trace or guessed accuracy is reported.', ''])
    (output / 'report.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    finalize(parser.parse_args().output)
