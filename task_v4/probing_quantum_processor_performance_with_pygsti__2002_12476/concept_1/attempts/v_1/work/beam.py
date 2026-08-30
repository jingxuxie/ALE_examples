import argparse
import json
import time
from pathlib import Path

import numpy as np

from optimize import Problem, COSTS, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='qmc_training.npz')
    parser.add_argument('--output', default='design_beam.json')
    parser.add_argument('--width', type=int, default=10)
    parser.add_argument('--branches', type=int, default=5)
    parser.add_argument('--tail', type=float, default=3)
    parser.add_argument('--boost', type=float, default=1.2)
    args = parser.parse_args()
    problem = Problem(np.load(args.data), tail=args.tail, boost=args.boost)
    continuous = problem.continuous(350, 274)
    np.save('qmc_relaxed.npy', continuous)
    selected = np.argsort(continuous * COSTS)[-120:]
    batches = np.zeros(len(COSTS))
    batches[selected] = continuous[selected]
    batches = problem.prune_exact(batches, target=42)
    selected = np.flatnonzero(batches > 1e-6)
    values = batches[selected]
    states = [(problem.evaluate(values, selected), selected, values)]
    started = time.time()
    while len(states[0][1]) > 24:
        next_states = []
        seen = set()
        for objective, selected, values in states:
            losses = problem.remove_losses(selected, values)
            for removed in np.argsort(losses)[:args.branches]:
                trial_selected = np.delete(selected, removed)
                key = tuple(sorted(trial_selected))
                if key in seen:
                    continue
                seen.add(key)
                trial_values, trial_objective = problem.optimize(trial_selected, np.delete(values, removed))
                next_states.append((trial_objective, trial_selected, trial_values))
        next_states.sort(key=lambda state: state[0])
        states = next_states[:args.width]
        print('beam', len(states[0][1]), states[0][0], states[-1][0], 'seconds', time.time() - started, flush=True)
    best = None
    best_value = np.inf
    for position, (objective, selected, values) in enumerate(states):
        batches = np.zeros(len(COSTS))
        batches[selected] = values
        batches = problem.exchange(batches)
        objective = problem.evaluate(batches)
        print('refined', position, objective, flush=True)
        if objective < best_value:
            best, best_value = batches, objective
            np.save(args.output.replace('.json', '_continuous.npy'), best)
    integer = problem.integer(best)
    Path(args.output).write_text(json.dumps({'batches': integer.tolist()}) + '\n')
    report(integer, args.output)


if __name__ == '__main__':
    main()
