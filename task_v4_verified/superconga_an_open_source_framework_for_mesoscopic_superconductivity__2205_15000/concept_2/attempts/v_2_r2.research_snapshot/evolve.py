import argparse
import json
import time

import numpy as np

from discrete import Swaps, feasible
from optimize import Inverse, OUTPUT, binary, save_best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycles', type=int, default=50)
    parser.add_argument('--seed', type=int, default=556)
    parser.add_argument('--double', type=int, default=192)
    arguments = parser.parse_args()
    random = np.random.default_rng(arguments.seed)
    inverse = Inverse(stride=2)
    swaps = Swaps(inverse)
    global_pattern = np.asarray(json.loads((OUTPUT / 'design.json').read_text())['pattern'], dtype=float)
    global_error = inverse.error(global_pattern)
    pool = [(global_error, global_pattern.copy())]
    continuous = sorted(OUTPUT.glob('continuous_*.npz'), key=lambda path: float(np.load(path)['error']))
    start = time.time()
    total_steps = 0
    for cycle in range(arguments.cycles):
        if (OUTPUT / 'STOP').exists():
            break
        if cycle == 0:
            pattern = global_pattern.copy()
        elif cycle == 1 and (OUTPUT / 'discrete_445.npz').exists():
            pattern = np.load(OUTPUT / 'discrete_445.npz')['pattern']
        elif cycle % 5 == 2 and continuous:
            pattern = binary(np.load(continuous[(cycle // 5) % len(continuous)])['pattern'])
        elif cycle % 5 == 3:
            while True:
                pattern = binary(random.random(64))
                if feasible(inverse, pattern):
                    break
        else:
            parents = random.choice(len(pool), 2, replace=True)
            first = pool[parents[0]][1]
            second = pool[parents[1]][1]
            for attempt in range(100):
                priority = first + second + random.uniform(-0.9, 0.9, 64)
                pattern = binary(priority)
                count = random.integers(2, 7)
                pattern[random.choice(np.flatnonzero(pattern), count, replace=False)] = 0
                pattern[random.choice(np.flatnonzero(1 - pattern), count, replace=False)] = 1
                if feasible(inverse, pattern):
                    break
        cycle_best = float('inf')
        cycle_pattern = pattern.copy()
        stages = [('linear', 6), ('sqrt', 2), ('linear', 0)]
        if cycle % 3 == 1:
            stages = [('log', 2), ('linear', 2), ('linear', 0)]
        if cycle % 3 == 2:
            stages = [('linear', 0), ('linear', 4), ('linear', 0)]
        for stage, (loss, smoothing) in enumerate(stages):
            inverse.loss = loss
            inverse.smoothing = smoothing
            best_stage = inverse.error(pattern)
            stage_pattern = pattern.copy()
            stale = 0
            tabu = set()
            for step in range(55):
                if (OUTPUT / 'STOP').exists():
                    return
                current_error = swaps.prepare(pattern)
                pairs = swaps.choices()
                errors = swaps.evaluate(pairs, store=bool(arguments.double))
                raw_errors = swaps.raw_errors.copy()
                mutations = [tuple(pair) for pair in pairs]
                if arguments.double and (np.min(errors) >= current_error - 1e-6 or step % 5 == 4):
                    doubles = swaps.double_choices(pairs, errors, count=arguments.double)
                    double_errors = swaps.evaluate(doubles)
                    errors = np.concatenate([errors, double_errors])
                    raw_errors = np.concatenate([raw_errors, swaps.raw_errors])
                    mutations.extend(tuple(mutation) for mutation in doubles)
                choice = None
                for candidate in np.argsort(errors):
                    changed = pattern.copy()
                    selected = np.asarray(mutations[candidate])
                    changed[selected] = 1 - changed[selected]
                    key = np.packbits(changed.astype(np.uint8)).tobytes()
                    if key in tabu:
                        continue
                    if feasible(inverse, changed):
                        choice = candidate
                        break
                if choice is None:
                    break
                tabu.add(np.packbits(pattern.astype(np.uint8)).tobytes())
                pattern = changed
                error = errors[choice]
                raw_error = raw_errors[choice]
                stale += 1
                total_steps += 1
                if error < best_stage - 1e-9:
                    best_stage = error
                    stage_pattern = pattern.copy()
                    stale = 0
                if raw_error < cycle_best - 1e-9:
                    cycle_best = raw_error
                    cycle_pattern = pattern.copy()
                if raw_error < global_error - 1e-9:
                    global_error = raw_error
                    global_pattern = pattern.copy()
                    save_best(inverse, pattern)
                    np.savez(OUTPUT / f'evolve_{arguments.seed}_best.npz', pattern=pattern, error=global_error)
                print('EVOLVE', cycle, stage, step, 'time', round(time.time() - start, 1), 'objective', round(error, 7), 'raw', round(raw_error, 7), 'global', round(global_error, 7), 'stale', stale, 'mutation', mutations[choice], flush=True)
                if global_error < 0.035:
                    return
                if stale >= 10:
                    break
            pattern = stage_pattern.copy()
        pool.append((cycle_best, cycle_pattern.copy()))
        pool.sort(key=lambda item: item[0])
        diverse = []
        for error, candidate in pool:
            if all(np.sum(candidate != previous) >= 6 for unused, previous in diverse):
                diverse.append((error, candidate))
        pool = diverse[:16]
        np.savez(OUTPUT / f'elite_{arguments.seed}_{cycle}.npz', pattern=cycle_pattern, error=cycle_best)
        print('CYCLE', cycle, cycle_best, 'pool', [round(item[0], 6) for item in pool], 'steps', total_steps, flush=True)


if __name__ == '__main__':
    main()
