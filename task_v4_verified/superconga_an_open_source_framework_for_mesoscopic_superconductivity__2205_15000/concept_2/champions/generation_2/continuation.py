from optimize import *
from concurrent.futures import ProcessPoolExecutor


def worker(seed):
    logfile = open(OUT / f'continuation_{seed}.log', 'w', buffering=1)
    sys.stdout = logfile
    model = Model()
    random = np.random.default_rng(seed + 937)
    pattern = np.zeros(64)
    pattern[random.choice(64, 24, replace=False)] = 1
    if seed % 3 == 0:
        pattern = random.uniform(0, .75, 64)
    mode = ['linear', 'log', 'sqrt'][seed % 3]
    best = np.inf
    for stage, weight in enumerate([.02, .1, .3, 1., 3., 10.]):
        def objective(current):
            loss, gradient = model.evaluate(current, mode=mode)
            penalty = weight * np.mean(current*(1-current))
            return loss+penalty, gradient+weight*(1-2*current)/64

        result = minimize(objective, pattern, method='SLSQP', jac=True, bounds=[(0,1)]*64,
                          constraints=[{'type':'eq', 'fun':lambda current:current.sum()-24, 'jac':lambda current:np.ones(64)}],
                          options={'maxiter':250, 'ftol':1e-9})
        pattern = np.clip(result.x, 0, 1)
        binary = np.zeros(64, dtype=int)
        binary[np.argsort(pattern)[-24:]] = 1
        loss, observed = model.evaluate(binary, False)
        if loss < best:
            best = loss
            np.savez(OUT / f'annealed_{seed}.npz', pattern=pattern, binary=binary, binary_loss=loss)
        print('STAGE', stage, 'weight', weight, 'relaxed', result.fun, 'binary', loss, 'best', best, 'fractional', np.mean(pattern*(1-pattern)), 'eval', model.count, flush=True)
        np.savez(OUT / f'annealstate_{seed}.npz', pattern=pattern, binary=binary, binary_loss=loss)
    print('FINAL', seed, best, flush=True)
    return seed, best


if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=24) as pool:
        for result in pool.map(worker, range(48)):
            print(result, flush=True)
