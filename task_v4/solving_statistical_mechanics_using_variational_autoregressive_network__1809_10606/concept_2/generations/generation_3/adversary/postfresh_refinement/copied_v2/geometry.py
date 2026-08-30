import contextlib
import io
import itertools
import json
from pathlib import Path

import numpy as np

from general_dp import construct
from landscape import best_sector
from refine import refine
from search import optimize
from verify import EDGES, PRODUCTS, evaluate, frustrated


ROOT = Path(__file__).resolve().parent


def main():
    free = None
    for selected in itertools.combinations(range(16), 4):
        if any(first in selected and second in selected for first, second in EDGES):
            continue
        core = [site for site in range(16) if site not in selected]
        degrees = [sum(first == site and second in core or second == site and first in core for first, second in EDGES) for site in core]
        if min(degrees) >= 2 and degrees.count(4) == 4:
            free = list(selected)
            break
    print('free geometry', free, flush=True)
    base = json.loads((ROOT / 'global_dp_49_2_minimax.json').read_text())
    incidence = [np.flatnonzero(np.any(EDGES == site, axis=1)) for site in free]
    candidates = []
    for index, choices in enumerate(itertools.product(range(1, 4), repeat=4)):
        bonds = np.ones(32, dtype=int)
        for indices, choice in zip(incidence, choices):
            bonds[indices[0]] = -1
            bonds[indices[choice]] = -1
        if not 4 <= frustrated(bonds) <= 12:
            continue
        energy = -PRODUCTS @ bonds
        if energy.min() != -16:
            continue
        template = json.loads(json.dumps(base))
        template['bonds'] = bonds.tolist()
        with contextlib.redirect_stdout(io.StringIO()):
            witness = construct(template, free, 0)
        witness, sector = best_sector(witness)
        metrics = evaluate(witness)['metrics']
        potential = min(.05 / metrics['reward_variance'], metrics['target_sector_mass'] / .35,
                        .001 / max(metrics['proposal_sector_mass'], 1e-20))
        candidates.append((potential, index, witness))
    candidates.sort(key=lambda item: item[0], reverse=True)
    print('screened', [(round(item[0], 6), item[1]) for item in candidates], flush=True)
    for potential, index, witness in candidates[:3]:
        print('initial', index, evaluate(witness)['metrics'], flush=True)
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=250, verbosity=0)
        witness, sector = best_sector(witness)
        witness, result = optimize(witness, objective='minimax', constraints=False,
                                   iterations=350, verbosity=0)
        witness, sector = best_sector(witness)
        if evaluate(witness)['core_score'] > .8:
            witness, result = refine(witness, iterations=180, verbose=False)
            witness, sector = best_sector(witness)
        (ROOT / f'geometry_{index}.json').write_text(json.dumps(witness, indent=2) + '\n')
        print('final', index, evaluate(witness), flush=True)


if __name__ == '__main__':
    main()
