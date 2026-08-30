import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
sys.path.insert(0, str(ROOT / 'evaluator/hidden'))
from evaluate import build, measure
from oracle import geometric, dak_crosscheck, check


def make_challenge():
    generator = np.random.default_rng(610982714)
    cases, references = [], []
    cross_error = 0.0
    for family in ['soft_radiator', 'hierarchical_collinear', 'dense_radiator_collinear']:
        for sample in range(60):
            directions = generator.normal(size=(6, 3))
            directions /= np.linalg.norm(directions, axis=1, keepdims=True)
            axis = directions[0]
            tangent = directions[1] - np.dot(directions[1], axis) * axis
            tangent /= np.linalg.norm(tangent)
            opening = 10.0 ** generator.uniform(-10, -2)
            near = np.cos(opening) * axis + np.sin(opening) * tangent
            energy = 10.0 ** generator.uniform(-14.5, -5)
            if family == 'soft_radiator':
                spatial = np.array([energy * axis, 0.3 * directions[2], 0.4 * directions[3], 0.8 * directions[4]])
            elif family == 'hierarchical_collinear':
                spatial = np.array([energy * axis, 0.3 * near, 0.4 * directions[3], 0.8 * near])
                spatial[3] = 0.8 * (np.cos(opening * 1.3) * axis + np.sin(opening * 1.3) * tangent)
            else:
                spatial = np.array([0.9 * axis, 0.3 * directions[2], 0.4 * directions[3], 0.8 * near])
            spatial = np.vstack([spatial, -np.sum(spatial, axis=0)])
            energies = np.linalg.norm(spatial, axis=1)
            momenta = np.column_stack([spatial, energies]) / energies.sum()
            scale = 10.0 ** generator.uniform(-85, 85)
            momenta *= scale
            permutation = generator.permutation(5)
            labels = [int(np.where(permutation == index)[0][0] + 1) for index in range(5)]
            case = {'id': f'{family}-{sample:03d}', 'family': family,
                    'p': momenta[permutation].tolist(), 'labels': labels,
                    'slots': list(map(int, generator.permutation(3) + 1)),
                    'axis': [*directions[5], 1.0]}
            reference = geometric(case, 140)
            higher = geometric(case, 190)
            expected = dak_crosscheck(case, 160)
            total = float(momenta[:, 3].sum())
            disagreement = max(float(np.max(np.abs(expected - np.asarray(reference['mapped'])[case['slots'][0]-1])) / total),
                               float(np.max(np.abs(np.asarray(higher['mapped']) - reference['mapped'])) / total))
            assert disagreement < 2e-13
            cross_error = max(cross_error, disagreement)
            cases.append(case)
            references.append(reference)
    destination = ROOT / 'adversary/domain_challenge'
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    (destination / 'references.json').write_text(json.dumps(references, indent=2) + '\n')
    (destination / 'validation.json').write_text(json.dumps({'cases': len(cases), 'max_crosscheck_error': cross_error,
        'precision_digits': [140, 160, 190], 'source_domain': 'combinations of already-published soft radiator, near-parallel, relabel, and scale ranges'}, indent=2) + '\n')
    print('prepared', len(cases), 'independently validated physical cases')


def score(artifact, report_path, challenge=None):
    destination = Path(challenge) if challenge else ROOT / 'adversary/domain_challenge'
    cases = json.loads((destination / 'cases.json').read_text())
    references = json.loads((destination / 'references.json').read_text())
    target = json.loads((ROOT / 'evaluator/hidden/target.json').read_text())
    with tempfile.TemporaryDirectory(prefix='eerad3-domain-') as directory:
        candidate_dir, baseline_dir = Path(directory) / 'candidate', Path(directory) / 'baseline'
        candidate_dir.mkdir()
        baseline_dir.mkdir()
        candidate = build(artifact, candidate_dir)
        baseline = build(ROOT / 'evaluator/hidden/pristine', baseline_dir)
        rows, candidate_cpu, candidate_trials = measure(candidate, cases, target['timing_repeats'])
        unused, baseline_cpu, baseline_trials = measure(baseline, cases, target['timing_repeats'])
    failures, families = [], {}
    for case, reference, row in zip(cases, references, rows):
        errors = check(case, reference, row, target)
        families.setdefault(case['family'], []).append(not errors)
        if errors:
            failures.append({'id': case['id'], 'checks': errors})
    scores = {name: float(np.mean(values)) for name, values in families.items()}
    ratio = candidate_cpu / baseline_cpu
    result = {'core_score': float(np.mean(list(scores.values()))), 'worst_family_score': min(scores.values()),
              'family_scores': scores, 'failed_case_count': len(failures), 'failures': failures,
              'runtime_ratio': ratio, 'runtime_ratio_limit': target['runtime_ratio_limit'],
              'runtime_score': min(1.0, target['runtime_ratio_limit'] / ratio),
              'passed': not failures and ratio <= target['runtime_ratio_limit'],
              'candidate_cpu_seconds': candidate_cpu, 'baseline_cpu_seconds': baseline_cpu,
              'candidate_trials': candidate_trials, 'baseline_trials': baseline_trials}
    Path(report_path).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({name: value for name, value in result.items() if name != 'failures'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact')
    parser.add_argument('--report')
    parser.add_argument('--challenge')
    arguments = parser.parse_args()
    if arguments.artifact:
        score(arguments.artifact, arguments.report, arguments.challenge)
    else:
        make_challenge()
