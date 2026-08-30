from robust import *


def chance_search(arguments):
    engine = Engine()
    paths = sorted(Path('.').glob(arguments.pattern))
    started = time.monotonic()
    rng = np.random.default_rng(arguments.seed)
    noise = rng.uniform(-.001, .001, (arguments.samples, 100))
    noise[:arguments.samples // 4, np.setdiff1d(np.arange(100), CONTROL)] = 0
    if arguments.family == 'vv':
        noise[:, np.setdiff1d(np.arange(100), CONTROL)] = 0
    top_count = max(1, int(arguments.samples * arguments.fraction))
    best = np.inf
    for trial, path in enumerate(paths):
        initial = coefficients(model.load_witness(path))[CONTROL]
        desired_tail = arguments.tail if arguments.tail else np.sign(engine.evaluate(initial)[0][-1]) * arguments.tailmag
        cached = {}

        def state(controls):
            if 'controls' not in cached or not np.array_equal(cached['controls'], controls):
                metrics, gradient, physical, hessian = engine.evaluate(controls, hessian=True)
                means = metrics[:35] * 1e6
                values = means[None, :] + 1e6 * noise @ gradient[:35].T
                active = np.argmax(np.abs(values), axis=1)
                active_values = values[np.arange(len(noise)), active]
                active_jac = (gradient[active][:, CONTROL] + np.einsum('ni,nij->nj', noise, hessian[active])) * (1e6 * np.sign(active_values))[:, None]
                parents = np.abs(active_values)
                worst = np.argpartition(parents, -top_count)[-top_count:]
                cost = np.mean(parents[worst])
                derivative = np.mean(active_jac[worst], axis=0)
                cached.update(controls=controls.copy(), cost=cost, derivative=derivative, means=means, mean_jac=gradient[:35, CONTROL] * 1e6, tail=metrics[-1] * 1e6, tail_jac=gradient[-1, CONTROL] * 1e6)
            return cached

        constraints = [dict(type='ineq', fun=lambda controls: np.r_[arguments.parent-state(controls)['means'], arguments.parent+state(controls)['means']], jac=lambda controls: np.vstack((-state(controls)['mean_jac'], state(controls)['mean_jac']))), dict(type='eq', fun=lambda controls: (state(controls)['tail'] - desired_tail) / 20, jac=lambda controls: state(controls)['tail_jac'] / 20)]
        result = minimize(lambda controls: state(controls)['cost'], initial, jac=lambda controls: state(controls)['derivative'], method='SLSQP', bounds=list(zip(-BOUNDS+.0011, BOUNDS-.0011)), constraints=constraints, options=dict(maxiter=arguments.iterations, ftol=1e-7))
        summary = engine.summary(result.x)
        likelihood = probability(engine, result.x)
        destination = arguments.prefix + '_%03d.json' % trial
        save(destination, result.x)
        if result.fun < best and abs(summary['tail']-desired_tail) < .1 and summary['parent'] < arguments.parent + 1e-4:
            best = result.fun
            save(arguments.output, result.x)
        print(json.dumps(dict(trial=trial, source=str(path), destination=destination, elapsed=time.monotonic()-started, cost=result.fun, status=result.message, iterations=result.nit, probability=likelihood, **summary)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pattern', default='robust_*.json')
    parser.add_argument('--samples', type=int, default=512)
    parser.add_argument('--family', default='full')
    parser.add_argument('--seed', type=int, default=651329)
    parser.add_argument('--fraction', type=float, default=.1)
    parser.add_argument('--tail', type=float, default=-70)
    parser.add_argument('--tailmag', type=float, default=105)
    parser.add_argument('--parent', type=float, default=.3)
    parser.add_argument('--iterations', type=int, default=200)
    parser.add_argument('--output', default='chance.json')
    parser.add_argument('--prefix', default='chance')
    chance_search(parser.parse_args())
