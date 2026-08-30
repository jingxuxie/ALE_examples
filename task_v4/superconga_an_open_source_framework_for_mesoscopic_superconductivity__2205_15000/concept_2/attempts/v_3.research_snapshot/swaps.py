import argparse
import json
import time

import numpy as np
from scipy.ndimage import gaussian_filter1d

from discrete import FlipModel
from invert import OUT, response, discrepancies, validate_design


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--start', default='discrete_1_best.json')
    parser.add_argument('--stride', type=int, default=3)
    parser.add_argument('--conditions', type=int, default=1)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--screen', type=int, default=256)
    parser.add_argument('--sigma', type=float, default=0)
    parser.add_argument('--temperature', type=float, default=.0005)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--connected', action='store_true')
    parser.add_argument('--eta', type=float)
    arguments = parser.parse_args()
    model = FlipModel(stride=arguments.stride, conditions=list(range(arguments.conditions)))
    if arguments.eta:
        from broad import broaden
        broaden(model, arguments.eta)
    pattern = np.asarray(json.loads((OUT / arguments.start).read_text())['pattern'])
    rng = np.random.default_rng(arguments.seed)
    best = np.inf
    last_changed = np.full(len(pattern), -100)
    started = time.time()
    best_pattern = pattern.copy()
    stalled = 0
    def cost(output):
        error = (output - model.target) / model.scales
        if arguments.sigma:
            error = gaussian_filter1d(error, arguments.sigma, axis=-1)
        return np.mean(error ** 2, axis=(-1, -2, -3))
    for step in range(arguments.steps):
        observed, flipped = model.calculate_flips(pattern)
        current = cost(observed)
        if current < best - 1e-12:
            best = current
            best_pattern = pattern.copy()
            stalled = 0
            try:
                validate_design(model.config, pattern)
                feasible = True
            except ValueError:
                feasible = False
            np.save(OUT / f'swaps_{arguments.seed}_best.npy', pattern)
            (OUT / f'swaps_{arguments.seed}_best.json').write_text(json.dumps({'pattern': pattern.tolist()}) + '\n')
            print('BEST', step, np.sqrt(best), 'feasible', feasible, 'time', round(time.time() - started, 1), flush=True)
            if feasible:
                (OUT / f'swaps_{arguments.seed}_feasible.json').write_text(json.dumps({'pattern': pattern.tolist()}) + '\n')
        else:
            stalled += 1
        remove, add = np.meshgrid(np.flatnonzero(pattern), np.flatnonzero(1 - pattern), indexing='ij')
        remove = remove.flatten()
        add = add.flatten()
        if arguments.screen < len(remove):
            approximate = cost(flipped[remove] + flipped[add] - observed)
            ranked = np.argsort(approximate)[:arguments.screen]
            random_indices = rng.choice(len(remove), size=min(arguments.screen // 2, len(remove)), replace=False)
            selected = np.unique(np.concatenate([ranked, random_indices]))
            remove, add = remove[selected], add[selected]
        costs = []
        for offset in range(0, len(remove), 256):
            output = model.calculate_swaps(remove[offset:offset + 256], add[offset:offset + 256])
            costs.extend(cost(output))
            if arguments.check:
                for index in range(3):
                    changed = pattern.copy()
                    changed[remove[index]] = 0
                    changed[add[index]] = 1
                    actual = response(model.config, changed)[model.conditions][:, :, model.selection]
                    print('CHECK', remove[index], add[index], np.max(abs(actual - output[index])), flush=True)
                print('TIME', time.time() - started, flush=True)
                return
        costs = np.asarray(costs)
        if arguments.connected:
            for index in range(len(costs)):
                changed = pattern.copy()
                changed[remove[index]] = 0
                changed[add[index]] = 1
                try:
                    validate_design(model.config, changed)
                except ValueError:
                    costs[index] = np.inf
        taboo = (step - last_changed[remove] < 2 + step // 30 % 5) | (step - last_changed[add] < 2 + step // 30 % 5)
        costs[taboo & (costs >= best - 1e-8)] = np.inf
        temperature = arguments.temperature * (1 + min(stalled, 50) / 10)
        chosen = np.argmin(costs - rng.gumbel(size=len(costs)) * temperature)
        pattern[remove[chosen]] = 0
        pattern[add[chosen]] = 1
        last_changed[remove[chosen]] = step
        last_changed[add[chosen]] = step
        if step % 10 == 0:
            print('STEP', step, 'error', np.sqrt(current), 'next', np.sqrt(costs[chosen]), 'best', np.sqrt(best), 'time', round(time.time() - started, 1), flush=True)
        if stalled >= 80:
            pattern = best_pattern.copy()
            removed = rng.choice(np.flatnonzero(pattern), 3, replace=False)
            added = rng.choice(np.flatnonzero(1 - pattern), 3, replace=False)
            pattern[removed] = 0
            pattern[added] = 1
            last_changed[:] = -100
            stalled = 0


if __name__ == '__main__':
    main()
