from robust import *


def minimax_search(arguments):
    engine = Engine()
    paths = sorted(Path('.').glob(arguments.pattern))
    started = time.monotonic()
    best = np.inf
    selected = CONTROL if arguments.family == 'vv' else np.arange(100)
    for trial, path in enumerate(paths):
        initial = coefficients(model.load_witness(path))[CONTROL]
        desired_tail = arguments.tail if arguments.tail else np.sign(engine.evaluate(initial)[0][-1]) * arguments.tailmag
        cached = {}

        def state(variables):
            controls = variables[:42]
            if 'controls' not in cached or not np.array_equal(cached['controls'], controls):
                metrics, gradient, physical, hessian = engine.evaluate(controls, hessian=True)
                means = metrics[:35] * 1e6
                sigma = np.sqrt(np.sum(gradient[:35, selected] ** 2, axis=1) + 1e-28) * 1e3 / np.sqrt(3)
                sigma_jac = np.einsum('ij,ijk->ik', gradient[:35, selected], hessian[:35, selected]) * (1e6 / 3) / sigma[:, None]
                cached.update(controls=controls.copy(), means=means, sigma=sigma, mean_jac=gradient[:35, CONTROL] * 1e6, sigma_jac=sigma_jac, tail=metrics[-1] * 1e6, tail_jac=gradient[-1, CONTROL] * 1e6)
            return cached

        initial_state = state(initial)
        variables = np.r_[initial, max(np.abs(initial_state['means']) + arguments.risk * initial_state['sigma'])]

        def constraint(variables):
            result = state(variables)
            return np.r_[variables[-1] - result['means'] - arguments.risk * result['sigma'], variables[-1] + result['means'] - arguments.risk * result['sigma']]

        def constraint_jac(variables):
            result = state(variables)
            return np.column_stack((np.vstack((-result['mean_jac'] - arguments.risk * result['sigma_jac'], result['mean_jac'] - arguments.risk * result['sigma_jac'])), np.ones(70)))

        constraints = [dict(type='ineq', fun=constraint, jac=constraint_jac), dict(type='eq', fun=lambda variables: (state(variables)['tail'] - desired_tail) / 20, jac=lambda variables: np.r_[state(variables)['tail_jac'] / 20, 0])]
        result = minimize(lambda variables: variables[-1], variables, jac=lambda variables: np.r_[np.zeros(42), 1], method='SLSQP', bounds=list(zip(-BOUNDS+.0011, BOUNDS-.0011)) + [(0, None)], constraints=constraints, options=dict(maxiter=arguments.iterations, ftol=1e-8))
        controls = result.x[:42]
        summary = engine.summary(controls)
        likelihood = probability(engine, controls)
        destination = arguments.prefix + '_%03d.json' % trial
        save(destination, controls)
        if result.fun < best and abs(summary['tail']-desired_tail) < .1:
            best = result.fun
            save(arguments.output, controls)
        print(json.dumps(dict(trial=trial, source=str(path), destination=destination, elapsed=time.monotonic()-started, risk=result.fun, status=result.message, iterations=result.nit, probability=likelihood, **summary)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pattern', default='robust_*.json')
    parser.add_argument('--risk', type=float, default=2.8)
    parser.add_argument('--family', default='full')
    parser.add_argument('--tail', type=float, default=-55)
    parser.add_argument('--tailmag', type=float, default=105)
    parser.add_argument('--iterations', type=int, default=250)
    parser.add_argument('--output', default='minimax.json')
    parser.add_argument('--prefix', default='minimax')
    minimax_search(parser.parse_args())
