import copy
import json
import os
from pathlib import Path

from experiments import ROOT, extend, load, run


for name in ['impurity', 'ladder', 'paired', 'spin_orbit', 'vibronic']:
    case = load(name)
    for profile in ['baseline', 'production', 'refined']:
        run(case, case['id'] + '_' + profile, profile)
    run(case, case['id'] + '_final_tensor', settings=dict(exact_limit=0))
    if name in ['ladder', 'paired', 'vibronic']:
        run(case, case['id'] + '_smallstep16', 'baseline', dict(step=0.03))
        run(case, case['id'] + '_more_sweeps16', 'baseline', dict(sweeps=24, energy_tol=1e-13))
        run(case, case['id'] + '_bond48', 'baseline', dict(bond=48, optimize_layout=True))

case = load('vibronic')
case['id'] = 'renamed_mixed_contact'
case['family'] = 'annotation_is_not_physics'
case['sector'] = dict(kind='parity', value=1)
case['region'] = [1, 3]
case['layout'] = [5, 3, 1, 6, 0, 4, 7, 2]
case['pairing'] = [dict(sites=[3, 0], spins=[1, 1], before=[0.1, 0.12], after=[0.05, -0.14]),
                   dict(sites=[2, 2], spins=[0, 1], before=[0.2, 0.02], after=[0.1, 0.16])]
case['edges'][1]['before'][0][1] = [0.07, 0.12]
case['edges'][1]['after'][0][1] = [0.12, -0.09]
case['zeeman'] = [0.17, -0.06, 0.07, -0.04]
case['density_edges'] = [dict(sites=[0, 3], strength=0.13)]
case['times'] = [0, 0.07, 0.19, 0.36, 0.61]
run(case, case['id'] + '_production')
run(case, case['id'] + '_tensor160', settings=dict(exact_limit=0, bond=160, step=0.04,
                                                one_site_after=None, optimize_layout=False))

for name, sites in [('impurity', 10), ('impurity', 12), ('impurity', 14), ('spin_orbit', 10), ('paired', 10)]:
    case = extend(name, sites)
    directory = ROOT / 'runs' / (case['id'] + '_production')
    if directory.exists():
        directory.rename(ROOT / 'runs' / (case['id'] + '_pilot160'))
    run(case, case['id'] + '_production')

for name, sites in [('spin_orbit', 14), ('paired', 14), ('vibronic', 6), ('vibronic', 10)]:
    case = extend(name, sites)
    run(case, case['id'] + '_final_policy')
