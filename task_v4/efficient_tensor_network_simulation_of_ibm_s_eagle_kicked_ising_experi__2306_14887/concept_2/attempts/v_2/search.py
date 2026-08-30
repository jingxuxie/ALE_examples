import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import concurrent.futures
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import minimize, least_squares

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/efficient_tensor_network_simulation_of_ibm_s_eagle_kicked_ising_experi__2306_14887/concept_2/participant')
sys.path.insert(0, str(ASSETS / 'workspace'))
from simulator import compare, compare_waveforms
from protocol import load_spec, metrics, waveforms

SPEC = load_spec()
ROOT = Path(__file__).resolve().parent


def witness(depth, knots):
    return dict(schema_version=1, depth=int(depth), knots=list(map(float, knots)), observable='zz1')


def assess(candidate, robust=False):
    families = waveforms(candidate, SPEC, include_corners=False)
    if not robust:
        families = {'nominal': families['nominal']}
    else:
        nominal = families['nominal']
        grid = np.linspace(-1, 1, len(nominal))
        families = {'nominal': nominal, 'minus': nominal - 0.004, 'plus': nominal + 0.004,
                    'tilt_minus': nominal - 0.004 * grid, 'tilt_plus': nominal + 0.004 * grid}
        active_path = ROOT / 'active_families.json'
        if active_path.exists():
            complete = waveforms(candidate, SPEC)
            families = {'nominal': nominal}
            for name in json.loads(active_path.read_text()):
                families[name] = complete[name]
    records = []
    for angles in families.values():
        result = compare(angles)
        records.append(metrics(result['exact']['zz1'], [result['mps'][str(chi)]['zz1'] for chi in (4, 8, 16)], SPEC))
    return dict(witness=candidate, margin=min(record['margin'] for record in records), records=records)


def safe_assess(candidate):
    try:
        return assess(candidate)
    except ValueError:
        return None


def robust_assess(entry):
    return assess(entry['witness'], True)


def finalists(options):
    candidates = json.loads((ROOT / options.input).read_text())
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(robust_assess, candidates))
    results.sort(key=lambda entry: entry['margin'], reverse=True)
    (ROOT / 'finalists.json').write_text(json.dumps(results[:4]))
    (ROOT / 'witness.json').write_text(json.dumps(results[0]['witness']) + '\n')
    for result in results:
        print(json.dumps(dict(witness=result['witness'], margin=result['margin'])), flush=True)


def screen(options):
    random = np.random.default_rng(options.seed)
    candidates = []
    if options.mode in ('grid', 'fine'):
        depths = range(12, 49, 2) if options.mode == 'grid' else range(20, 49)
        angles = np.arange(0.6, 1.451, 0.05) if options.mode == 'grid' else np.arange(1.1, 1.451, 0.01)
        for depth in depths:
            for angle in angles:
                candidates.append(witness(depth, [angle] * 6))
    else:
        for trial in range(options.trials):
            depth = int(random.integers(16, 49))
            center = random.uniform(0.65, 1.4)
            knots = np.clip(center + random.normal(0, random.uniform(0.01, 0.2), 6), 0.12, 1.45)
            candidates.append(witness(depth, knots))
    best = []
    start = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for index, result in enumerate(pool.map(safe_assess, candidates)):
            if result is not None:
                best.append(result)
                best.sort(key=lambda entry: entry['margin'], reverse=True)
                best = best[:30]
                if result is best[0]:
                    print(json.dumps(dict(index=index, elapsed=time.time()-start, best=result)), flush=True)
                    (ROOT / 'witness.json').write_text(json.dumps(result['witness']) + '\n')
                if index % 20 == 0:
                    (ROOT / (options.mode + '_candidates.json')).write_text(json.dumps(best))
            if index % 40 == 0:
                print('progress', index, len(candidates), time.time()-start, flush=True)
    (ROOT / (options.mode + '_candidates.json')).write_text(json.dumps(best))


def compute_validation(candidate, workers=4):
    start = time.time()
    results = compare_waveforms(waveforms(candidate, SPEC), workers=workers)
    records = {}
    for name, result in results.items():
        records[name] = metrics(result['exact']['zz1'], [result['mps'][str(chi)]['zz1'] for chi in (4, 8, 16)], SPEC)
    worst = min(records, key=lambda name: records[name]['margin'])
    summary = dict(witness=candidate, family_count=len(records), passed=all(record['passed'] for record in records.values()),
                   worst_family=worst, worst=records[worst], nominal=records['nominal'],
                   max_spread=max(record['spread'] for record in records.values()),
                   min_error=min(record['error'] for record in records.values()), elapsed_seconds=time.time()-start)
    summary['worst_cases'] = [{**records[name], 'family': name} for name in sorted(records, key=lambda name: records[name]['margin'])[:12]]
    critical = {min(records, key=lambda name: records[name]['error']), worst}
    for index in range(2):
        critical.add(min(records, key=lambda name: records[name]['estimates'][index+1] - records[name]['estimates'][index]))
        critical.add(max(records, key=lambda name: records[name]['estimates'][index+1] - records[name]['estimates'][index]))
    summary['critical_families'] = sorted(critical)
    return summary


