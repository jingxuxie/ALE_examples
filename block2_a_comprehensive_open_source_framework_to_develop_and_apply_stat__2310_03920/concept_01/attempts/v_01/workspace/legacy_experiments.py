import copy
import json
import os
from pathlib import Path
import subprocess

from experiments import ASSETS, ROOT, load, run


def legacy(case, label, clock=False, interaction=False, profile='production'):
    output = ROOT / 'runs' / label
    output.mkdir(parents=True, exist_ok=True)
    (output / 'case.json').write_text(json.dumps(case, indent=2))
    environment = dict(os.environ)
    environment.pop('LEGACY_REPAIR_CLOCK', None)
    environment.pop('LEGACY_REPAIR_U', None)
    if clock:
        environment['LEGACY_REPAIR_CLOCK'] = '1'
    if interaction:
        environment['LEGACY_REPAIR_U'] = '1'
    with (output / 'run.log').open('w') as handle:
        subprocess.run(['python3', str(ROOT / 'workspace/legacy/run.py'), str(output / 'case.json'), str(output), profile],
                       env=environment, stdout=handle, stderr=subprocess.STDOUT, check=True, timeout=120)
    profile_label = 'legacy_clock_U' if interaction else ('legacy_clock' if clock else 'legacy')
    (output / 'profile.txt').write_text(profile_label + '\n')
    stats = json.loads((output / 'stats.json').read_text())
    stats['settings'].update(repair_clock=clock, repair_U=interaction, method='legacy SZ QC-integral MPS')
    stats['profile'] = profile_label
    (output / 'stats.json').write_text(json.dumps(stats, indent=2))
    print('DONE', label, flush=True)


for name in ('impurity', 'ladder', 'paired', 'spin_orbit', 'vibronic'):
    case = load(name)
    legacy(case, case['id'] + '_legacy')
    if name == 'impurity':
        legacy(case, case['id'] + '_legacy_clock', clock=True)
        legacy(case, case['id'] + '_legacy_clock_U', clock=True, interaction=True, profile='refined')
    if name in ('paired', 'impurity', 'vibronic'):
        case['times'] = [index / 40 for index in range(49)]
        run(case, case['id'] + '_dense_grid', settings={})

dimer = json.loads((ROOT / 'runs/dimer_calibration_production/case.json').read_text())
legacy(dimer, 'dimer_calibration_legacy')
legacy(dimer, 'dimer_calibration_legacy_clock_U', clock=True, interaction=True)

for name, ablation in [('spin_orbit', 'real_hopping'), ('vibronic', 'zero_coupling'),
                       ('ladder', 'zero_density'), ('paired', 'zero_pairing')]:
    case = load(name)
    case['id'] = name + '_' + ablation
    if ablation == 'real_hopping':
        for edge in case['edges']:
            for stage in ('before', 'after'):
                for row in edge[stage]:
                    for coefficient in row:
                        coefficient[1] = 0
    elif ablation == 'zero_coupling':
        for mode in case['phonons']:
            mode['coupling'] = dict(before=0.0, after=0.0)
    elif ablation == 'zero_density':
        case['density_edges'] = []
    else:
        case['pairing'] = []
    run(case, case['id'] + '_production')
