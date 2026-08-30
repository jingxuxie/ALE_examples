from optimize import *
import argparse

def run_grid(arguments):
    cases, shape, dt, splines = arguments
    initial, target, residual = fc.references(cases, shape, Path('cache'))
    state, diagnostics = fc.evolve(splines, cases, shape, dt, initial)
    scores = fc.fidelities(state, target, shape)
    return state, diagnostics, scores, residual

def holdouts():
    from scipy.stats import qmc
    cases = PUBLIC.copy()
    groups = [('interaction', ['g', 'self_ratio', 'cross_ratio']), ('calibration', ['rf_gain', 'bias', 'gradient']), ('trap', ['trap_x', 'trap_y', 'gradient']), ('joint', list(PROTOCOL['uncertainty']))]
    for family, keys in groups:
        fractions = qmc.Sobol(len(keys), scramble=True, seed=784).random_base2(3)
        if family != 'joint':
            fractions = np.array([[(index >> offset) & 1 for offset in range(len(keys))] for index in range(8)])
        else:
            fractions = np.concatenate((np.round(fractions), fractions))
        for index, row in enumerate(fractions):
            case = dict(PROTOCOL['nominal'], id='hold_' + family + str(index), family=family)
            for key, fraction in zip(keys, row):
                lower, upper = PROTOCOL['uncertainty'][key]
                case[key] = lower + fraction * (upper - lower)
            cases.append(case)
    return cases

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('artifact')
    parser.add_argument('--cases', default='public')
    parser.add_argument('--output', default='evaluation.json')
    parser.add_argument('--nx', type=int, default=64)
    parser.add_argument('--dt', type=float, default=0.04)
    parser.add_argument('--audit', action='store_true')
    parser.add_argument('--workers', type=int, default=1)
    args = parser.parse_args()
    cases = holdouts() if args.cases == 'holdout' else cases_for(args.cases)
    splines, control_info = fc.validate_artifact(fc.read_json(args.artifact), PROTOCOL)
    configurations = [(80, 40, 0.01), (112, 56, 0.01), (112, 56, 0.005)] if args.audit else [(args.nx, args.nx // 2, args.dt)]
    results = []
    states = []
    started = time.monotonic()
    if args.workers > 1:
        import multiprocessing
        pool = multiprocessing.get_context('fork').Pool(args.workers)
        partitions = [[cases[index] for index in indices] for indices in np.array_split(np.arange(len(cases)), args.workers)]
    for nx, ny, dt in configurations:
        shape = (nx, ny)
        if args.workers == 1:
            state, diagnostics, scores, residual = run_grid((cases, shape, dt, splines))
        else:
            parts = pool.map(run_grid, [(part, shape, dt, splines) for part in partitions])
            state = np.concatenate([part[0] for part in parts])
            diagnostics = {key: np.concatenate([part[1][key] for part in parts]) for key in parts[0][1]}
            scores = np.concatenate([part[2] for part in parts])
            residual = max(part[3] for part in parts)
        states.append(state)
        results.append({'shape': shape, 'dt': dt, 'fidelities': scores.tolist(), 'diagnostics': {key: value.tolist() for key, value in diagnostics.items()}, 'residual': residual})
        print('GRID', shape, dt, 'scores', fc.summarize(scores, cases, PROTOCOL), 'diagnostics', {key: float(max(value)) for key, value in diagnostics.items()}, 'seconds', time.monotonic() - started, flush=True)
    valid = True
    distance = []
    allowance = np.zeros(len(cases))
    if args.audit:
        allowance = 2 * (np.abs(np.array(results[0]['fidelities']) - np.array(results[1]['fidelities'])) + np.abs(np.array(results[1]['fidelities']) - np.array(results[2]['fidelities']))) + 2e-6
        scores = np.maximum(0, scores - allowance)
        distance = [fc.state_distance(fc.prolong(states[0], (112, 56)), states[1], (112, 56)).tolist(), fc.state_distance(states[1], states[2], (112, 56)).tolist()]
        valid = max(allowance) <= 2e-4 and np.max(distance) <= 0.002
        for result in results:
            for key, limit in [('norm_error', 1e-10), ('boundary_mass', 1e-8), ('spectral_tail', 1e-8)]:
                valid = valid and max(result['diagnostics'][key]) <= limit
    summary = fc.summarize(scores, cases, PROTOCOL)
    report = dict(summary, valid=bool(valid), audited=args.audit, artifact=args.artifact, resource_score=fc.resource_score(splines, PROTOCOL), control_diagnostics=control_info, cases=[dict(case, fidelity=float(score)) for case, score in zip(cases, scores)], grids=results, allowance=allowance.tolist(), distance=distance, runtime_seconds=time.monotonic() - started)
    report['passed'] = bool(args.audit and valid and summary['passed'])
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
    print('RESULT', summary, 'valid', valid, 'allowance', max(allowance), 'distance', np.max(distance) if distance else 0, flush=True)
    if args.workers > 1:
        pool.close()
        pool.join()

if __name__ == '__main__':
    main()
