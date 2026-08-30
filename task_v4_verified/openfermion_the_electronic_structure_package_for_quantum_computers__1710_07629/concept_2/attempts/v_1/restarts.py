import argparse
import time
from optimize import *


def run(instance, trials=400, seed=0):
    random = np.random.default_rng(seed)
    sources = []
    for path in Path('.').glob(instance['id'] + '*partial.json'):
        circuit = json.loads(path.read_text())
        if len(circuit['layers']) > instance['budgets']['max_depth']:
            continue
        edges, parameters = unpack(circuit)
        if len(edges) > instance['budgets']['max_gates']:
            continue
        residual = Fit(instance, edges).evaluate(parameters.ravel())[0]
        sources.append((np.linalg.norm(residual) * np.sqrt(2), edges, parameters))
    sources.sort(key=lambda item: item[0])
    sources = sources[:5]
    if not sources:
        print('NO SOURCES', flush=True)
        return
    best = sources[0][0]
    started = time.monotonic()
    for trial in range(trials):
        error, edges, parameters = sources[trial % len(sources)]
        guess = parameters.copy()
        if trial % 5 == 0:
            guess += random.normal(scale=0.5, size=guess.shape)
        elif trial % 5 == 1:
            guess = random.normal(scale=0.8, size=guess.shape)
        else:
            selected = random.choice(len(guess), size=1 + (trial % 3), replace=False)
            radii = np.linalg.norm(guess[selected], axis=1)
            guess[selected] *= (1 + random.choice([-1, 1], size=len(selected)) * np.pi / 2 / np.maximum(radii, 1e-12))[:, None]
            guess += random.normal(scale=0.02, size=guess.shape)
        parameters, error = Fit(instance, edges).solve(guess, evaluations=300, tolerance=1e-11)
        if error < best - 1e-10:
            best = error
            sources[trial % len(sources)] = error, edges, parameters
            print('BEST', instance['id'], trial, best, 'time', round(time.monotonic() - started, 1), flush=True)
        if error < 1e-8:
            Path(instance['id'] + '_restart.json').write_text(json.dumps(pack(instance, edges, parameters)))
            print('SOLVED', instance['id'], error, flush=True)
            return
        if trial % 20 == 0:
            print('TRIAL', instance['id'], trial, best, 'time', round(time.monotonic() - started, 1), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--trials', type=int, default=400)
    arguments = parser.parse_args()
    run(INSTANCES[arguments.index], arguments.trials)
