import sys

from experiments import extend, run


for name, sites in [('paired', 10), ('spin_orbit', 10)]:
    case = extend(name, sites)
    run(case, case['id'] + '_exact', settings=dict(exact_limit=1000000))
for name, sites in [('paired', 14), ('spin_orbit', 14), ('vibronic', 6), ('vibronic', 10)]:
    case = extend(name, sites)
    run(case, case['id'] + '_fast96', settings=dict(exact_limit=0, bond=96, step=0.1))
    if name == 'vibronic' and sites == 6:
        run(case, case['id'] + '_fast64', settings=dict(exact_limit=0, bond=64, step=0.1))
