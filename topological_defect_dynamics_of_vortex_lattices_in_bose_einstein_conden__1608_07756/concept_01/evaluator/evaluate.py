import argparse
import csv
import hashlib
import json
import math
import os
import resource
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment


HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parent
sys.path.insert(0, str(CONCEPT / 'solution/workspace'))
from cores import detect
from current import measure
from model import Model
from order import characterize


def rows(path):
    with open(path) as stream:
        return list(csv.DictReader(stream))


def lookup(table):
    return {(row['case'], int(row['frame'])): row for row in table}


def finite(value):
    return np.all(np.isfinite(np.asarray(value, dtype=float)))


def decay(error, scale):
    return float(np.exp(-min(700, max(0, float(error)) / scale)))


def vortex_score(predicted, target):
    predicted = np.asarray(predicted, dtype=float).reshape(-1, 3)
    target = np.asarray(target, dtype=float).reshape(-1, 3)
    if not finite(predicted):
        return 0.0
    total = len(predicted) + len(target)
    if not total:
        return 1.0
    quality = 0.0
    for charge in [-1, 1]:
        first = predicted[predicted[:, 2] == charge, :2]
        second = target[target[:, 2] == charge, :2]
        if len(first) and len(second):
            distances = np.linalg.norm(first[:, None] - second[None], axis=-1)
            row, column = linear_sum_assignment(distances)
            quality += np.exp(-distances[row, column] / 0.16).sum()
    return float(2 * quality / total)


def topology_score(predicted, target):
    predicted_counts = np.asarray(predicted['counts'], dtype=float)
    target_counts = np.asarray(target['counts'], dtype=float)
    counts_error = np.abs(predicted_counts - target_counts).sum() / max(target_counts.sum(), 5)
    correlations_error = np.mean(np.abs(np.asarray(predicted['correlations']) - target['correlations']))
    pair_error = np.abs(np.asarray(predicted['pair_counts']) - target['pair_counts']).sum() / max(sum(target['pair_counts']), 5)
    radius_error = abs(predicted['defect_radius'] - target['defect_radius']) / max(target['defect_radius'], 2)
    return 0.40 * decay(counts_error, 0.4) + 0.35 * decay(correlations_error, 0.13) + 0.10 * decay(pair_error, 0.25) + 0.15 * decay(radius_error, 0.5)


def physics_score(predicted, target):
    denominator = max(target['Ec'] + target['Ei'] + target['Eq'], 1e-8)
    energy_error = sum(abs(predicted[key] - target[key]) for key in ['Ec', 'Ei', 'Eq']) / denominator
    spectral_error = sum(np.abs(np.asarray(predicted[key]) - target[key]).sum() for key in ['Ec_bins', 'Ei_bins']) / denominator
    hamiltonian_error = abs(predicted['energy'] - target['energy']) / max(abs(target['energy']), 1)
    moment_error = abs(predicted['r2'] - target['r2']) / max(abs(target['r2']), 1)
    norm_error = abs(predicted['norm'] - target['norm'])
    return 0.38 * decay(energy_error, 0.13) + 0.32 * decay(spectral_error, 0.16) + 0.12 * decay(hamiltonian_error, 0.015) + 0.10 * decay(moment_error, 0.015) + 0.08 * decay(norm_error, 0.002)


def scalar_record(cores, topology, physics, model):
    selected = model.sample(model.bulk, cores[:, :2])
    record = {key: physics[key] for key in ['norm', 'r2', 'energy', 'Ec', 'Ei', 'Eq']}
    record.update(nplus=int(np.sum(selected & (cores[:, 2] > 0))), nminus=int(np.sum(selected & (cores[:, 2] < 0))))
    record.update({f'n{coordination}': topology['counts'][coordination] for coordination in [5, 6, 7]})
    record.update(g6_near=topology['correlations'][0], g6_far=topology['correlations'][-1], defect_radius=topology['defect_radius'])
    return record


