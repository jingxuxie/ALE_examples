from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
sys.path.insert(0, str(ROOT / 'evaluator/hidden'))
sys.path.insert(0, str(ROOT / 'adversary'))
from evaluate import build, run
from oracle import check, geometric, dak_crosscheck
from conditioned_cases import validate_case
from prepare_generation_2 import digest, put

DESTINATION = ROOT / 'adversary/champion_quality_search'
DEADLINE = datetime.fromisoformat('2026-08-28T13:37:40+00:00').timestamp()


def cases_for(seed, samples=1500):
    generator = np.random.default_rng(seed)
    result = []
    for family in ['ultrasoft_offset', 'ultrasoft_near', 'threshold_soft', 'threshold_asymmetric']:
        for sample in range(samples):
            axis = generator.normal(size=3)
            axis /= np.linalg.norm(axis)

            def near(direction, opening):
                tangent = generator.normal(size=3)
                tangent -= np.dot(tangent, direction) * direction
                tangent /= np.linalg.norm(tangent)
                return np.cos(opening) * direction + np.sin(opening) * tangent

            fraction = generator.uniform(0.25, 0.75)
            hard_opening = 10.0 ** generator.uniform(-12, -7)
            radiator_opening = 10.0 ** generator.uniform(-9.97, -3)
            radiator_offset = 10.0 ** generator.uniform(-3, 0.35)
            soft = 2 * 10.0 ** generator.uniform(-15.97, -10, size=2)
            if family == 'ultrasoft_offset' and sample < 300:
                hard_opening = 10.0 ** generator.uniform(-12, -11.6)
                radiator_opening = 10.0 ** generator.uniform(-9.98, -9.7)
                radiator_offset = 10.0 ** generator.uniform(-3.1, -2.9)
                soft = 2 * 10.0 ** generator.uniform(-15.97, -15.7, size=2)
            if family == 'ultrasoft_near':
                radiator_offset = 10.0 ** generator.uniform(-12, -3)
            if family.startswith('threshold'):
                hard_opening = np.sqrt(4e-6 / (fraction * (1 - fraction))) * 10.0 ** generator.uniform(-0.5, 0.5)
                if family == 'threshold_asymmetric':
                    soft[generator.integers(0, 2)] = 10.0 ** generator.uniform(-8, -2)
            radiator = near(axis, radiator_offset)
            directions = [radiator, axis, near(axis, hard_opening), near(radiator, radiator_opening)]
            energies = np.array([soft[0], fraction, 1 - fraction, soft[1]])
            spatial = energies[:, None] * directions
            spatial = np.vstack([spatial, -spatial.sum(axis=0)])
            norms = np.linalg.norm(spatial, axis=1)
            momenta = np.column_stack([spatial, norms]) / norms.sum()
            momenta *= 10.0 ** generator.uniform(-90, 90)
            permutation = generator.permutation(5)
            result.append({'id': f'{family}-{seed}-{sample:04d}', 'family': 'quality_' + family,
                'p': momenta[permutation].tolist(),
                'labels': [int(np.where(permutation == index)[0][0] + 1) for index in range(5)],
                'slots': list(map(int, generator.permutation(3) + 1)),
                'axis': [*axis, 1.0]})
    return result


def error_ratios(case, reference, record, target):
    if not np.isfinite(record).all():
        return {'nonfinite': True}
    raw = np.asarray(case['p'])
    energy = raw[:, 3].sum()
    mapped = record[25:37].reshape(3, 4) / energy
    left = raw[case['labels'][0] - 1, :3]
    right = raw[case['labels'][3] - 1, :3]
    left = left / np.max(np.abs(left))
    right = right / np.max(np.abs(right))
    chord = np.linalg.norm(left / np.linalg.norm(left) - right / np.linalg.norm(right))
    slack = 16 * np.finfo(float).eps / chord if chord < 1e-4 else 0.0
    error = float(np.max(np.abs(mapped - np.asarray(reference['mapped']) / energy)))
    tolerance = target['momentum_atol'] + slack
    return {'nonfinite': False, 'component_error_over_q': error, 'component_tolerance_over_q': tolerance,
            'component_ratio': error / tolerance,
            'mapped_invariant_ratio': float(np.max(np.abs(record[37:40] - reference['s']))) /
                                      (target['mapped_invariant_atol'] + 2 * slack),
            'shell_ratio': float(np.max(np.abs(mapped[:, 3]**2 - np.sum(mapped[:, :3]**2, axis=1)))) / target['shell_atol'],
            'conservation_ratio': float(np.max(np.abs(mapped.sum(axis=0) - raw.sum(axis=0) / energy))) / target['conservation_atol']}


