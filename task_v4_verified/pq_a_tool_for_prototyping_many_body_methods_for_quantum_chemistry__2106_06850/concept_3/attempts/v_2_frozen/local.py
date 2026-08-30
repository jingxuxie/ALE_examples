import argparse
import time
import numpy as np
import fermion
from search import Engine


def insert(engine, labels, angles, choices=10):
    values, optimal = engine.projected(labels, angles)
    order = np.argsort(values.ravel())[::-1]
    trials = []
    seen = set()
    for flat in order:
        position, label = np.unravel_index(flat, values.shape)
        fingerprint = (label, round(values[position, label], 8))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        trials.append(engine.optimize(np.insert(labels, position, label), np.insert(angles, position, optimal[position, label]), 200))
        if len(trials) >= choices:
            break
    return min(trials, key=lambda trial: trial[2])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, default=0)
    parser.add_argument('--seconds', type=float, default=300)
    parser.add_argument('--choices', type=int, default=10)
    args = parser.parse_args()
    engine = Engine(fermion.load_cases()[args.case])
    labels, angles, loss = engine.load()
    engine.best = loss
    rng = np.random.default_rng(144)
    iteration = 0
    while time.time() - engine.started < args.seconds:
        iteration += 1
        baseline = loss
        for position in rng.permutation(len(labels)):
            removed = engine.optimize(np.delete(labels, position), np.delete(angles, position), 200)
            trial = insert(engine, removed[0], removed[1], args.choices)
            if trial[2] < loss - 1e-11:
                labels, angles, loss = trial
                engine.save(labels, angles, loss)
        print('sweep',iteration,'loss',loss,'elapsed',time.time()-engine.started,flush=True)
        if loss >= baseline - 1e-11:
            for original in rng.permutation(len(labels)):
                base_labels = np.delete(labels, original)
                base_angles = np.delete(angles, original)
                for position in range(len(labels)):
                    if original == position:
                        continue
                    trial = engine.optimize(np.insert(base_labels, position, labels[original]), np.insert(base_angles, position, angles[original]), 100)
                    if trial[2] < loss - 1e-11:
                        labels, angles, loss = trial
                        engine.save(labels, angles, loss)
            if loss >= baseline - 1e-11:
                print('stationary',flush=True)
                break


if __name__ == '__main__':
    main()
