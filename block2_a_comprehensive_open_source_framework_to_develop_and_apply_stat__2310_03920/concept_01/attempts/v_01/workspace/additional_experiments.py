import copy

from experiments import extend, load, run


for sites in [10, 14]:
    original = load('ladder')
    case = copy.deepcopy(original)
    case['id'] = 'ladder_scale_' + str(sites)
    case['n_sites'] = sites
    case['sector']['value'] = 2 * (sites // 3)
    case['interaction'] = [3.5] * sites
    case['zeeman'] = [0.0] * sites
    case['onsite']['before'] = [0.09 * (site % 2) for site in range(sites)]
    case['onsite']['after'] = [value + (0.5 if site < 2 else -0.3)
                              for site, value in enumerate(case['onsite']['before'])]
    case['edges'] = []
    for left in range(sites):
        neighbors = []
        if left % 2 == 0:
            neighbors.append((left + 1, -0.75))
        if left + 2 < sites:
            neighbors.append((left + 2, -1.0))
        if left % 2 == 0 and left + 3 < sites:
            neighbors.append((left + 3, -0.16))
        for right, amplitude in neighbors:
            hopping = [[[amplitude, 0], [0, 0]], [[0, 0], [amplitude, 0]]]
            case['edges'].append(dict(sites=[left, right], before=hopping, after=hopping))
    case['density_edges'] = [dict(sites=[site, site + 2], strength=0.25) for site in range(sites - 2)]
    case['layout'] = list(range(sites))
    case['times'] = [0, 0.2, 0.4, 0.8, 1.2]
    run(case, case['id'] + '_production')
    if sites == 10:
        run(case, case['id'] + '_final_tensor', settings=dict(exact_limit=0))

case = extend('vibronic', 6, levels=3)
case['times'] = [0, 0.2, 0.4, 0.8, 1.2]
run(case, case['id'] + '_production')
run(case, case['id'] + '_final_tensor', settings=dict(exact_limit=0))
