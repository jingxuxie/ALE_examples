import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(os.environ['ALE_ASSETS'])


def run(case, label, profile='production', settings=None, timeout=175):
    output = ROOT / 'runs' / label
    output.mkdir(parents=True, exist_ok=True)
    for name in ('stats.json', 'trajectory.csv', 'failure.json'):
        if (output / name).exists():
            (output / name).unlink()
    (output / 'case.json').write_text(json.dumps(case, indent=2))
    environment = dict(os.environ)
    environment['ALE_SETTINGS'] = json.dumps(settings or {})
    started = time.perf_counter()
    print('START', label, flush=True)
    try:
        with (output / 'run.log').open('w') as handle:
            subprocess.run(['bash', str(ROOT / 'run.sh'), str(output / 'case.json'), str(output), profile],
                           env=environment, stdout=handle, stderr=subprocess.STDOUT, timeout=timeout, check=True)
        stats = json.loads((output / 'stats.json').read_text())
        print('DONE', label, stats['seconds'], stats['initial_energy'], flush=True)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as error:
        (output / 'failure.json').write_text(json.dumps(dict(error=str(error), seconds=time.perf_counter() - started)))
        print('FAILED', label, str(error), flush=True)


def load(name):
    return json.loads((ASSETS / 'input' / 'cases' / (name + '_dev.json')).read_text())


def extend(name, sites, levels=4):
    original = load(name)
    case = copy.deepcopy(original)
    case['id'] = name + '_scale_' + str(sites) + ('_levels' + str(levels) if name == 'vibronic' else '')
    case['n_sites'] = sites
    case['times'] = [0, 0.25, 0.5, 1.0, 1.5, 2.0]
    if name == 'spin_orbit':
        case['sector']['value'] = sites - sites % 2 - 2
    elif name != 'paired':
        case['sector']['value'] = sites
    case['region'] = list(range(sites // 2))
    for stage in ('before', 'after'):
        if name == 'impurity':
            case['onsite'][stage] = [(-0.7 if site == sites // 2 - 1 else 0.0) for site in range(sites)]
            if stage == 'after':
                case['onsite'][stage] = [value + (-0.35 if site < sites // 2 else 0.35)
                                          for site, value in enumerate(case['onsite'][stage])]
        else:
            case['onsite'][stage] = [original['onsite']['before'][site % len(original['onsite']['before'])]
                                     + ((0.35 if site < sites // 2 else -0.35) if stage == 'after' else 0)
                                     for site in range(sites)]
    case['interaction'] = [original['interaction'][0]] * sites
    if name == 'impurity':
        case['interaction'][sites // 2 - 1] = 1.6
    case['zeeman'] = [original.get('zeeman', [0])[site % len(original.get('zeeman', [0]))]
                      for site in range(sites)]
    case['edges'] = []
    for site in range(sites if name == 'spin_orbit' else sites - 1):
        edge = copy.deepcopy(original['edges'][0])
        edge['sites'] = [site, (site + 1) % sites]
        case['edges'].append(edge)
    case['pairing'] = []
    if name == 'paired':
        for site in range(sites):
            pair = copy.deepcopy(original['pairing'][site % len(original['pairing'])])
            pair['sites'] = [site, site]
            case['pairing'].append(pair)
    case['phonons'] = []
    if name == 'vibronic':
        for site in range(min(6, sites)):
            mode = copy.deepcopy(original['phonons'][site % len(original['phonons'])])
            mode.update(site=site, levels=levels)
            case['phonons'].append(mode)
    case['density_edges'] = []
    case['layout'] = list(range(sites + len(case['phonons'])))
    return case


def calibration():
    matrix = [[[-1, 0], [0, 0]], [[0, 0], [-1, 0]]]
    dimer = dict(id='dimer_calibration', n_sites=2, sector=dict(kind='number_sz', value=2, twosz=0),
                 onsite=dict(before=[0, 0], after=[0, 0]), interaction=[2, 2], zeeman=[0, 0],
                 edges=[dict(sites=[0, 1], before=matrix, after=matrix)], pairing=[], density_edges=[],
                 phonons=[], region=[0], times=[0, 0.1, 0.2], layout=[1, 0])
    for profile in ('production', 'baseline'):
        run(dimer, dimer['id'] + '_' + profile, profile)
    for name in ('impurity', 'ladder', 'paired', 'spin_orbit', 'vibronic'):
        case = load(name)
        run(case, case['id'] + '_tensor160', settings=dict(exact_limit=0, bond=160, step=0.04,
                                                         spin_orbitals=False, one_site_after=None))
        if name in ('ladder', 'paired', 'vibronic'):
            run(case, case['id'] + '_smallstep16', 'baseline', dict(step=0.03))
            run(case, case['id'] + '_more_sweeps16', 'baseline', dict(sweeps=24, energy_tol=1e-13))
            run(case, case['id'] + '_bond48', 'baseline', dict(bond=48, optimize_layout=True))
    case = load('paired')
    case['id'] = 'mixed_nonlocal_odd'
    case['sector']['value'] = 1
    case['layout'] = [4, 1, 5, 0, 3, 2]
    case['zeeman'] = [0.09, -0.07, 0.16, -0.12, 0.05, 0.03]
    case['pairing'].extend([
        dict(sites=[5, 0], spins=[0, 0], before=[0.12, 0.07], after=[0.23, -0.09]),
        dict(sites=[1, 4], spins=[1, 1], before=[-0.14, 0.03], after=[-0.05, 0.14]),
        dict(sites=[2, 0], spins=[1, 0], before=[0.09, -0.06], after=[0.11, 0.13])])
    case['edges'][0]['before'][0][1] = [0.14, 0.1]
    case['edges'][0]['after'][0][1] = [0.21, 0.12]
    case['region'] = [0, 2, 5]
    run(case, case['id'] + '_production')
    run(case, case['id'] + '_tensor160', settings=dict(exact_limit=0, optimize_layout=False))


def scaling():
    for name, sites in [('impurity', 10), ('impurity', 12), ('impurity', 14),
                        ('spin_orbit', 10), ('spin_orbit', 14), ('paired', 10), ('paired', 14),
                        ('vibronic', 6), ('vibronic', 10)]:
        case = extend(name, sites)
        run(case, case['id'] + '_production')
        if sites in (6, 10):
            run(case, case['id'] + '_baseline', 'baseline')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('study', choices=['calibration', 'scaling'])
    args = parser.parse_args()
    globals()[args.study]()
