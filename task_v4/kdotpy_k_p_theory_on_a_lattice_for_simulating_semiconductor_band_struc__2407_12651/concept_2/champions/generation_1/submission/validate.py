import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import argparse
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent / 'participant/workspace'))
from model import LOWER, UPPER, diagnose

SHIFTS = [(.137, .271), (.319, .173), (.223, .417)]


def evaluate(job):
    label, parameters, size, shift, robust = job
    result = diagnose(parameters, size, shift)
    sign = round(result['chern'])
    signed_mean = sign * result['plateau_mean']
    failures = []
    conditions = {
        'chern': abs(sign) == 1,
        'full': abs(result['full'] - sign) <= (.003 if robust else .001),
        'gap': result['gap_lower_bound'] >= (.08 if robust else .10),
        'norm': result['norm_upper_bound'] <= 6.0,
        'flux': result['max_flux'] <= .45,
        'overlap': result['min_overlap'] >= .94,
        'spread': result['plateau_spread'] <= (.009 if robust else .006),
        'mean': (.175 <= signed_mean <= .425) if robust else (.18 <= signed_mean <= .42),
        'optical': result['retained_optical_min'] >= (.0145 if robust else .015),
        'omission': result['omitted_response'] >= .55,
    }
    failures = [name for name, passed in conditions.items() if not passed]
    return {'label': label, 'robust': robust, 'shift': shift,
            'diagnostic': result, 'failures': failures}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('witness')
    parser.add_argument('--output', default='validation.json')
    parser.add_argument('--all-shifts', action='store_true')
    options = parser.parse_args()
    started = time.monotonic()
    parameters = np.array(json.loads(Path(options.witness).read_text())['parameters'])
    assert parameters.shape == (25,)
    assert np.all(np.isfinite(parameters))
    assert np.all(parameters >= LOWER) and np.all(parameters <= UPPER)
    jobs = []
    for size in (49, 73, 97):
        for shift_index, shift in enumerate(SHIFTS):
            jobs.append((f'nominal_{size}_{shift_index}', parameters, size, shift, False))
    for parameter_index in range(21):
        for direction in (-1, 1):
            perturbed = parameters.copy()
            perturbed[parameter_index] += .002 * direction
            for shift_index, shift in enumerate(SHIFTS if options.all_shifts else SHIFTS[:1]):
                jobs.append((f'perturb_{parameter_index}_{direction}_{shift_index}',
                             perturbed, 73, shift, True))
    with mp.Pool(4) as pool:
        results = pool.map(evaluate, jobs)
    nominal = [record['diagnostic'] for record in results if not record['robust']]
    fine = [record for record in nominal if record['size'] in (73, 97)]
    responses = np.array([record['windows'] + [record['full']] for record in fine])
    fine_spread = float(np.ptp(responses, axis=0).max())
    all_diagnostics = [record['diagnostic'] for record in results]
    summary = {
        'passes': not any(record['failures'] for record in results) and fine_spread <= .0008,
        'evaluations': len(results),
        'fine_response_spread': fine_spread,
        'maximum_plateau_spread': max(record['plateau_spread'] for record in all_diagnostics),
        'minimum_retained_optical': min(record['retained_optical_min'] for record in all_diagnostics),
        'minimum_gap_bound': min(record['gap_lower_bound'] for record in all_diagnostics),
        'maximum_norm_bound': max(record['norm_upper_bound'] for record in all_diagnostics),
        'maximum_chern_error': max(abs(record['full'] - round(record['chern'])) for record in all_diagnostics),
        'failures': [{'label': record['label'], 'failures': record['failures']}
                     for record in results if record['failures']],
        'elapsed': time.monotonic() - started,
    }
    Path(options.output).write_text(json.dumps({'summary': summary, 'results': results}, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
