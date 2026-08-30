import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import mpmath as mp
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
sys.path.insert(0, str(ROOT / 'evaluator/hidden'))
from oracle import check, dak_crosscheck, geometric

FAMILIES = ['light_balanced', 'light_hierarchical', 'light_soft_radiator',
            'light_double_soft', 'light_soft_pair', 'light_nested',
            'light_transition', 'light_transition_soft', 'light_transition_double_soft']


def rest_frame_reference(case, digits=180):
    with mp.workdps(digits):
        spatial = [[mp.mpf(value) for value in vector[:3]] for vector in case['p']]
        energies = [mp.sqrt(mp.fsum(value**2 for value in vector)) for vector in spatial]
        energy = mp.fsum(energies)
        vectors = [[value / energy for value in vector] + [norm / energy]
                   for vector, norm in zip(spatial, energies)]
        antenna = [vectors[index - 1] for index in case['labels'][:4]]
        total = [mp.fsum(vector[component] for vector in antenna) for component in range(4)]

        def euclidean(left, right):
            return mp.fsum(first * second for first, second in zip(left[:3], right[:3]))

        def pair(left, right):
            chord = mp.fsum((left[component] / left[3] - right[component] / right[3])**2
                           for component in range(3))
            return left[3] * right[3] * chord

        pairs = [[pair(left, right) for right in antenna] for left in antenna]
        mass = mp.sqrt(mp.fsum(pairs[first][second] for first in range(4) for second in range(first)))
        weight1 = (pairs[1][3] + pairs[1][2]) / (pairs[0][1] + pairs[1][3] + pairs[1][2])
        weight2 = pairs[2][3] / (pairs[0][2] + pairs[2][3] + pairs[1][2])

        def boost(vector, sign):
            projection = euclidean(total, vector)
            coefficient = projection / (mass * (total[3] + mass)) + sign * vector[3] / mass
            return [vector[component] + coefficient * total[component] for component in range(3)] + [
                (total[3] * vector[3] + sign * projection) / mass]

        radiator, first, second, recoil = [boost(vector, -1) for vector in antenna]
        direction = [radiator[component] / radiator[3] - recoil[component] / recoil[3]
                     for component in range(3)]
        norm = mp.sqrt(euclidean(direction, direction))
        direction = [value / norm for value in direction]
        recoil_weight = (mass / 2 - weight1 * first[3] - weight2 * second[3]) / recoil[3]
        origin = [weight1 * first[component] + weight2 * second[component] + recoil_weight * recoil[component]
                  for component in range(3)]
        projection = euclidean(origin, direction)
        transverse = [value - projection * axis for value, axis in zip(origin, direction)]
        radius_squared = mass**2 / 4 - euclidean(transverse, transverse)
        if radius_squared <= 0:
            raise AssertionError('Nonpositive rest-frame sphere intersection')
        radius = mp.sqrt(radius_squared)
        mapped_first = boost([value + radius * axis for value, axis in zip(transverse, direction)] + [mass / 2], 1)
        mapped_second = [value - first_value for value, first_value in zip(total, mapped_first)]
        mapped = [None] * 3
        for slot, vector in zip(case['slots'], [mapped_first, mapped_second, vectors[case['labels'][4] - 1]]):
            mapped[slot - 1] = vector
        residual = max(abs(vector[3]**2 - euclidean(vector, vector)) for vector in mapped)
        if residual > mp.mpf('1e-80') or min(vector[3] for vector in mapped) <= 0:
            raise AssertionError('Rest-frame oracle physical residual')
        radiator_chord = mp.sqrt(mp.fsum((antenna[0][component] / antenna[0][3]
                                       - antenna[3][component] / antenna[3][3])**2 for component in range(3)))
        return [[float(value * energy) for value in vector] for vector in mapped], {
            'rest_frame_shell_residual': float(residual),
            'antenna_mass_squared_over_q_squared': float(mass**2),
            'radiator_chord': float(radiator_chord),
            'minimum_energy_fraction': float(min(vector[3] for vector in vectors))}


