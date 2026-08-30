from robust import *


def maximize_search(arguments):
    engine = Engine()
    rng = np.random.default_rng(arguments.seed)
    started = time.monotonic()
    paths = sorted(Path('.').glob(arguments.pattern)) if arguments.pattern else []
    best = -np.inf
    for trial in range(arguments.trials):
        if paths:
            initial = coefficients(model.load_witness(paths[trial % len(paths)]))[CONTROL]
        else:
            initial = np.r_[rng.normal(0, arguments.spread, 21), rng.uniform(-.5, .5, 21)]
        initial = np.clip(initial, -BOUNDS+.0012, BOUNDS-.0012)
        cached = {}

        def state(controls):
            if 'controls' not in cached or not np.array_equal(cached['controls'], controls):
                metrics, gradient, physical, hessian = engine.evaluate(controls, hessian=True)
                means = metrics[:35] * 1e6
                sigma = np.sqrt(np.sum(gradient[:35] ** 2, axis=1) + 1e-28) * 1e3 / np.sqrt(3)
                sigma_jac = np.einsum('ij,ijk->ik', gradient[:35], hessian[:35]) * (1e6 / 3) / sigma[:, None]
                cached.update(controls=controls.copy(), means=means, sigma=sigma, mean_jac=gradient[:35, CONTROL] * 1e6, sigma_jac=sigma_jac, tail=metrics[-1] * 1e6, tail_jac=gradient[-1, CONTROL] * 1e6)
            return cached

        def constraint(controls):
            result = state(controls)
            return np.r_[arguments.limit - result['means'] - arguments.risk * result['sigma'], arguments.limit + result['means'] - arguments.risk * result['sigma']]

        def constraint_jac(controls):
            result = state(controls)
            return np.vstack((-result['mean_jac'] - arguments.risk * result['sigma_jac'], result['mean_jac'] - arguments.risk * result['sigma_jac']))

        result = minimize(lambda controls: -arguments.sign * state(controls)['tail'] / 20, initial, jac=lambda controls: -arguments.sign * state(controls)['tail_jac'] / 20, method='SLSQP', bounds=list(zip(-BOUNDS+.0011, BOUNDS-.0011)), constraints=[dict(type='ineq', fun=constraint, jac=constraint_jac)], options=dict(maxiter=arguments.iterations, ftol=1e-8))
        summary = engine.summary(result.x)
        likelihood = probability(engine, result.x)
        destination = arguments.prefix + '_%03d.json' % trial
        save(destination, result.x)
        feasible = min(constraint(result.x)) > -1e-4
        quality = arguments.sign * summary['tail']
        if quality > best and feasible:
            best = quality
            save(arguments.output, result.x)
        print(json.dumps(dict(trial=trial, destination=destination, elapsed=time.monotonic()-started, status=result.message, iterations=result.nit, feasible=bool(feasible), probability=likelihood, **summary)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pattern')
    parser.add_argument('--trials', type=int, default=20)
    parser.add_argument('--seed', type=int, default=625)
    parser.add_argument('--spread', type=float, default=.06)
    parser.add_argument('--risk', type=float, default=2.8)
    parser.add_argument('--limit', type=float, default=.95)
    parser.add_argument('--sign', type=int, default=-1)
    parser.add_argument('--iterations', type=int, default=200)
    parser.add_argument('--output', default='maximum.json')
    parser.add_argument('--prefix', default='maximum')
    maximize_search(parser.parse_args())
