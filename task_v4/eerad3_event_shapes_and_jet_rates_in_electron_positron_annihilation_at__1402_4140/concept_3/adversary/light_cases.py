import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator/hidden'))
from oracle import geometric, dak_crosscheck


def main():
    generator = np.random.default_rng(2390751)
    cases, references = [], []
    maximum = 0.0
    for family in ['light_balanced', 'light_hierarchical', 'light_soft_radiator']:
        for sample in range(60):
            directions = generator.normal(size=(5, 3))
            directions /= np.linalg.norm(directions, axis=1, keepdims=True)
            axis = directions[0]
            def near(angle, selector):
                tangent = directions[selector] - np.dot(directions[selector], axis) * axis
                tangent /= np.linalg.norm(tangent)
                return np.cos(angle) * axis + np.sin(angle) * tangent
            opening = 10.0 ** generator.uniform(-6, -3.5)
            radiator_opening = opening if family == 'light_balanced' else 10.0 ** generator.uniform(-10, -8)
            energy = 0.9 if family != 'light_soft_radiator' else 10.0 ** generator.uniform(-14.3, -6)
            spatial = np.array([energy * axis, 0.3 * near(opening, 1),
                                0.4 * near(opening * 1.3, 2), 0.8 * near(radiator_opening, 3)])
            spatial = np.vstack([spatial, -spatial.sum(axis=0)])
            energies = np.linalg.norm(spatial, axis=1)
            momenta = np.column_stack([spatial, energies]) / energies.sum()
            momenta *= 10.0 ** generator.uniform(-80, 80)
            permutation = generator.permutation(5)
            case = {'id': f'{family}-{sample:03d}', 'family': family,
                    'p': momenta[permutation].tolist(),
                    'labels': [int(np.where(permutation == index)[0][0]+1) for index in range(5)],
                    'slots': list(map(int, generator.permutation(3)+1)), 'axis': [*directions[4], 1.0]}
            reference = geometric(case, 140)
            higher = geometric(case, 190)
            algebra = dak_crosscheck(case, 160)
            total = float(momenta[:, 3].sum())
            error = max(float(np.max(np.abs(np.asarray(higher['mapped']) - reference['mapped'])) / total),
                        float(np.max(np.abs(algebra-np.asarray(reference['mapped'])[case['slots'][0]-1])) / total))
            assert error < 2e-13
            maximum = max(maximum, error)
            cases.append(case)
            references.append(reference)
    destination = ROOT / 'adversary/light_challenge'
    destination.mkdir(parents=True, exist_ok=True)
    (destination/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    (destination/'references.json').write_text(json.dumps(references,indent=2)+'\n')
    (destination/'validation.json').write_text(json.dumps({'cases':len(cases),'max_crosscheck_error':maximum,
        'precision_digits':[140,160,190], 'scientific_region':'small antenna invariant mass, including correlated internal angle and soft hierarchies; the published domain does not impose an event-shape cut'},indent=2)+'\n')
    print('validated light-antenna cases:', len(cases))


if __name__ == '__main__':
    main()
