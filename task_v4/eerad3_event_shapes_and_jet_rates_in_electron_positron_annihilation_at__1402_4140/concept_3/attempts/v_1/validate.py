import argparse
import json
import math
import os
import subprocess
from pathlib import Path

import mpmath as mp
import numpy as np

ROOT = Path(__file__).resolve().parent
ASSETS = Path(os.environ['TASK']) / 'input'
mp.mp.dps = 90


def oracle(case):
    points = [[mp.mpf(value) for value in row] for row in case['p']]
    energy = sum(row[3] for row in points)
    for row in points:
        row[3] = mp.sqrt(sum(value * value for value in row[:3]))
    def product(first, second):
        return first[3] * second[3] - sum(first[index] * second[index] for index in range(3))
    inv = [[2 * product(first, second) / energy**2 for second in points] for first in points]
    aidx, uidx, vidx, bidx, spectator = [index - 1 for index in case['labels']]
    ya1, ya2, y1b, y2b, y12, yab = [inv[first][second] for first, second in
        [(aidx, uidx), (aidx, vidx), (uidx, bidx), (vidx, bidx), (uidx, vidx), (aidx, bidx)]]
    total = ya1 + ya2 + y1b + y2b + y12 + yab
    weight1 = (y1b + y12) / (ya1 + y1b + y12)
    weight2 = y2b / (ya2 + y2b + y12)
    rho2 = 1 + (weight1-weight2)**2 / yab**2 / total**2 * (
        yab**2*y12**2+ya1**2*y2b**2+ya2**2*y1b**2
        -2*(yab*ya1*y2b*y12+yab*ya2*y1b*y12+ya1*ya2*y1b*y2b)) + (
        (weight1*(1-weight2)+weight2*(1-weight1))*2*(yab*ya1*y2b+yab*ya2*y1b-yab**2*y12)
        +4*weight1*(1-weight1)*yab*ya1*y1b+4*weight2*(1-weight2)*yab*ya2*y2b)/yab**2/total
    rho = mp.sqrt(rho2)
    firstweight = ((1+rho)*total-(2*y1b+y12)*weight1-(2*y2b+y12)*weight2
        +(ya1*y2b-ya2*y1b)*(weight1-weight2)/yab)/(2*(yab+ya1+ya2))
    lastweight = ((1-rho)*total-(2*ya1+y12)*weight1-(2*ya2+y12)*weight2
        -(ya1*y2b-ya2*y1b)*(weight1-weight2)/yab)/(2*(yab+y1b+y2b))
    weights = [firstweight, weight1, weight2, lastweight]
    mapped = [[mp.mpf(0)]*4 for unused in range(3)]
    firstslot, secondslot, thirdslot = [index-1 for index in case['slots']]
    for component in range(4):
        mapped[firstslot][component] = sum(weight*points[index][component] for weight, index in zip(weights, [aidx, uidx, vidx, bidx]))
        mapped[secondslot][component] = sum((1-weight)*points[index][component] for weight, index in zip(weights, [aidx, uidx, vidx, bidx]))
        mapped[thirdslot][component] = mp.mpf(case['p'][spectator][component])
    mapped_inv = [2*product(mapped[first], mapped[second])/energy**2 for first, second in [(0,1),(0,2),(1,2)]]
    return np.array(inv, float), np.array(mapped, float), np.array(mapped_inv, float)


def generate(count, seed=418319):
    rng = np.random.default_rng(seed)
    def unit():
        direction = rng.normal(size=3)
        return direction / np.linalg.norm(direction)
    cases = []
    for event in range(count):
        family = ['generic', 'soft', 'double', 'triple', 'parallel', 'allparallel', 'hierarchy', 'boundary'][event % 8]
        directions = np.array([unit() for unused in range(4)])
        energies = rng.uniform(.1, 1, size=4)
        opening = 10**rng.uniform(-12, -1)
        if family == 'soft':
            energies[1:3] *= 10**rng.uniform(-16, -2, size=2)
        if family == 'double':
            directions[1] = directions[0] + opening * unit()
            directions[2] = directions[3] + opening * unit()
        if family == 'triple':
            directions[1] = directions[0] + opening * unit()
            directions[2] = directions[0] + opening * unit()
        if family == 'parallel':
            directions[3] = directions[0] + opening * unit()
        if family == 'allparallel':
            directions = np.array([directions[0] + opening*unit() for unused in range(4)])
        if family == 'hierarchy':
            energies *= 10**rng.uniform(-16, 0, size=4)
            directions[3] = directions[0] + opening * unit()
        if family == 'boundary':
            directions[3] = directions[0] + 10**rng.uniform(-4.2, -3.8)*unit()
        directions /= np.linalg.norm(directions, axis=1)[:,None]
        spatial = energies[:,None]*directions
        spatial = np.vstack([spatial, -spatial.sum(axis=0)])
        points = np.column_stack([spatial, np.linalg.norm(spatial, axis=1)])
        points /= points[:,3].sum()
        points *= 10**rng.uniform(-90, 90)
        reorder = rng.permutation(5)
        labels = np.argsort(reorder) + 1
        if event % 7 == 0:
            labels = rng.permutation(5) + 1
        axis = unit() * 10**rng.uniform(-70, 70)
        if event % 3 == 0:
            axis[rng.integers(3)] *= 1e-200
        if event % 11 == 0:
            axis = np.array([0., 0., (-1.)**event])
        cases.append(dict(id=f'{family}-{event}', family=family, p=points[reorder].tolist(), labels=labels.tolist(), slots=(rng.permutation(3)+1).tolist(), axis=[*axis, 0.]))
    return cases