def main():
    started = time.time()
    if started >= DEADLINE:
        raise RuntimeError('Bounded search deadline already reached')
    DESTINATION.mkdir(exist_ok=True)
    target = json.loads((ROOT / 'adversary/generation_1_snapshot/evaluator/hidden/target.json').read_text())
    artifact = ROOT / 'champions/generation_1/workspace'
    source_hashes = {name: digest(artifact / name) for name in ['kinematics.f', 'phaseee.f', 'eerad3lib.f']}
    result = {'artifact': str(artifact.relative_to(ROOT)), 'source_sha256': source_hashes,
              'started_utc': datetime.now(timezone.utc).isoformat(), 'deadline_utc': '2026-08-28T13:37:40+00:00',
              'quality_only': True, 'tested_native_cases': 0, 'oracle_cases_checked': 0, 'robust_failures': []}
    with tempfile.TemporaryDirectory(prefix='eerad3-quality-search-') as temporary:
        executable = build(artifact, Path(temporary))
        for seed in [98324761, 98324762]:
            if time.time() > DEADLINE - 45:
                break
            cases = cases_for(seed)
            records, ignored_cpu = run(executable, cases)
            result['tested_native_cases'] += len(cases)
            energy = np.array([sum(vector[3] for vector in case['p']) for case in cases])
            mapped = records[:, 25:37].reshape(len(cases), 3, 4) / energy[:, None, None]
            with np.errstate(all='ignore'):
                physical = np.max(np.abs(mapped[:, :, 3]**2 - np.sum(mapped[:, :, :3]**2, axis=2)), axis=1) / target['shell_atol']
                physical = np.where(np.isfinite(records).all(axis=1), physical, np.inf)
            finite_order = sorted(np.where(np.isfinite(physical))[0], key=lambda index: -physical[index])
            nonfinite_order = list(np.where(~np.isfinite(physical))[0])
            order = list(dict.fromkeys(finite_order[:96] + nonfinite_order[:16] + list(range(300))
                                      + list(range(0, len(cases), 11))))
            print('native batch', seed, 'cases', len(cases), 'nonfinite', len(nonfinite_order),
                  'maximum finite shell ratio', max((physical[index] for index in finite_order), default=0), flush=True)
            put(DESTINATION / f'cases_{seed}.json', cases)
            np.save(DESTINATION / f'records_{seed}.npy', records)
            for index in order:
                if time.time() > DEADLINE - 25:
                    break
                case = cases[index]
                reference = geometric(case, 190)
                result['oracle_cases_checked'] += 1
                errors = check(case, reference, records[index], target)
                if not errors:
                    continue
                ratios = error_ratios(case, reference, records[index], target)
                if not ratios['nonfinite'] and max(value for name, value in ratios.items() if name.endswith('_ratio')) <= 2:
                    continue
                confirmed, properties = validate_case(case)
                higher = geometric(case, 240)
                direct = dak_crosscheck(case, 220)
                scale = sum(vector[3] for vector in case['p'])
                assert np.max(np.abs(np.asarray(confirmed['mapped']) - higher['mapped'])) / scale < 1e-20
                assert np.max(np.abs(np.asarray(confirmed['mapped'])[case['slots'][0] - 1] - direct)) / scale < 1e-20
                witness = {'case': case, 'reference': confirmed, 'record': records[index].tolist() if np.isfinite(records[index]).all() else None,
                           'errors': errors, 'ratios': ratios, 'domain_and_oracle': properties}
                result['robust_failures'].append(witness)
                print('VALIDATED CHAMPION FAILURE', case['id'], errors, ratios, properties, flush=True)
                put(DESTINATION / 'report.json', result)
                if len(result['robust_failures']) >= 6 and any(not item['ratios']['nonfinite'] for item in result['robust_failures']):
                    break
            if result['robust_failures']:
                break
    result['elapsed_seconds'] = time.time() - started
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    result['resource_ratchet_unchanged_no_go'] = True
    put(DESTINATION / 'report.json', result)
    print('QUALITY SEARCH DONE', result['tested_native_cases'], result['oracle_cases_checked'],
          'robust failures', len(result['robust_failures']), 'seconds', result['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
