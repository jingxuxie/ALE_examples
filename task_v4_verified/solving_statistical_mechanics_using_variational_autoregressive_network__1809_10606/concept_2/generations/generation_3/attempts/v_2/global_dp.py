import argparse
import contextlib
import io
import json
from pathlib import Path

import numpy as np
from scipy.special import expit

from bond_search import candidates
from landscape import best_sector
from search import optimize
from subset_tree import CORE, FREE, dynamic_tree, prepare
from verify import BOUND, evaluate


ROOT = Path(__file__).resolve().parent


def screen(base):
    all_candidates = []
    for unused_merit, model_index, signature, template in candidates(base):
        costs, free_couplings = prepare(template)
        core_states = np.ones((4096, 16))
        core_states[:, CORE] = 1 - 2 * ((np.arange(4096)[:, None] >> np.arange(12)) & 1)
        fields = core_states @ free_couplings.T
        logits = fields * BOUND / 4
        aligned = np.tanh(logits / 2)
        relative_kl = ((logits / 2 - fields) * aligned - np.log(np.cosh(logits / 2)) + np.log(np.cosh(fields))).sum(axis=1)
        conditional_variance = (((logits / 2 - fields) ** 2) * (1 - aligned ** 2)).sum(axis=1)
        effective = costs + relative_kl
        edge_logits = np.where((effective > 3.5) & (effective < BOUND), effective, BOUND - 1e-10)
        error_probabilities = expit(-edge_logits)
        penalties = error_probabilities * ((effective - edge_logits) ** 2 + conditional_variance)
        for seed in range(4):
            with contextlib.redirect_stdout(io.StringIO()):
                witness = dynamic_tree(template, effective, free_couplings, seed, penalties)
            witness, sector = best_sector(witness)
            report = evaluate(witness)
            metrics = report['metrics']
            potential = min(.05 / metrics['reward_variance'], metrics['target_sector_mass'] / .35,
                            .001 / max(metrics['proposal_sector_mass'], 1e-20))
            all_candidates.append((potential, model_index, seed, witness, metrics))
    all_candidates.sort(key=lambda item: item[0], reverse=True)
    print('screened', [(round(item[0], 6), item[1], item[2], round(item[4]['reward_variance'], 7), round(item[4]['target_sector_mass'], 6)) for item in all_candidates[:30]], flush=True)
    return all_candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'beta1_free_sector.json')
    parser.add_argument('--count', type=int, default=12)
    parser.add_argument('--iterations', type=int, default=240)
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    all_candidates = screen(base)
    seen = set()
    chosen = 0
    for potential, model_index, seed, witness, initial_metrics in all_candidates:
        signature = (round(initial_metrics['reward_variance'], 5), round(initial_metrics['target_sector_mass'], 5), round(initial_metrics['proposal_sector_mass'], 7))
        if signature in seen:
            continue
        seen.add(signature)
        filename = ROOT / f'global_dp_{model_index}_{seed}_initial.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('initial', model_index, seed, potential, initial_metrics, flush=True)
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=arguments.iterations, verbosity=0)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'global_dp_{model_index}_{seed}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('variance', model_index, seed, report['core_score'], report['metrics'], flush=True)
        witness, result = optimize(witness, objective='minimax', constraints=False,
                                   iterations=400, verbosity=0)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'global_dp_{model_index}_{seed}_minimax.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('minimax', model_index, seed, report['core_score'], report['metrics'], flush=True)
        chosen += 1
        if chosen >= arguments.count:
            break


if __name__ == '__main__':
    main()