def validate(options):
    candidate = json.loads((ROOT / options.input).read_text())
    summary = compute_validation(candidate)
    (ROOT / options.report).write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)


def batch_check(entry):
    return compute_validation(entry['witness'], workers=1)


def batch_validate(options):
    entries = json.loads((ROOT / options.input).read_text())
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        reports = list(pool.map(batch_check, entries[:4]))
    reports.sort(key=lambda report: report['worst']['margin'], reverse=True)
    (ROOT / options.report).write_text(json.dumps(reports[0], indent=2) + '\n')
    (ROOT / 'witness.json').write_text(json.dumps(reports[0]['witness']) + '\n')
    (ROOT / 'batch_results.json').write_text(json.dumps(reports))
    for report in reports:
        print(json.dumps({key: value for key, value in report.items() if key != 'worst_cases'}), flush=True)


def optimize_job(job):
    index, candidate, evaluations, robust, seed, method, step = job
    random = np.random.default_rng(seed + index)
    depth = candidate['depth']
    best = None
    calls = 0

    def objective(knots, residual=False):
        nonlocal best, calls
        calls += 1
        proposal = witness(depth, knots)
        try:
            result = assess(proposal, robust)
        except ValueError:
            return 1000 + float(np.sum(np.maximum(0.12-knots, 0) + np.maximum(knots-1.45, 0)))
        record = result['records']
        loss = max(max(entry['spread']/0.0078, 0.152/max(entry['error'], 1e-6)) for entry in record)
        result['loss'] = loss
        result['calls'] = calls
        if best is None or loss < best['loss']:
            best = result
            (ROOT / f'opt_{index}.json').write_text(json.dumps(best))
            if calls % 20 == 1 or result['margin'] > 1:
                print(json.dumps(dict(worker=index, calls=calls, best=result)), flush=True)
        if residual:
            values = []
            for entry in record:
                values.extend(np.diff(entry['estimates']) / 0.006)
                values.append(max(0, 0.175-entry['error']) / 0.02)
            return np.asarray(values)
        return loss

    initial = np.asarray(candidate['knots'])
    simplex = np.tile(initial, (7, 1))
    for knot in range(6):
        if index % 2:
            simplex[knot+1] += step * random.choice([-1, 1]) * np.cos(np.pi*knot*(np.arange(6)+0.5)/6)
        else:
            simplex[knot+1, knot] += step * random.choice([-1, 1])
    if method == 'least':
        least_squares(lambda knots: objective(knots, True), initial, bounds=(0.12, 1.45),
                      diff_step=1e-4, max_nfev=evaluations, ftol=1e-5, xtol=1e-5, gtol=1e-5)
    else:
        minimize(objective, initial, method='Nelder-Mead',
                 options=dict(maxfev=evaluations, xatol=2e-5, fatol=2e-5, initial_simplex=simplex))
    return best


def optimize(options):
    candidates = json.loads((ROOT / options.input).read_text())
    if isinstance(candidates, dict):
        candidates = [dict(witness=candidates)] * 4
    jobs = [(index, candidate['witness'], options.trials, options.robust, options.seed, options.method, options.step)
            for index, candidate in enumerate(candidates[:4])]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(optimize_job, jobs))
    results.sort(key=lambda entry: entry['margin'], reverse=True)
    (ROOT / 'optimized.json').write_text(json.dumps(results))
    (ROOT / 'witness.json').write_text(json.dumps(results[0]['witness']) + '\n')
    print(json.dumps(results), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['grid', 'fine', 'random', 'validate', 'optimize', 'finalists', 'batch_validate'])
    parser.add_argument('--trials', type=int, default=500)
    parser.add_argument('--seed', type=int, default=14887)
    parser.add_argument('--input', default='witness.json')
    parser.add_argument('--report', default='validation.json')
    parser.add_argument('--robust', action='store_true')
    parser.add_argument('--method', choices=['simplex', 'least'], default='simplex')
    parser.add_argument('--step', type=float, default=0.003)
    options = parser.parse_args()
    if options.mode == 'validate':
        validate(options)
    elif options.mode == 'optimize':
        optimize(options)
    elif options.mode == 'finalists':
        finalists(options)
    elif options.mode == 'batch_validate':
        batch_validate(options)
    else:
        screen(options)
