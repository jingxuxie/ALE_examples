import argparse
import time
import numpy as np
import fermion
from search import Engine
from local import insert


def contract(engine, labels, angles, cap, rng):
    while len(labels) > cap:
        state, jacobian = engine.state_jac(labels, angles)
        inverse = np.linalg.inv(jacobian.T @ jacobian + 1e-8 * np.eye(len(labels)))
        scores = angles * angles / np.diag(inverse)
        candidates = np.argsort(scores)[:min(25, len(labels))]
        trials = []
        for position in candidates:
            projected = angles - angles[position] * inverse[:, position] / inverse[position, position]
            trials.append(engine.optimize(np.delete(labels, position), np.delete(projected, position), 250))
            if abs(angles[position]) > 0.4:
                trials.append(engine.optimize(np.delete(labels, position), np.delete(angles, position), 250))
        labels, angles, loss = min(trials, key=lambda trial: trial[2])
        if len(labels) % 5 == 0 or len(labels) == cap:
            print('contract',len(labels),loss,'elapsed',time.time()-engine.started,flush=True)
    return labels, angles, loss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, default=0)
    parser.add_argument('--size', type=int, default=70)
    parser.add_argument('--seconds', type=float, default=300)
    parser.add_argument('--seed', type=int, default=234)
    args = parser.parse_args()
    engine = Engine(fermion.load_cases()[args.case])
    labels, angles, loss = engine.load()
    engine.best = loss
    rng = np.random.default_rng(args.seed)
    iteration = 0
    while time.time() - engine.started < args.seconds:
        iteration += 1
        if iteration > 1:
            labels, angles, loss = engine.load()
            for mutation in range(5):
                position = rng.integers(len(labels))
                labels = np.delete(labels, position)
                angles = np.delete(angles, position)
            labels, angles, loss = engine.optimize(labels, angles, 300)
        while len(labels) < args.size and loss > 1e-15:
            labels, angles, loss = insert(engine, labels, angles, choices=5)
            if len(labels) % 10 == 0:
                print('expand',len(labels),loss,'elapsed',time.time()-engine.started,flush=True)
        engine.save(labels, angles, loss, 'large')
        labels, angles, loss = contract(engine, labels, angles, engine.case.max_gates, rng)
        engine.save(labels, angles, loss)
        labels, angles, loss = engine.polish(labels, angles, loss, rounds=20, width=30)
        print('round',iteration,'best',engine.best,'elapsed',time.time()-engine.started,flush=True)


if __name__ == '__main__':
    main()
