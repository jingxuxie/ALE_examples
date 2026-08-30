import argparse
import glob
import json
import time
from pathlib import Path
import numpy as np
import fermion
from search import Engine


def grow(engine, labels, angles, cap, rng, randomize=0):
    while len(labels) < cap:
        values, optimal = engine.projected(labels, angles)
        order = np.argsort(values.ravel())[::-1]
        selected = order[:8]
        if randomize:
            selected = rng.choice(order[:randomize], 5, replace=False)
        trials = []
        for flat in selected:
            position, label = np.unravel_index(flat, values.shape)
            trials.append(engine.optimize(np.insert(labels, position, label), np.insert(angles, position, optimal[position, label]), 150))
        labels, angles, loss = min(trials, key=lambda trial: trial[2])
    return labels, angles, loss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, default=0)
    parser.add_argument('--seconds', type=float, default=600)
    parser.add_argument('--population', type=int, default=80)
    parser.add_argument('--seed', type=int, default=554)
    args = parser.parse_args()
    engine = Engine(fermion.load_cases()[args.case])
    labels, angles, loss = engine.load()
    engine.best = loss
    population = {tuple(sorted(labels)): (labels, angles, loss)}
    for filename in glob.glob(str(Path(__file__).resolve().parent / (engine.case.case_id + '_beam_*.json'))):
        suffix = Path(filename).stem[len(engine.case.case_id) + 1:]
        labels, angles, loss = engine.load(suffix)
        key = tuple(sorted(labels))
        if key not in population or loss < population[key][2]:
            population[key] = labels, angles, loss
    rng = np.random.default_rng(args.seed)
    iteration = 0
    while time.time() - engine.started < args.seconds and engine.best > 1e-12:
        iteration += 1
        ordered = sorted(population.values(), key=lambda item: item[2])[:args.population]
        population = {tuple(sorted(item[0])): item for item in ordered}
        parent = ordered[min(int(rng.exponential(max(2, len(ordered) / 3))), len(ordered) - 1)]
        labels, angles, loss = parent[0].copy(), parent[1].copy(), parent[2]
        state, _ = engine.state_jac(labels, angles)
        if state @ engine.target < 0:
            engine.target = -engine.target
        mutation = rng.random()
        if mutation < 0.7:
            removed = rng.choice(len(labels), int(rng.choice([1,2,2,3,3,4,5,7])), replace=False)
            labels = np.delete(labels, removed)
            angles = np.delete(angles, removed)
            labels, angles, loss = engine.optimize(labels, angles, 200)
            labels, angles, loss = grow(engine, labels, angles, engine.case.max_gates, rng, randomize=int(rng.choice([0,20,40,100])))
        elif mutation < 0.87:
            for move in range(int(rng.integers(1,5))):
                source, destination = rng.choice(len(labels), 2, replace=False)
                label, angle = labels[source], angles[source]
                labels = np.insert(np.delete(labels, source), destination, label)
                angles = np.insert(np.delete(angles, source), destination, angle)
            labels, angles, loss = engine.optimize(labels, angles, 300)
        elif mutation < 0.96:
            other = ordered[int(rng.integers(len(ordered)))]
            split = int(rng.integers(2, len(labels)-2))
            labels[split:] = other[0][split:]
            angles[split:] = other[1][split:]
            labels, angles, loss = engine.optimize(labels, angles, 300)
        else:
            positions = rng.choice(len(labels), int(rng.integers(1,len(labels)+1)), replace=False)
            angles[positions] += rng.normal(0, 1.5, len(positions))
            labels, angles, loss = engine.optimize(labels, angles, 300)
        if loss < engine.best - 1e-10:
            labels, angles, loss = engine.polish(labels, angles, loss, rounds=20, width=50)
            engine.save(labels, angles, loss)
        key = tuple(sorted(labels))
        if key not in population or loss < population[key][2]:
            population[key] = labels, angles, loss
        if iteration % 100 == 0:
            print('generation',iteration,'best',engine.best,'population',len(population),'worst',ordered[-1][2],'elapsed',time.time()-engine.started,flush=True)
    for position, item in enumerate(sorted(population.values(), key=lambda item:item[2])[:args.population]):
        engine.save(*item, suffix='evolve_' + str(position))


if __name__ == '__main__':
    main()