def evaluate_case(case, output, truth, case_alias):
    with np.load(HERE / 'hidden' / case['asset']) as arrays:
        model = Model(case, arrays)
    with np.load(output / (case_alias + '.npz')) as arrays:
        prediction = arrays['psi']
        predicted_times = arrays['times']
    with np.load(truth / (case['id'] + '.npz')) as arrays:
        reference = arrays['psi']
    if prediction.shape != reference.shape or not np.allclose(predicted_times, case['times'], atol=1e-12):
        raise ValueError('Output field shape or sample times violate the public contract')
    if not np.all(np.isfinite(prediction)):
        raise ValueError('Non-finite wavefunction')
    diagnostics = json.loads((output / (case_alias + '.json')).read_text())
    reference_diagnostics = json.loads((truth / (case['id'] + '.json')).read_text())
    reported = lookup(rows(output / 'results.csv'))
    scores = []
    errors = []
    for frame_index, (predicted, target, diagnostic, exact) in enumerate(zip(prediction, reference, diagnostics, reference_diagnostics)):
        overlap = np.vdot(target, predicted)
        aligned = predicted * np.exp(-1j * np.angle(overlap))
        field_error = np.linalg.norm(aligned - target) / np.linalg.norm(target)
        density_error = np.linalg.norm(np.abs(predicted) ** 2 - np.abs(target) ** 2) / np.linalg.norm(np.abs(target) ** 2)
        state = 0.5 * decay(field_error, 0.06) + 0.5 * decay(density_error, 0.06)
        core = vortex_score(diagnostic['cores'], exact['cores'])
        topology = topology_score(diagnostic['topology'], exact['topology'])
        physics = physics_score(diagnostic['physics'], exact['physics'])
        measured_cores = detect(predicted, model)
        measured_topology = characterize(measured_cores, model)
        measured_physics = measure(predicted, model, case['times'][frame_index])
        consistency = (vortex_score(diagnostic['cores'], measured_cores) + topology_score(diagnostic['topology'], measured_topology) + physics_score(diagnostic['physics'], measured_physics)) / 3
        expected_scalars = scalar_record(np.asarray(diagnostic['cores']).reshape(-1, 3), diagnostic['topology'], diagnostic['physics'], model)
        report = reported[(case_alias, frame_index)]
        table_errors = [abs(float(report[key]) - value) / max(1, abs(value)) for key, value in expected_scalars.items()]
        table_consistency = decay(max(table_errors), 0.0001)
        combined = (0.42 * state + 0.15 * core + 0.18 * topology + 0.25 * physics) * (0.75 + 0.25 * consistency) * (0.90 + 0.10 * table_consistency)
        if frame_index > 0:
            scores.append(combined)
        errors.append(dict(time=case['times'][frame_index], field_error=float(field_error), density_error=float(density_error), state=state, signed_cores=core, topology=topology, kinetic_physics=physics, raw_consistency=consistency, table_consistency=table_consistency))
    if len(diagnostics) != len(case['times']):
        raise ValueError('Missing frame diagnostics')
    return dict(score=float(np.mean(scores)), frames=errors)


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (300, 305))


def run_submission(submission, manifest, output, config, timeout=300):
    environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONNOUSERSITE='1')
    started = time.perf_counter()
    with open(output.parent / (output.name + '_stdout.log'), 'w') as log:
        process = subprocess.run(['bash', str(submission / 'run.sh'), str(manifest), str(output), str(config)], cwd=submission, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, preexec_fn=limits)
    elapsed = time.perf_counter() - started
    if process.returncode:
        raise RuntimeError(f'Entry point failed with exit status {process.returncode}')
    return elapsed


