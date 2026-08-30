import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import sys
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import linprog

OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[1] / 'participant'
sys.path.insert(0, str(ROOT / 'workspace'))
from search_api import family, PROTOCOL
from simulator import quick

KEYS = list(PROTOCOL['parameter_bounds'])
SCALES = np.array([.002, .04, .004, .01, .01, .003, .002, .002, .002, .002, .002, .002, .002, .008, .008, .008, .008])
STARTED = time.process_time()

def margins(report):
    return np.array([1-report['certificate']/1e-4, 1-report['tail_mass']/.02, (report['observable_gap']-.001)/.3-1])

def evaluate(parameters, selected=None):
    reports = {}
    for name, member in family(parameters):
        if selected is None or name in selected:
            reports[name] = quick(member)
    return reports

def summary(reports):
    worst = sorted((float(min(margins(report))), name) for name, report in reports.items())
    print('worst', worst[:8], 'cpu', round(time.process_time()-STARTED, 2), flush=True)
    return worst[0][0]

def vector(reports, selected):
    return np.concatenate([margins(reports[name]) for name in selected])

def main():
    parameters = json.loads((ROOT / 'baseline/champion.json').read_text())['parameters']
    while True:
        try:
            reports = json.loads((OUTPUT / 'baseline_screen.json').read_text())
            if len(reports) == len(PROTOCOL['family']):
                break
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(2)
    current_margin = summary(reports)
    trust = 1.0
    for iteration in range(8):
        if current_margin >= .03:
            break
        active = set()
        for constraint in range(3):
            active.update(sorted(reports, key=lambda name: margins(reports[name])[constraint])[:3])
        selected = sorted(active)
        print('iteration', iteration, 'active', selected, 'trust', trust, flush=True)
        base = vector(reports, selected)
        gradient = np.empty((len(base), len(KEYS)))
        for index, key in enumerate(KEYS):
            shifted = dict(parameters)
            shifted[key] += .1*SCALES[index]
            gradient[:, index] = (vector(evaluate(shifted, selected), selected)-base)/.1
            print('gradient', key, flush=True)
        variable_count = len(KEYS)
        objective = np.r_[np.zeros(variable_count), -1, np.full(variable_count, .0003)]
        constraint_matrix = np.vstack([
            np.c_[-gradient, np.ones(len(base)), np.zeros((len(base), variable_count))],
            np.c_[np.eye(variable_count), np.zeros(variable_count), -np.eye(variable_count)],
            np.c_[-np.eye(variable_count), np.zeros(variable_count), -np.eye(variable_count)],
        ])
        constraint_bounds = np.r_[base, np.zeros(2*variable_count)]
        step_bounds = []
        for index, key in enumerate(KEYS):
            lower, upper = PROTOCOL['parameter_bounds'][key]
            step_bounds.append((max(-trust, (lower-parameters[key])/SCALES[index]), min(trust, (upper-parameters[key])/SCALES[index])))
        result = linprog(objective, A_ub=constraint_matrix, b_ub=constraint_bounds, bounds=step_bounds+[(None, .1)]+[(0, None)]*variable_count, method='highs')
        if not result.success:
            raise RuntimeError(result.message)
        print('predicted', result.x[variable_count], 'step', result.x[:variable_count].tolist(), flush=True)
        improved = False
        for factor in (1.0, .5, .25):
            candidate = {key: parameters[key]+factor*SCALES[index]*result.x[index] for index, key in enumerate(KEYS)}
            candidate_reports = evaluate(candidate)
            candidate_margin = summary(candidate_reports)
            (OUTPUT / f'candidate_{iteration}_{factor}.json').write_text(json.dumps({'schema_version': 1, 'parameters': candidate}, indent=2)+'\n')
            (OUTPUT / f'screen_{iteration}_{factor}.json').write_text(json.dumps(candidate_reports, indent=2)+'\n')
            if candidate_margin > current_margin:
                parameters, reports, current_margin = candidate, candidate_reports, candidate_margin
                improved = True
                break
        if not improved:
            trust *= .4
        (OUTPUT / 'submission.json').write_text(json.dumps({'schema_version': 1, 'parameters': parameters}, indent=2)+'\n')
        (OUTPUT / 'best_screen.json').write_text(json.dumps(reports, indent=2)+'\n')
    print('FINAL', current_margin, json.dumps(parameters), 'cpu_seconds', time.process_time()-STARTED, flush=True)

if __name__ == '__main__':
    main()
