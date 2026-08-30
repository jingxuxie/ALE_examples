import argparse
import contextlib
import io
import json
from pathlib import Path

import numpy as np
from scipy.special import expit

from landscape import KERNELS, best_sector, fwht
from search import optimize
from subset_tree import CORE, FREE, dynamic_tree, prepare
from verify import BOUND, STATES, evaluate


ROOT = Path(__file__).resolve().parent


def initial_candidates(base, count):
    costs, free_couplings = prepare(base)
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
    base_penalties = error_probabilities * ((effective - edge_logits) ** 2 + conditional_variance)
    report, target, proposal, energy, gradients = evaluate(base, True)
    target_mass = fwht(fwht(target) * KERNELS[4]) / 65536
    proposal_mass = fwht(fwht(proposal) * KERNELS[4]) / 65536
    feasible = np.flatnonzero((target_mass[:32768] >= .35) & (proposal_mass[:32768] <= .001))
    feasible = feasible[np.argsort(proposal_mass[feasible])]
    rng = np.random.default_rng(381)
    if len(feasible) > count:
        selected = [int(feasible[0])]
        selected.extend(int(value) for value in rng.choice(feasible[1:min(len(feasible), 400)], count - 1, replace=False))
    else:
        selected = feasible.tolist()
    all_states = np.repeat(core_states[:, None, :], 16, axis=1)
    free_states = 2 * ((np.arange(16)[:, None] >> np.arange(4)) & 1) - 1
    all_states[:, :, FREE] = free_states[None, :, :]
    free_probabilities = np.exp(-np.logaddexp(0, -free_states[None, :, :] * logits[:, None, :]).sum(axis=2))
    candidates_list = []
    for index, center in enumerate(selected):
        pattern = STATES[center].astype(int).tolist()
        distance = np.count_nonzero(all_states != pattern, axis=2)
        sector_conditional = (free_probabilities * (np.minimum(distance, 16 - distance) <= 4)).sum(axis=1)
        for strength in (10., 60.):
            penalties = base_penalties + strength * error_probabilities * sector_conditional
            with contextlib.redirect_stdout(io.StringIO()):
                witness = dynamic_tree(base, effective, free_couplings, index, penalties)
            witness['pattern'] = pattern
            witness['radius'] = 4
            report = evaluate(witness)
            rank = max(report['metrics']['reward_variance'] / .05, report['metrics']['proposal_sector_mass'] / .001)
            candidates_list.append((rank, index, strength, witness))
    candidates_list.sort(key=lambda item: item[:3])
    print('screened', [(round(item[0], 6), item[1], item[2]) for item in candidates_list], flush=True)
    return candidates_list


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'beta1_free_sector.json')
    parser.add_argument('--patterns', type=int, default=14)
    parser.add_argument('--count', type=int, default=12)
    parser.add_argument('--iterations', type=int, default=240)
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    candidates_list = initial_candidates(base, arguments.patterns)
    seen = set()
    chosen = 0
    for rank, index, strength, witness in candidates_list:
        key = json.dumps([witness['order'], witness['weights']])
        if key in seen:
            continue
        seen.add(key)
        filename = ROOT / f'sector_dp_{index}_{int(strength)}_initial.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('initial', index, strength, evaluate(witness)['metrics'], flush=True)
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=arguments.iterations, verbosity=0)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'sector_dp_{index}_{int(strength)}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('variance', index, strength, report['core_score'], report['metrics'], flush=True)
        witness, result = optimize(witness, objective='minimax', constraints=False,
                                   iterations=300, verbosity=0)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'sector_dp_{index}_{int(strength)}_minimax.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('minimax', index, strength, report['core_score'], report['metrics'], flush=True)
        chosen += 1
        if chosen >= arguments.count:
            break


if __name__ == '__main__':
    main()
