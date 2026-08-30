import argparse

import numpy as np

from optimize import Problem, COSTS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('continuous')
    parser.add_argument('--data', default='stress_training.npz')
    parser.add_argument('--tail', type=float, default=5)
    parser.add_argument('--output', default='count')
    args = parser.parse_args()
    problem = Problem(np.load(args.data), tail=args.tail, boost=1.2)
    batches = np.load(args.continuous)
    selected = np.flatnonzero(batches > 1e-6)
    values, objective = problem.optimize(selected, batches[selected])
    print('count', len(selected), objective, flush=True)
    while len(selected) > 21:
        choices = []
        for position in range(len(selected)):
            trial_selected = np.delete(selected, position)
            trial_values, trial_objective = problem.optimize(trial_selected, np.delete(values, position))
            choices.append((trial_objective, trial_selected, trial_values))
        objective, selected, values = min(choices, key=lambda choice: choice[0])
        trial = np.zeros(len(COSTS))
        trial[selected] = values
        trial = problem.exchange(trial)
        selected = np.flatnonzero(trial > 1e-6)
        values = trial[selected]
        objective = problem.evaluate(values, selected)
        np.save(args.output + str(len(selected)) + '.npy', trial)
        print('count', len(selected), objective, flush=True)


if __name__ == '__main__':
    main()
