import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'evaluator'))
from evaluate import aggregate, verify_frozen_package

GROUPS = {
    'discovery': ('discovery_cases', 'discovery_champion_replay', 'discovery_lp_control_replay', 'discovery_baseline'),
    'heldout': ('heldout_cases', 'heldout_champion', 'heldout_lp_control', 'heldout_baseline'),
    'resolved_discovery': ('resolved_discovery', 'resolved_discovery_champion', 'resolved_discovery_lp_control', 'resolved_discovery_baseline'),
    'resolved_heldout': ('resolved_heldout', 'resolved_heldout_champion', 'resolved_heldout_lp_control', 'resolved_heldout_baseline'),
}


def read(path):
    return json.loads(path.read_text())


def main():
    policy = read(ROOT / 'participant/workspace/policy.json')
    root_hash = verify_frozen_package()
    archive = ROOT / 'adversary/generation2_archive'
    archived = read(archive / 'archive_manifest.json')
    for relative, digest in archived['files'].items():
        assert hashlib.sha256((archive / relative).read_bytes()).hexdigest() == digest
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
    assert read(ROOT / 'status.json')['status'] == 'solved'
    assert policy['mean_gain_min'] == 0.070 and policy['worst_family_gain_min'] == 0.057
    combined = {'champion': [], 'lp_control': [], 'baseline': []}
    suites, bounds, rejected, clusters = {}, [], [], {'champion_execution': [], 'champion_infeasibility': [],
                                                     'champion_regression': [], 'champion_failed_suite': [],
                                                     'lp_control_internal_timeout': []}
    validations = {}
    for suite, (case_directory, champion_directory, lp_directory, baseline_directory) in GROUPS.items():
        manifest = read(PRIVATE / case_directory / 'manifest.json')
        rejected.extend(dict(row, suite=suite) for row in manifest.get('rejected', []))
        validation = read(PRIVATE / f'{suite}_validation.json')
        assert validation['passed'] and len(validation['rows']) == len(manifest['cases'])
        validations[suite] = validation
        suite_reports = {}
        for method, directory in [('champion', champion_directory), ('lp_control', lp_directory), ('baseline', baseline_directory)]:
            report = read(PRIVATE / directory / 'report.json')
            assert report['complete'] and len(report['rows']) == len(manifest['cases'])
            assert report['policy'] == policy and report['frozen_manifest_sha256'] == root_hash
            assert report['summary']['valid'] and report['summary']['resource_score'] == 1.0
            suite_reports[method] = report
            combined[method].extend(dict(row, case_id=f'{suite}/{row["case_id"]}') for row in report['rows'])
        champion = suite_reports['champion']
        if not champion['summary']['passed']:
            clusters['champion_failed_suite'].append(suite)
        for row in champion['rows']:
            if row.get('runtime', {}).get('error'):
                clusters['champion_execution'].append(f'{suite}/{row["case_id"]}')
            if not row['feasible']:
                clusters['champion_infeasibility'].append(f'{suite}/{row["case_id"]}')
            if row['gain'] < 0:
                clusters['champion_regression'].append(f'{suite}/{row["case_id"]}')
            diagnostic = read(PRIVATE / lp_directory / row['case_id'] / 'output/diagnostics.json')['lp']
            evidence = {'case_id': f'{suite}/{row["case_id"]}', 'family': row['family'],
                        'champion_gain': row['gain'], 'lp_success': diagnostic['success'], 'lp': diagnostic}
            if diagnostic['success']:
                evidence['remaining_gain_ceiling'] = diagnostic['upper_gain_bound'] - row['gain']
                assert evidence['remaining_gain_ceiling'] >= -1e-8
            else:
                clusters['lp_control_internal_timeout'].append(evidence['case_id'])
            bounds.append(evidence)
        assert all(abs(row['gain']) < 1e-12 for row in suite_reports['baseline']['rows'])
        suites[suite] = {method: report['summary'] for method, report in suite_reports.items()}
    summaries = {method: aggregate(rows, policy) for method, rows in combined.items()}
    assert summaries['champion']['passed']
    assert not any(clusters[name] for name in clusters if name.startswith('champion'))
    preflight = read(PRIVATE / 'replay_preflight.json')
    assert preflight['passed'] and all(preflight['controls'].values())
    passing_bounds = [row for row in bounds if row['lp_success']]
    wall_times = [row['runtime']['wall_seconds'] for row in combined['champion']]
    headroom = {'successful_relaxations': len(passing_bounds), 'unknown_relaxations': len(bounds) - len(passing_bounds),
                'maximum_remaining_gain_ceiling': max(row['remaining_gain_ceiling'] for row in passing_bounds),
                'method': 'Four-candidate vertex/edge/plaquette local-polytope LP with budget, anchors, Chern and admissibility; sign-clipped dual and box-residual correction.',
                'caution': 'Numerical floating-coefficient bounds, not interval certificates. Failed internal 35-second LP solves give no bound. Actual feasible champion outputs establish target attainment.'}
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    status = {'status': 'solved_no_ratchet', 'generation_preserved': 2, 'ready_for_fresh3': False,
              'generation3_created': False, 'fresh_agents_launched': 0, 'hardness_claim': False,
              'reason': 'No genuine champion failure in 23 valid scientific challenges, including independently seeded held-out cases and two topology-resolved narrow-gap refinements. Do not tighten thresholds merely to manufacture failure.',
              'completed_at_utc': timestamp, 'policy': policy, 'new_targets': None,
              'root_frozen_manifest_sha256': root_hash, 'root_package_and_archive_unchanged': True,
              'case_count': len(combined['champion']), 'family_count': len(summaries['champion']['families']),
              'champion': summaries['champion'], 'weak_baseline': summaries['baseline'],
              'independent_lp_control': summaries['lp_control'], 'suites': suites,
              'failure_clusters': clusters, 'generator_rejections': rejected,
              'headroom': headroom, 'champion_min_case_seconds': min(wall_times),
              'champion_max_case_seconds': max(wall_times),
              'validation_passed': True, 'isolation_preflight_passed': True,
              'invalid_controller_setup_runs': ['discovery_champion', 'discovery_lp_control'],
              'setup_error_note': 'Initial controller forgot to create the output parent; no solver launched in these two runs. They were fixed and excluded, not counted as champion failures.',
              'scientific_cautions': ['Synthetic lattice-Dirac acquisition proxies, not material-specific kdotpy/Kane simulations.',
                                      'Fixed four candidates, rank two in ambient dimension six, and four robust scenarios.',
                                      'Determinant-bundle Chern targets include -1, -2 and -3; no globally smooth frame is required.',
                                      'Candidate GL(2,C) frame invariance, common ambient unitary invariance, independent Wilson-loop scoring and 64-state exhaustive enumeration checked.',
                                      'Doubled-mesh Chern agreement is necessary here, not a proof of converged pointwise Berry curvature.',
                                      'The two refined meshes preserve Hamiltonian parameters and RNG seeds, not a continuum realization of acquisition noise.',
                                      'Wall runtime is hardware-sensitive; the largest observed runtime is near, but below, 90 seconds.',
                                      'The inherited 2-GiB restriction is RLIMIT_AS per process, not a cgroup-wide resident-memory measurement.']}
    (PRIVATE / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    (PRIVATE / 'headroom_summary.json').write_text(json.dumps({'summary': headroom, 'cases': bounds}, indent=2) + '\n')
    validation_report = {'passed': True, 'case_count': status['case_count'], 'suites': validations,
                         'isolation': preflight, 'archive_files_verified': len(archived['files']),
                         'frozen_package_unchanged': True, 'weak_baseline_zero_gain_all_cases': True}
    (PRIVATE / 'validation.json').write_text(json.dumps(validation_report, indent=2) + '\n')
    lines = ['# C1 champion–challenger review: no ratchet', '',
             'Generation 2 remains solved and byte-for-byte unchanged. No generation 3 is created or ready; no fresh agent was launched.', '',
             '## Fixed decision rule', '',
             'The inherited thresholds remain mean gain >= 0.070, worst-family gain >= 0.057, no case regression, and all cases feasible. No new targets are proposed. Every solver replay uses the unchanged evaluator isolation: 90 s/case, four CPU cores, and 2 GiB RLIMIT_AS.', '',
             '## Scores', '',
             '| Suite | Champion mean | Champion worst | Weak baseline | LP-control mean / worst |',
             '|---|---:|---:|---:|---:|']
    for suite, methods in suites.items():
        lines.append(f'| {suite} | {methods["champion"]["core_score"]:.10f} | {methods["champion"]["worst_family_score"]:.10f} | 0 | {methods["lp_control"]["core_score"]:.10f} / {methods["lp_control"]["worst_family_score"]:.10f} |')
    lines.extend(['', '| Combined family | Champion gain | Weak baseline gain |', '|---|---:|---:|'])
    for family, scores in summaries['champion']['families'].items():
        lines.append(f'| {family} | {scores["mean_gain"]:.10f} | 0 |')
    lines.extend(['', f'Combined champion: core_score={summaries["champion"]["core_score"]:.10f}, worst_family_score={summaries["champion"]["worst_family_score"]:.10f}, runtime_seconds={summaries["champion"]["runtime_seconds"]:.3f}, resource_score=1.0. All 23 outputs are feasible; per-case runtime is {min(wall_times):.3f}–{max(wall_times):.3f} s. Full reports include reason and all requested score fields.', '',
                  '## Failure clustering and headroom', '',
                  '- Champion execution, topology/budget/admissibility, regression and suite-threshold failure clusters are empty.',
                  '- Four regimes: near-inversion narrow gaps; spatially correlated opposing-scenario acquisition errors; nonuniform integer acquisition costs; doubled-winding Dirac textures with optional second nontrivial occupied block.',
                  '- Discovery has 11 valid cases and independent held-out has 10. Two unresolved narrow-gap seeds are recovered on 16x16 meshes without changing their Hamiltonian parameters. One held-out seed with the wrong Chern sector is excluded before replay. None of these construction defects counts as hardness.',
                  f'- {headroom["successful_relaxations"]} LP solves succeeded. The largest numerical upper bound on remaining improvement beyond the champion is {100 * headroom["maximum_remaining_gain_ceiling"]:.4f} percentage points of baseline-normalized gain. These are not interval-certified optimality claims.',
                  '- The simple LP control passes discovery and held-out. Its internal 35-second LP allowance expires on both refined meshes and it returns the baseline; these are control limitations, not champion failures. The champion achieves 11.443% and 11.550% gain on those same meshes within the official caps.',
                  '- No additional expensive portfolio is warranted after all champion suites pass. Existing champion outputs and the independent control constitute feasible witnesses; no cached answers are published.', '',
                  '## Validation and preservation', '',
                  '- Independent Wilson-loop scoring, candidate-frame gauge changes, baseline LP embeddings, original common-ambient-unitary test, and 64-state exhaustive enumeration pass.',
                  '- Eleven public-only dummy canary isolation checks pass, including private/sibling dummy denial, read-only input, environment cleaning, PID/network namespaces and numerical imports. No authentication files are read.',
                  '- Generation-2 participant, evaluator, frozen manifest and supporting metadata are archived in `../generation2_archive/`; all 44 archived files still match the root originals.',
                  '- Public participant, evaluator, cases, policy, root status, and frozen manifest have not been edited. All new work is confined to this private review and the requested archive.', '',
                  '## Replay commands', '',
                  'Run from concept_1. Use an escalated shell if the default sandbox hangs. Choose fresh output directories; replay refuses to overwrite existing evidence. Numerical dependencies are the existing NumPy/SciPy installation; the frozen champion uses its private native shared object only inside bwrap.', '',
                  '```bash',
                  'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 timeout 620 /usr/bin/python3 -B adversary/ratchet3/replay_challenges.py --cases adversary/ratchet3/discovery_cases --submission champions/generation_2/submission --output adversary/ratchet3/discovery_rerun --workers 2 > adversary/ratchet3/discovery_rerun.log 2>&1',
                  'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 timeout 1000 /usr/bin/python3 -B evaluator/evaluate.py --submission champions/generation_2/submission --split hidden --output adversary/ratchet3/original_hidden_rerun.json > adversary/ratchet3/original_hidden_rerun.log 2>&1',
                  '```', '',
                  'The first command reproduces the private challenge protocol; the second is the official unchanged generation-2 evaluator CLI, not a new generation-3 test. Each private worker uses four disjoint cores; two workers do not give one solver eight cores. Per-case stdout/stderr, output artifacts, source snapshots and hashes are retained beside each report.', '',
                  '## Scientific cautions', ''])
    lines.extend(f'- {caution}' for caution in status['scientific_cautions'])
    (PRIVATE / 'REPORT.md').write_text('\n'.join(lines) + '\n')
    hashes = {}
    for path in sorted(PRIVATE.rglob('*')):
        if path.is_file() and not path.is_symlink() and path.name != 'evidence_manifest.json':
            hashes[str(path.relative_to(PRIVATE))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (PRIVATE / 'evidence_manifest.json').write_text(json.dumps({'frozen_at_utc': timestamp, 'scope': 'private review evidence only; not a new task generation', 'sha256': hashes}, indent=2) + '\n')
    print(json.dumps({'status': status['status'], 'champion': summaries['champion'], 'headroom': headroom,
                      'private_evidence_files': len(hashes), 'root_unchanged': True}, indent=2))


if __name__ == '__main__':
    main()
