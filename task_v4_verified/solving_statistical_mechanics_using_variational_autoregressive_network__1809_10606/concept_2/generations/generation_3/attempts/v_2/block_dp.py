import json
from pathlib import Path

import numpy as np
from scipy.special import expit

from construct import fit_distribution
from landscape import best_sector
from refine import refine
from search import optimize
from verify import BOUND, PRODUCTS, STATES, evaluate


ROOT = Path(__file__).resolve().parent


def construct(base, center, seed):
    free = [center, 4, 6, 13, 15]
    core = [site for site in range(16) if site not in free]
    core_count = len(core)
    count = 1 << core_count
    codes = ((STATES[:, core] < 0).astype(np.int64) * (1 << np.arange(core_count))).sum(axis=1)
    energy = -PRODUCTS @ base['bonds']
    boltzmann = np.exp(-energy)
    partition = np.bincount(codes, weights=boltzmann, minlength=count)
    costs = -np.log(partition) + np.log(partition[0])
    edge_logits = np.where((costs > 3.5) & (costs < BOUND), costs, BOUND - 1e-10)
    penalties = expit(-edge_logits) * (costs - edge_logits) ** 2
    rng = np.random.default_rng(seed)
    penalties *= np.exp(rng.normal(0, .3, count))
    penalties += rng.uniform(0, 1e-9, count)
    forests = np.full(count, np.inf)
    trees = np.full(count, np.inf)
    forest_choices = np.zeros(count, dtype=int)
    roots = np.zeros(count, dtype=int)
    forests[0] = 0
    for mask in sorted(range(1, count), key=int.bit_count):
        members = [index for index in range(core_count) if mask & (1 << index)]
        root = min(members, key=lambda index: forests[mask ^ (1 << index)])
        trees[mask] = penalties[mask] + forests[mask ^ (1 << root)]
        roots[mask] = root
        first_bit = mask & -mask
        subset = mask
        best_value, best_subset = np.inf, 0
        while subset:
            if subset & first_bit:
                value = trees[subset] + forests[mask ^ subset]
                if value < best_value:
                    best_value, best_subset = value, subset
            subset = (subset - 1) & mask
        forests[mask] = best_value
        forest_choices[mask] = best_subset
    full = count - 1
    root = int(roots[full])
    parents = {root: None}
    subtrees = {}

    def walk(mask, parent):
        while mask:
            subtree = int(forest_choices[mask])
            child = int(roots[subtree])
            parents[child] = parent
            subtrees[child] = subtree
            walk(subtree ^ (1 << child), child)
            mask ^= subtree

    walk(full ^ (1 << root), root)
    order_indices = [root]
    for parent in order_indices:
        order_indices.extend(child for child in parents if parents[child] == parent)
    order = [core[index] for index in order_indices] + free
    log_core = np.full(65536, -np.log(2.))
    for child, parent in parents.items():
        if parent is not None:
            aligned = STATES[:, core[child]] * STATES[:, core[parent]]
            log_core -= np.logaddexp(0, -aligned * edge_logits[subtrees[child]])
    teacher = np.exp(log_core) * boltzmann / partition[codes]
    assert abs(teacher.sum() - 1) < 1e-10
    witness = json.loads(json.dumps(base))
    witness['order'] = order
    witness['weights'] = fit_distribution(teacher, order).tolist()
    print('DP', center, seed, 'proxy', forests[full ^ (1 << root)], 'order', order, flush=True)
    return witness


def main():
    base = json.loads((ROOT / 'global_dp_49_2_minimax.json').read_text())
    for center, seed in [(7, 0), (5, 0), (12, 1), (14, 1)]:
        witness = construct(base, center, seed)
        witness, sector = best_sector(witness)
        print('initial', center, seed, evaluate(witness)['metrics'], flush=True)
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=250, verbosity=0)
        witness, sector = best_sector(witness)
        witness, result = optimize(witness, objective='minimax', constraints=False,
                                   iterations=350, verbosity=0)
        witness, sector = best_sector(witness)
        if evaluate(witness)['core_score'] > .8:
            witness, result = refine(witness, iterations=180, verbose=False)
            witness, sector = best_sector(witness)
        filename = ROOT / f'block_{center}_{seed}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('final', center, seed, evaluate(witness), flush=True)


if __name__ == '__main__':
    main()
