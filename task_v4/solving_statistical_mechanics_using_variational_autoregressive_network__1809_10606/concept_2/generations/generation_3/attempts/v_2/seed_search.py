import contextlib
import io
import json
from pathlib import Path

from general_dp import construct
from landscape import best_sector
from refine import refine
from search import optimize
from verify import evaluate


ROOT = Path(__file__).resolve().parent


def main():
    candidates = []
    for model in (49, 76):
        base = json.loads((ROOT / f'global_dp_{model}_2_minimax.json').read_text())
        for seed in range(4, 24):
            with contextlib.redirect_stdout(io.StringIO()):
                witness = construct(base, [4, 6, 13, 15], seed)
            witness, sector = best_sector(witness)
            report = evaluate(witness)
            metrics = report['metrics']
            potential = min(.05 / metrics['reward_variance'], metrics['target_sector_mass'] / .35,
                            .001 / max(metrics['proposal_sector_mass'], 1e-20))
            candidates.append((potential, model, seed, witness))
        print('screened model', model, flush=True)
    candidates.sort(key=lambda item: item[0], reverse=True)
    print('ranking', [(round(item[0], 7), item[1], item[2]) for item in candidates], flush=True)
    seen = set()
    chosen = 0
    for potential, model, seed, witness in candidates:
        key = json.dumps([witness['order'], witness['weights']])
        if key in seen:
            continue
        seen.add(key)
        print('start', model, seed, potential, flush=True)
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=250, verbosity=0)
        witness, sector = best_sector(witness)
        witness, result = optimize(witness, objective='minimax', constraints=False,
                                   iterations=350, verbosity=0)
        witness, sector = best_sector(witness)
        witness, result = refine(witness, iterations=160, verbose=False)
        witness, sector = best_sector(witness)
        filename = ROOT / f'seed_{model}_{seed}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('final', model, seed, evaluate(witness), flush=True)
        chosen += 1
        if chosen >= 5:
            break


if __name__ == '__main__':
    main()