def validate_case(case):
    reference = geometric(case, 140)
    higher = geometric(case, 190)
    direct = dak_crosscheck(case, 160)
    rest, properties = rest_frame_reference(case)
    energy = sum(vector[3] for vector in case['p'])
    error = max(float(np.max(np.abs(np.asarray(reference['mapped']) - higher['mapped'])) / energy),
                float(np.max(np.abs(np.asarray(reference['mapped']) - rest)) / energy),
                float(np.max(np.abs(np.asarray(reference['mapped'])[case['slots'][0] - 1] - direct)) / energy))
    raw = np.asarray(case['p']) / energy
    cm_error = float(np.max(np.abs(raw[:, :3].sum(axis=0))))
    shell_error = float(np.max(np.abs(raw[:, 3] - np.linalg.norm(raw[:, :3], axis=1))))
    if error > 2e-13 or cm_error > 2e-15 or shell_error > 2e-15 or np.min(raw[:, 3]) <= 0:
        raise AssertionError((case['id'], error, cm_error, shell_error))
    properties.update(oracle_disagreement=error, input_cm_residual=cm_error, input_null_residual=shell_error)
    return reference, properties


def make_cases(seed=804371927, samples=180):
    generator = np.random.default_rng(seed)
    cases = []
    for family in FAMILIES:
        for sample in range(samples):
            directions = generator.normal(size=(5, 3))
            directions /= np.linalg.norm(directions, axis=1, keepdims=True)
            axis = directions[0]

            def near(angle, selector):
                tangent = directions[selector] - np.dot(directions[selector], axis) * axis
                tangent /= np.linalg.norm(tangent)
                return np.cos(angle) * axis + np.sin(angle) * tangent

            opening = 10.0 ** generator.uniform(-10, -4)
            radiator_opening = opening
            first_opening, second_opening = opening, 1.3 * opening
            energies = np.array([0.9, 0.3, 0.4, 0.8])
            if family == 'light_hierarchical':
                first_opening = 10.0 ** generator.uniform(-8, -3.5)
                second_opening = 1.3 * first_opening
                radiator_opening = 10.0 ** generator.uniform(-10, -8)
            if family in ['light_soft_radiator', 'light_double_soft']:
                energies[0] *= 10.0 ** generator.uniform(-14, -3)
                radiator_opening = 10.0 ** generator.uniform(-10, -4)
            if family == 'light_double_soft':
                energies[3] *= 10.0 ** generator.uniform(-14, -3)
            if family == 'light_soft_pair':
                energies[1:3] *= 10.0 ** generator.uniform(-14, -3, size=2)
                first_opening, second_opening = 10.0 ** generator.uniform(-12, -4, size=2)
            if family == 'light_nested':
                first_opening = 10.0 ** generator.uniform(-12, -8)
                second_opening = 10.0 ** generator.uniform(-12, -4)
                energies[generator.integers(0, 4)] *= 10.0 ** generator.uniform(-14, 0)
            if family.startswith('light_transition'):
                first_opening = 10.0 ** generator.uniform(-3.2, -1.4)
                second_opening = 1.3 * first_opening
                radiator_opening = 10.0 ** generator.uniform(-10, -6)
                if family != 'light_transition':
                    energies[0] *= 10.0 ** generator.uniform(-14, -3)
                if family == 'light_transition_double_soft':
                    energies[3] *= 10.0 ** generator.uniform(-14, -3)
            spatial = energies[:, None] * np.array([axis, near(first_opening, 1),
                                                   near(second_opening, 2), near(radiator_opening, 3)])
            spatial = np.vstack([spatial, -spatial.sum(axis=0)])
            norms = np.linalg.norm(spatial, axis=1)
            momenta = np.column_stack([spatial, norms]) / norms.sum()
            momenta *= 10.0 ** generator.uniform(-85, 85)
            permutation = generator.permutation(5)
            cases.append({'id': f'{family}-{sample:04d}', 'family': family,
                          'p': momenta[permutation].tolist(),
                          'labels': [int(np.where(permutation == index)[0][0] + 1) for index in range(5)],
                          'slots': list(map(int, generator.permutation(3) + 1)),
                          'axis': [*directions[4], 1.0]})
    return cases


