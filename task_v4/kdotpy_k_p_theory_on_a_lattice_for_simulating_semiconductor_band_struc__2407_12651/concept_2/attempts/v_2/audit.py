import argparse
import json
from pathlib import Path
from multiprocessing import Pool

import numpy as np
from model import LOWER, UPPER, diagnose


def evaluate(item):
    parameters, size, shift = item
    return diagnose(parameters, size, shift)


def perturbations(count=256, seed=20260828):
    axis = np.zeros((42, 25))
    for index in range(21):
        axis[2 * index, index] = .02
        axis[2 * index + 1, index] = -.02
    rng = np.random.default_rng(seed)
    simultaneous = np.zeros((count, 25))
    simultaneous[:, :21] = rng.uniform(-.02, .02, (count, 21))
    return np.r_[axis, simultaneous]


def margins(result, robust=False):
    chern = round(result['chern'])
    signed = chern * result['plateau_mean']
    return {
        'spread': (.009 if robust else .006) - result['plateau_spread'],
        'mean_low': signed - (.175 if robust else .18),
        'mean_high': (.425 if robust else .42) - signed,
        'omitted': result['omitted_response'] - .55,
        'optical': result['retained_optical_min'] - (.0145 if robust else .015),
        'gap': result['gap_lower_bound'] - (.08 if robust else .1),
        'chern': (.003 if robust else .001) - abs(result['full'] - chern),
        'integer': 0. if abs(chern) == 1 else -1.,
        'flux': .45 - result['max_flux'],
        'overlap': result['min_overlap'] - .94,
        'norm': 6. - result['norm_upper_bound'],
    }


def audit(path, count=256, seed=20260828, size=73):
    parameters = np.array(json.loads(Path(path).read_text())['parameters'])
    print('bounds', bool(np.all(parameters >= LOWER) and np.all(parameters <= UPPER)), flush=True)
    nominal = [diagnose(parameters, mesh, shift) for mesh, shift in
               zip([49, 73, 97], [(0.137, 0.271), (0.319, 0.173), (0.223, 0.417)])]
    for result in nominal:
        print('nominal', result, 'margins', margins(result), flush=True)
    variations = perturbations(count, seed)
    with Pool(4) as pool:
        results = pool.map(evaluate, [(parameters + delta, size, (.137, .271))
                                     for delta in variations])
    keys = list(margins(results[0], True))
    margins_array = np.array([[margins(result, True)[key] for key in keys] for result in results])
    print('robust minimum margins', dict(zip(keys, margins_array.min(axis=0))), flush=True)
    print('worst indices', dict(zip(keys, margins_array.argmin(axis=0))), flush=True)
    print('failed probes', np.sum(np.any(margins_array < -1e-10, axis=1)), 'of', len(results), flush=True)
    response_delta = np.max(np.abs(np.array(nominal[-1]['windows']) - nominal[-2]['windows']))
    print('fine window delta', response_delta, flush=True)
    summary = {'nominal': nominal, 'perturbations': variations.tolist(),
               'robust': results, 'minimum_margins': dict(zip(keys, margins_array.min(axis=0)))}
    Path(Path(path).stem + f'_audit_{seed}.json').write_text(json.dumps(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    parser.add_argument('--count', type=int, default=256)
    parser.add_argument('--seed', type=int, default=20260828)
    parser.add_argument('--size', type=int, default=73)
    options = parser.parse_args()
    audit(options.path, options.count, options.seed, options.size)
