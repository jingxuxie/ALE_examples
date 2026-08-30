from search import *


def probability(engine, controls, count=4096, seed=628691):
    metrics, jacobian, physical = engine.evaluate(controls)
    rng = np.random.default_rng(seed)
    output = {}
    for family in ("vv", "full"):
        indices = CONTROL if family == "vv" else np.arange(100)
        uniforms = rng.random((count, len(indices)))
        noise = .002 * uniforms - .001
        selected = np.arange(42) if family == 'vv' else CONTROL
        lower = np.maximum(-BOUNDS, controls-.001)
        upper = np.minimum(BOUNDS, controls+.001)
        noise[:, selected] = lower + uniforms[:, selected] * (upper-lower) - controls
        values = (metrics[None, :] + noise @ jacobian[:, indices].T) * 1e6
        parents = np.max(np.abs(values[:, :35]), axis=1)
        tails = np.abs(values[:, 35])
        passed = (parents <= 1) & (tails >= 50) & (tails >= 100 * parents)
        output[family] = dict(success=float(np.mean(passed)), p95=float(np.quantile(parents, .95)), p99=float(np.quantile(parents, .99)))
    return output


def search_robust(arguments):
    engine = Engine()
    starts = list(Path(".").glob(arguments.pattern))
    rng = np.random.default_rng(arguments.seed)
    best = -np.inf
    selected = CONTROL if arguments.family == 'vv' else np.arange(100)
    started = time.monotonic()
    for trial, path in enumerate(starts):
        initial = coefficients(model.load_witness(path))[CONTROL]
        cached = {}

        def objective(controls):
            if "controls" not in cached or not np.array_equal(controls, cached["controls"]):
                metrics, gradient, physical, hessian = engine.evaluate(controls, hessian=True)
                sigma_weight = arguments.risk / np.sqrt(3) * 1e3
                residual = np.r_[metrics[:35] * 1e6 * arguments.mean_weight, (gradient[:35, selected] * sigma_weight).ravel(), (metrics[-1] * 1e6 - arguments.tail) * arguments.tail_weight]
                derivative = np.vstack((gradient[:35, CONTROL] * 1e6 * arguments.mean_weight, (hessian[:35, selected] * sigma_weight).reshape(-1, 42), gradient[-1, CONTROL][None, :] * 1e6 * arguments.tail_weight))
                cached.update(controls=controls.copy(), residual=residual, derivative=derivative)
            return cached

        result = least_squares(lambda controls: objective(controls)["residual"], initial, jac=lambda controls: objective(controls)["derivative"], bounds=(-BOUNDS + 0.0011, BOUNDS - 0.0011), max_nfev=arguments.iterations, ftol=1e-9, xtol=1e-9, gtol=1e-7)
        summary = engine.summary(result.x)
        likelihood = probability(engine, result.x)
        quality = min(1, 1/max(summary['parent'], .0001), abs(summary['tail'])/50, abs(summary['tail'])/max(100*summary['parent'], .0001)) + min(1, likelihood['vv']['success']/.95) + min(1, likelihood['full']['success']/.95)
        if quality > best:
            best = quality
            save(arguments.output, result.x)
        destination = arguments.prefix + "_%03d.json" % trial
        save(destination, result.x)
        print(json.dumps(dict(trial=trial, source=str(path), destination=destination, elapsed=time.monotonic()-started, cost=result.cost, evaluations=result.nfev, probability=likelihood, **summary)), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=987)
    parser.add_argument("--pattern", default="trial_*.json")
    parser.add_argument("--risk", type=float, default=2)
    parser.add_argument("--family", default='full')
    parser.add_argument("--mean-weight", type=float, default=1)
    parser.add_argument("--tail", type=float, default=-100)
    parser.add_argument("--tail-weight", type=float, default=.2)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--output", default="robust.json")
    parser.add_argument("--prefix", default="robust")
    search_robust(parser.parse_args())