def write_challenge(destination, seed, samples):
    cases = make_cases(seed, samples)
    references, properties = [], []
    for index, case in enumerate(cases):
        reference, diagnostic = validate_case(case)
        references.append(reference)
        properties.append({'id': case['id'], **diagnostic})
        if (index + 1) % 180 == 0:
            print('independently validated', index + 1, flush=True)
    destination.mkdir(parents=True, exist_ok=True)
    for name, content in [('cases', cases), ('references', references), ('properties', properties)]:
        (destination / (name + '.json')).write_text(json.dumps(content, indent=2, allow_nan=False) + '\n')
    report = {'seed': seed, 'samples_per_family': samples, 'case_count': len(cases),
              'families': dict(Counter(case['family'] for case in cases)),
              'case_sha256': hashlib.sha256((destination / 'cases.json').read_bytes()).hexdigest(),
              'reference_sha256': hashlib.sha256((destination / 'references.json').read_bytes()).hexdigest(),
              'precision_digits': {'geometric': [140, 190], 'direct_DAK': 160, 'rest_frame_sphere': 180},
              'max_oracle_disagreement': max(item['oracle_disagreement'] for item in properties),
              'max_input_cm_residual': max(item['input_cm_residual'] for item in properties),
              'max_input_null_residual': max(item['input_null_residual'] for item in properties),
              'max_rest_frame_shell_residual': max(item['rest_frame_shell_residual'] for item in properties),
              'minimum_radiator_chord': min(item['radiator_chord'] for item in properties),
              'minimum_energy_fraction': min(item['minimum_energy_fraction'] for item in properties),
              'selection': 'All generated events retained; no filtering by candidate performance.'}
    (destination / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


def score(challenge, artifacts, output):
    from evaluate import build, run
    cases = json.loads((challenge / 'cases.json').read_text())
    references = json.loads((challenge / 'references.json').read_text())
    target = json.loads((ROOT / 'evaluator/hidden/target.json').read_text())
    results = {}
    for artifact in artifacts:
        with tempfile.TemporaryDirectory(prefix='eerad3-conditioned-') as directory:
            executable = build(artifact, Path(directory))
            records, duration = run(executable, cases, 1)
        failures, families = [], {}
        for case, reference, record in zip(cases, references, records):
            errors = check(case, reference, record, target)
            families.setdefault(case['family'], []).append(not errors)
            if errors:
                mapped = np.asarray(record[25:37]).reshape((4, 3), order='F').T
                energy = sum(vector[3] for vector in case['p'])
                failures.append({'id': case['id'], 'checks': errors,
                                 'map_error_over_q': float(np.max(np.abs(mapped - reference['mapped'])) / energy)})
        result = {'quality_passed': not failures, 'failed_case_count': len(failures),
                  'family_scores': {name: float(np.mean(values)) for name, values in families.items()},
                  'failures': failures, 'single_probe_cpu_seconds_not_resource_score': duration}
        results[str(artifact)] = result
        print(str(artifact), json.dumps({key: value for key, value in result.items() if key != 'failures'}), flush=True)
    output.write_text(json.dumps(results, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', type=Path, default=ROOT / 'adversary/conditioned_challenge')
    parser.add_argument('--seed', type=int, default=804371927)
    parser.add_argument('--samples', type=int, default=180)
    parser.add_argument('--artifacts', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, default=ROOT / 'adversary/conditioned_scores.json')
    arguments = parser.parse_args()
    if arguments.artifacts:
        score(arguments.destination, arguments.artifacts, arguments.output)
    else:
        write_challenge(arguments.destination, arguments.seed, arguments.samples)


if __name__ == '__main__':
    main()
