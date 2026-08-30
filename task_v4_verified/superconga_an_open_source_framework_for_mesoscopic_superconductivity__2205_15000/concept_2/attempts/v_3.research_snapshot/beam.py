import json
import time
import argparse

import numpy as np

from discrete import FlipModel
from invert import OUT, ROOT, load_problem, response, discrepancies, validate_design


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start')
    parser.add_argument('--conditions', type=int, default=1)
    parser.add_argument('--depth', type=int, default=20)
    parser.add_argument('--width', type=int, default=24)
    parser.add_argument('--tag', default='beam')
    arguments = parser.parse_args()
    model = FlipModel(stride=3, conditions=list(range(arguments.conditions)))
    if arguments.start:
        pattern = np.asarray(json.loads((OUT / arguments.start).read_text())['pattern'])
    else:
        pattern = np.load(OUT / 'seed418.npy').astype(int)
        pattern[65] = 0
        pattern[34] = 1
    beams = [pattern]
    seen = {np.packbits(pattern).tobytes()}
    rng = np.random.default_rng(88)
    best = np.inf
    started = time.time()
    for depth in range(arguments.depth):
        children = []
        for parent in beams:
            observed, flipped = model.calculate_flips(parent)
            remove, add = np.meshgrid(np.flatnonzero(parent), np.flatnonzero(1 - parent), indexing='ij')
            remove, add = remove.ravel(), add.ravel()
            approximate = np.mean(((flipped[remove] + flipped[add] - observed - model.target) / model.scales) ** 2, axis=(1, 2, 3))
            chosen = np.unique(np.concatenate([np.argsort(approximate)[:256], rng.choice(len(remove), 64, replace=False)]))
            remove, add = remove[chosen], add[chosen]
            costs = []
            for offset in range(0, len(remove), 128):
                output = model.calculate_swaps(remove[offset:offset + 128], add[offset:offset + 128])
                costs.extend(np.mean(((output - model.target) / model.scales) ** 2, axis=(1, 2, 3)))
            added = 0
            for index in np.argsort(costs):
                child = parent.copy()
                child[remove[index]] = 0
                child[add[index]] = 1
                key = np.packbits(child).tobytes()
                if key in seen:
                    continue
                try:
                    validate_design(model.config, child)
                except ValueError:
                    continue
                seen.add(key)
                children.append((costs[index], child))
                added += 1
                if costs[index] < best:
                    best = costs[index]
                    np.save(OUT / f'{arguments.tag}_best.npy', child)
                    (OUT / f'{arguments.tag}_best.json').write_text(json.dumps({'pattern': child.tolist()}) + '\n')
                    print('BEST', depth, np.sqrt(best), 'distance', np.sum(child != pattern), 'time', round(time.time() - started, 1), flush=True)
                    if best < .06 ** 2:
                        config, target = load_problem(ROOT / 'input')
                        metrics = discrepancies(config, response(config, child), target)
                        print('FULL', metrics, flush=True)
                        if metrics['core_score'] >= .96 and metrics['worst_family_score'] >= .94:
                            (OUT / 'design.json').write_text(json.dumps({'pattern': child.tolist()}) + '\n')
                            (OUT / 'match.json').write_text(json.dumps(metrics) + '\n')
                            return
                if added >= 32:
                    break
        children.sort(key=lambda item: item[0])
        beams = []
        for cost, child in children:
            if not any(np.sum(child != other) < (2 if depth < 2 else 4) for other in beams):
                beams.append(child)
            if len(beams) >= arguments.width:
                break
        print('DEPTH', depth, 'beam', len(beams), 'best', np.sqrt(best), 'time', round(time.time() - started, 1), flush=True)


if __name__ == '__main__':
    main()