def stream(cases, repeats):
    lines = [f'{len(cases)} {repeats}']
    for case in cases:
        lines += [' '.join(format(value, '.17e') for value in row) for row in case['p']]
        lines += [' '.join(map(str, case['labels'] + case['slots']))]
        lines += [' '.join(format(value, '.17e') for value in case['axis'])]
    return '\n'.join(lines) + '\n'


def edge_cases():
    cases = []
    for opening in [1e-4, 1e-8, 1e-12]:
        for soft in [1e-8, 1e-12, 1e-16]:
            for pattern in range(3):
                if pattern == 0:
                    spatial = np.array([[.3, 0, 0], [.2, 0, 0], [.1, 0, 0], [soft, soft*opening, 0]])
                elif pattern == 1:
                    spatial = np.array([[soft, soft, 0], [.2, 0, 0], [.1, .1*opening, 0], [soft, -soft, soft]])
                else:
                    spatial = np.array([[.3, 0, 0], [soft, soft*opening, 0], [.1, 0, 0], [.2, .2*opening, 0]])
                spatial = np.vstack([spatial, -spatial.sum(axis=0)])
                points = np.column_stack([spatial, np.linalg.norm(spatial, axis=1)])
                cases.append(dict(id=f'edge-{opening}-{soft}-{pattern}', family='edge',
                    p=points.tolist(), labels=[1,2,3,4,5], slots=[1,2,3], axis=[0.,1.,0.,0.]))
    return cases


def run(cases, repeats=1, binary='workspace/mapping_driver'):
    output = subprocess.run([str(ROOT / binary)], input=stream(cases, repeats), text=True, capture_output=True, check=True).stdout.splitlines()
    return [np.fromstring(line, sep=' ') for line in output[:-1]], float(output[-1].split()[1])


def check(cases):
    results, elapsed = run(cases)
    assert len(results) == len(cases)
    assert all(len(result) == 84 for result in results)
    worst = {}
    failures = []
    for case, result in zip(cases, results):
        expected_y, expected_map, expected_s = oracle(case)
        points = np.array(case['p'])
        energy = points[:,3].sum()
        inv = result[:25].reshape((5,5), order='F')
        mapped = result[25:37].reshape((3,4)) / energy
        mapped_s = result[37:40]
        saved = result[40:52].reshape((3,4)) / energy
        rotation = result[52:68].reshape((4,4), order='F')
        inverse = result[68:84].reshape((4,4), order='F')
        axis = np.array(case['axis'][:3], dtype=float)
        axis /= np.linalg.norm(axis)
        first, last = [case['labels'][index]-1 for index in [0,3]]
        chord = np.linalg.norm(points[first,:3]/np.linalg.norm(points[first,:3])-points[last,:3]/np.linalg.norm(points[last,:3]))
        slack = 16*np.finfo(float).eps/chord if chord < 1e-4 else 0
        shell = abs(mapped[:,3]**2 - np.sum(mapped[:,:3]**2,axis=1)).max()
        invariant_consistency = max(abs(mapped_s[index]-2*(mapped[first,3]*mapped[second,3]-mapped[first,:3]@mapped[second,:3])) for index,(first,second) in enumerate([(0,1),(0,2),(1,2)]))
        errors = dict(
            inv=np.max(abs(inv-expected_y)/(3e-8*abs(expected_y)+1e-29)),
            map=np.max(abs(mapped-expected_map/energy))/(3e-9+slack),
            shell=shell/3e-10,
            conservation=np.max(abs(mapped.sum(axis=0)-points.sum(axis=0)/energy))/3e-11,
            mapped_inv=np.max(abs(mapped_s-expected_s))/(3e-9+2*slack),
            consistency=invariant_consistency/3e-9,
            saved=np.max(abs(mapped-saved))/1e-14,
            spectator=np.max(abs(mapped[case['slots'][2]-1]-points[case['labels'][4]-1]/energy))/1e-14,
            rotation=max(np.max(abs(rotation@inverse-np.eye(4))),np.max(abs(rotation.T@rotation-np.eye(4))),abs(np.linalg.det(rotation)-1),np.max(abs(rotation[:3,:3]@axis-[0,0,1])))/3e-12,
        )
        if case.get('family') == 'generic':
            errors['ordinary_map'] = np.max(abs(mapped-expected_map/energy))/3e-12
            errors['ordinary_inv'] = np.max(abs(mapped_s-expected_s))/3e-12
        if not np.isfinite(result).all() or min(mapped[:,3]) <= 0:
            errors['finite_positive'] = float('inf')
        for name, error in errors.items():
            if error > worst.get(name, (0, ''))[0]:
                worst[name] = (error, case['id'])
            if error > 1:
                failures.append((case['id'], name, error))
    print('Worst error / tolerance:', json.dumps(worst, indent=2))
    print('Failures:', failures[:30], 'count=', len(failures))
    return failures


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=800)
    parser.add_argument('--timing', type=int, default=0)
    parser.add_argument('--seed', type=int, default=418319)
    args = parser.parse_args()
    public = json.loads((ASSETS/'examples.json').read_text())
    cases = public + generate(args.count, args.seed) + edge_cases()
    if args.timing:
        for selection in [public, cases]:
            baseline = [run(selection, args.timing, 'baseline/mapping_driver')[1] for unused in range(3)]
            candidate = [run(selection, args.timing)[1] for unused in range(3)]
            print('Timing', len(selection), 'baseline', baseline, 'candidate', candidate,
                  'ratio', np.median(candidate)/np.median(baseline))
    else:
        failures = check(cases)
        raise SystemExit(bool(failures))