def numerical_table_equal(first, second):
    first, second = lookup(first), lookup(second)
    if set(first) != set(second):
        return False
    for key in first:
        for column, value in first[key].items():
            if column == 'case':
                continue
            if column not in second[key] or not np.isclose(float(value), float(second[key][column]), rtol=1e-6, atol=1e-8):
                return False
    return True


def audit_evidence(submission, rerun):
    checks, details = {}, {}
    required = ['run.sh', 'workspace', 'config.json', 'ablation_config.json', 'refinement_config.json', 'results.csv', 'ablation.csv', 'scaling.csv', 'claims.json', 'report.md', 'figures/primary_result.png', 'figures/robustness_or_scaling.png']
    checks['artifacts'] = all((submission / name).exists() for name in required)
    for variant, table in [('primary', 'results.csv'), ('ablation', 'ablation.csv')]:
        try:
            checks[variant + '_table_copy'] = numerical_table_equal(rows(submission / table), rows(submission / 'experiments' / variant / 'results.csv'))
        except Exception as error:
            checks[variant + '_table_copy'] = False
            details[variant] = str(error)
    try:
        checks['public_reproducibility'] = numerical_table_equal(rows(submission / 'results.csv'), rows(rerun / 'results.csv'))
    except Exception as error:
        checks['public_reproducibility'] = False
        details['public_reproducibility'] = str(error)
    for variant, rerun_name in [('primary', 'public_rerun'), ('ablation', 'ablation_rerun'), ('refinement', 'refinement_rerun')]:
        try:
            saved = submission / 'experiments' / variant
            regenerated = rerun.parent / rerun_name
            checks[variant + '_rerun_tables'] = numerical_table_equal(rows(saved / 'results.csv'), rows(regenerated / 'results.csv'))
            case_ids = set(row['case'] for row in rows(saved / 'results.csv'))
            raw_ok = True
            for case_id in case_ids:
                with np.load(saved / (case_id + '.npz')) as first, np.load(regenerated / (case_id + '.npz')) as second:
                    raw_ok &= np.allclose(first['times'], second['times'], atol=1e-12)
                    raw_ok &= np.allclose(np.abs(first['psi']) ** 2, np.abs(second['psi']) ** 2, rtol=1e-5, atol=1e-9)
                raw_ok &= json.loads((saved / (case_id + '.json')).read_text()) == json.loads((regenerated / (case_id + '.json')).read_text())
            checks[variant + '_raw_reproducibility'] = bool(raw_ok)
        except Exception as error:
            checks[variant + '_rerun_tables'] = False
            checks[variant + '_raw_reproducibility'] = False
            details[variant + '_rerun'] = str(error)
    try:
        configs = [json.loads((submission / name).read_text()) for name in ['config.json', 'ablation_config.json', 'refinement_config.json']]
        primary = rows(submission / 'results.csv')
        alternate = rows(submission / 'ablation.csv')
        checks['distinct_ablation'] = configs[0] != configs[1] and not numerical_table_equal(primary, alternate)
        checks['refinement_exists'] = configs[0] != configs[2] and bool(rows(submission / 'experiments/refinement/results.csv'))
        checks['scaling_records'] = set(row['variant'] for row in rows(submission / 'scaling.csv')) == {'primary', 'ablation', 'refinement'} and all(float(row['wall_seconds']) > 0 and float(row['max_rss_kib']) > 0 for row in rows(submission / 'scaling.csv'))
    except Exception as error:
        checks.update(distinct_ablation=False, refinement_exists=False, scaling_records=False)
        details['configurations'] = str(error)
    try:
        claims = json.loads((submission / 'claims.json').read_text())
        claims_ok = len(claims) >= 2
        for claim in claims:
            values = []
            for evidence in claim['evidence']:
                table = lookup(rows(submission / evidence['table']))
                values.append(float(table[(evidence['case'], int(evidence['frame']))][evidence['column']]))
            comparison = claim['comparison']
            calculated = values[0] - values[1] if comparison == 'difference' else values[0] / values[1]
            claims_ok &= comparison in ['difference', 'ratio'] and math.isfinite(claim['value']) and bool(claim['statement']) and np.isclose(calculated, claim['value'], rtol=1e-5, atol=1e-8)
        checks['quantitative_claims'] = bool(claims_ok)
    except Exception as error:
        checks['quantitative_claims'] = False
        details['claims'] = str(error)
    try:
        from PIL import Image
        for name in ['primary_result.png', 'robustness_or_scaling.png']:
            with Image.open(submission / 'figures' / name) as image:
                image.verify()
        checks['figures_readable'] = True
    except Exception:
        checks['figures_readable'] = False
    return dict(score=float(np.mean(list(checks.values()))), checks=checks, details=details)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skip-evidence', action='store_true')
    arguments = parser.parse_args()
    submission = arguments.submission.resolve()
    work = HERE / 'runs' / uuid.uuid4().hex[:12]
    work.mkdir(parents=True)
    manifest = json.loads((HERE / 'hidden/manifest.json').read_text())
    aliases = {}
    staged = []
    for index, case in enumerate(manifest['cases']):
        alias = 'sample_' + uuid.uuid4().hex[:8]
        asset = 'state_' + uuid.uuid4().hex[:8] + '.npz'
        shutil.copyfile(HERE / 'hidden' / case['asset'], work / asset)
        aliases[case['id']] = alias
        staged.append(dict(case, id=alias, asset=asset))
    (work / 'manifest.json').write_text(json.dumps(dict(cases=staged), indent=2))
    result = dict(submission=str(submission), work_directory=str(work), per_family={}, infrastructure_error=None)
    try:
        elapsed = run_submission(submission, work / 'manifest.json', work / 'outputs', submission / 'config.json')
        result['runtime_seconds'] = elapsed
        result['measured_peak_rss_kib'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        for case in manifest['cases']:
            try:
                result['per_family'][case['id']] = evaluate_case(case, work / 'outputs', HERE / 'hidden/truth', aliases[case['id']])
            except Exception as error:
                result['per_family'][case['id']] = dict(score=0.0, output_error=repr(error))
        values = [case['score'] for case in result['per_family'].values()]
        result['mean_family_score'] = float(np.mean(values))
        result['minimum_family_score'] = float(min(values))
        result['core_score'] = 0.7 * result['mean_family_score'] + 0.3 * result['minimum_family_score']
        result['resource_score'] = 1 / (1 + (elapsed / 120) ** 2)
        scaling = rows(work / 'outputs/scaling.csv')
        result['reported_peak_rss_kib'] = max(float(row['max_rss_kib']) for row in scaling)
        if arguments.skip_evidence:
            result['evidence'] = dict(score=0, skipped=True)
        else:
            try:
                result['public_rerun_seconds'] = run_submission(submission, CONCEPT / 'participant/v_02/input/campaign.json', work / 'public_rerun', submission / 'config.json')
            except Exception as error:
                result['public_rerun_error'] = repr(error)
            for variant, config_name in [('ablation', 'ablation_config.json'), ('refinement', 'refinement_config.json')]:
                try:
                    result[variant + '_rerun_seconds'] = run_submission(submission, CONCEPT / 'participant/v_02/input/campaign.json', work / (variant + '_rerun'), submission / config_name)
                except Exception as error:
                    result[variant + '_rerun_error'] = repr(error)
            result['evidence'] = audit_evidence(submission, work / 'public_rerun')
        result['overall_score'] = 0.85 * result['core_score'] + 0.10 * result['resource_score'] + 0.05 * result['evidence']['score']
    except Exception as error:
        result.update(core_score=0.0, overall_score=0.0, execution_error=repr(error))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({key: value for key, value in result.items() if key != 'per_family'}, indent=2))
    print(json.dumps({key: value['score'] for key, value in result['per_family'].items()}, indent=2))


if __name__ == '__main__':
    main()
