from robust import *
from scipy.special import expit


def run(arguments):
    engine = Engine()
    rng = np.random.default_rng(arguments.seed)
    uniforms = rng.random((arguments.samples * 2, 100))
    original_noise = .002 * uniforms - .001
    original_noise[:arguments.samples, np.setdiff1d(np.arange(100), CONTROL)] = 0
    paths = sorted(Path('.').glob(arguments.pattern))
    started = time.monotonic()
    best = -np.inf
    scales = np.r_[np.full(21, arguments.hopping_scale), np.ones(21)]
    for trial, path in enumerate(paths):
        initial = coefficients(model.load_witness(path))[CONTROL]
        sign = np.sign(engine.evaluate(initial)[0][-1])
        cached = {}

        def state(controls):
            if 'controls' not in cached or not np.array_equal(cached['controls'], controls):
                metrics, gradient, physical, hessian = engine.evaluate(controls, hessian=True)
                lower = np.maximum(-BOUNDS, controls-.001)
                upper = np.minimum(BOUNDS, controls+.001)
                noise = original_noise.copy()
                noise[:, CONTROL] = lower + uniforms[:, CONTROL] * (upper-lower) - controls
                noise_jac = (controls-.001 > -BOUNDS)[None, :] * (1-uniforms[:, CONTROL]) + (controls+.001 < BOUNDS)[None, :] * uniforms[:, CONTROL]
                values = (metrics[None, :] + noise @ gradient.T) * 1e6
                active = np.argmax(np.abs(values[:, :35]), axis=1)
                active_values = values[np.arange(len(noise)), active]
                active_jac = (gradient[active][:, CONTROL] * noise_jac + np.einsum('ni,nij->nj', noise, hessian[active])) * (1e6 * np.sign(active_values))[:, None]
                parents = np.abs(active_values)
                tails = values[:, -1] * sign
                tail_jac = (gradient[-1, CONTROL][None, :] * noise_jac + noise @ hessian[-1]) * (1e6 * sign)
                limits = np.minimum(1, tails / 100)
                margin = limits - parents
                margin_jac = (tails < 100)[:, None] * tail_jac / 100 - active_jac
                tail_margin = (tails - 50) / 30
                tail_active = tail_margin < margin
                margin[tail_active] = tail_margin[tail_active]
                margin_jac[tail_active] = tail_jac[tail_active] / 30
                means = metrics[:35] * 1e6
                cached.update(controls=controls.copy(), margin=margin, margin_jac=margin_jac, means=means, mean_jac=gradient[:35, CONTROL] * 1e6, tail=metrics[-1] * sign * 1e6, tail_jac=gradient[-1, CONTROL] * sign * 1e6, physical=physical[:2], physical_jac=engine.physical_jacobian.copy())
            return cached

        def objective(controls, temperature):
            result = state(controls)
            probability_values = expit(result['margin'] / temperature)
            weights = np.ones(len(original_noise))
            weights[:arguments.samples] *= arguments.vv_weight
            if np.mean(probability_values[:arguments.samples]) >= .99:
                weights[:arguments.samples] = 0
            cost = -arguments.vv_weight * min(.99, np.mean(probability_values[:arguments.samples])) - np.mean(probability_values[arguments.samples:])
            derivative = -np.sum((weights * probability_values * (1-probability_values) / temperature)[:, None] * result['margin_jac'], axis=0) / arguments.samples
            return cost, derivative

        def constraints(controls):
            result = state(controls)
            return np.r_[.98-result['means'], .98+result['means'], .0098*result['tail']-result['means'], .0098*result['tail']+result['means'], (result['tail']-arguments.minimum_tail)/20, (result['physical']-np.array([.951, .42]))*np.array([100, 10])]

        def constraint_jac(controls):
            result = state(controls)
            return np.vstack((-result['mean_jac'], result['mean_jac'], .0098*result['tail_jac']-result['mean_jac'], .0098*result['tail_jac']+result['mean_jac'], result['tail_jac'][None, :]/20, result['physical_jac']*np.array([100,10])[:, None]))

        current = initial
        for temperature in arguments.temperatures:
            def scaled_objective(variables):
                cost, derivative = objective(variables*scales, temperature)
                return cost, derivative*scales
            result = minimize(scaled_objective, current/scales, jac=True, method='SLSQP', bounds=list(zip(-BOUNDS/scales, BOUNDS/scales)), constraints=[dict(type='ineq', fun=lambda variables: constraints(variables*scales), jac=lambda variables: constraint_jac(variables*scales)*scales)], options=dict(maxiter=arguments.iterations, ftol=1e-8))
            current = np.clip(result.x*scales, -BOUNDS, BOUNDS)
            likelihood = probability(engine, current, 8192)
            summary = engine.summary(current)
            destination = arguments.prefix+'_%03d_%s.json'%(trial,str(temperature).replace('.',''))
            save(destination,current)
            quality = min(1,likelihood['vv']['success']/.95) + min(1,likelihood['full']['success']/.95)
            feasible = min(constraints(current)) >= -1e-5
            if quality > best and feasible:
                best = quality
                save(arguments.output,current)
                save('witness.json',current)
            print(json.dumps(dict(trial=trial, source=str(path), destination=destination, temperature=temperature, elapsed=time.monotonic()-started, cost=result.fun, status=result.message, iterations=result.nit, feasible=bool(feasible), probability=likelihood, **summary)),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=997256)
    parser.add_argument('--samples',type=int,default=512)
    parser.add_argument('--pattern',default='catalog_*.json')
    parser.add_argument('--temperatures',nargs='+',type=float,default=[.3,.15,.07])
    parser.add_argument('--vv-weight',type=float,default=1)
    parser.add_argument('--minimum-tail',type=float,default=52)
    parser.add_argument('--hopping-scale',type=float,default=1)
    parser.add_argument('--iterations',type=int,default=150)
    parser.add_argument('--prefix',default='success')
    parser.add_argument('--output',default='success.json')
    run(parser.parse_args())
