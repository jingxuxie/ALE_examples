import argparse
import time
import numpy as np
import fermion
from search import Engine


def expand(engine, labels, angles, extra, rng, width=5, temperature=0.0):
    for step in range(extra):
        values, optimal = engine.options(labels, angles)
        order = np.argsort(values.ravel())[::-1]
        top = order[:width]
        if temperature:
            top = rng.choice(order[:max(width, int(temperature))], width, replace=False)
        trials = []
        for flat in top:
            position, label = np.unravel_index(flat, values.shape)
            trial = engine.optimize(np.insert(labels, position, label), np.insert(angles, position, optimal[position, label]), 150)
            trials.append(trial)
        labels, angles, loss = min(trials, key=lambda trial: trial[2])
    return labels, angles, loss


def contract(engine, labels, angles, cap, rng, width=100):
    while len(labels) > cap:
        trials = []
        positions = np.argsort(np.abs(np.sin(angles)))[:width]
        for position in positions:
            trial = engine.optimize(np.delete(labels, position), np.delete(angles, position), 120)
            trials.append(trial)
        labels, angles, loss = min(trials, key=lambda trial: trial[2])
    return labels, angles, loss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, default=0)
    parser.add_argument('--seconds', type=float, default=300)
    parser.add_argument('--seed', type=int, default=22)
    parser.add_argument('--extra', type=int, default=3)
    args = parser.parse_args()
    engine = Engine(fermion.load_cases()[args.case])
    labels, angles, loss = engine.load()
    engine.best = loss
    best = labels.copy(), angles.copy(), loss
    rng = np.random.default_rng(args.seed)
    iteration = 0
    while time.time() - engine.started < args.seconds and engine.best > 1e-12:
        iteration += 1
        extra = int(rng.integers(1, args.extra + 1))
        temperature = 0 if iteration % 4 == 0 else rng.choice([20, 50, 100])
        grown = expand(engine, labels, angles, extra, rng, 5, temperature)
        labels, angles, loss = contract(engine, grown[0], grown[1], engine.case.max_gates, rng)
        if loss < engine.best:
            engine.save(labels, angles, loss)
            best = labels.copy(), angles.copy(), loss
        elif iteration % 3 == 0 or loss > engine.best + 0.005:
            labels, angles, loss = best[0].copy(), best[1].copy(), best[2]
        if iteration % 10 == 0:
            print('iteration',iteration,'best',engine.best,'elapsed',time.time()-engine.started,flush=True)


if __name__ == '__main__':
    main()
