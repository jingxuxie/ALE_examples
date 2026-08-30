import os
import sys
import json
import math
import numpy as np

sys.path.insert(0, os.environ['P'] + '/workspace')
from fermion import load_cases, allowed_excitations, rotation_pairs, apply_rotation


def candidates(state, pairs_list, minimum=1):
    support = np.count_nonzero(abs(state) > 1e-10)
    choices = []
    for label, pairs in enumerate(pairs_list):
        sources, destinations, signs = pairs
        active = np.hypot(state[sources], state[destinations]) > 1e-10
        angles = np.arctan2(signs[active] * state[destinations[active]], state[sources[active]])
        angles = (angles + math.pi / 4) % (math.pi / 2) - math.pi / 4
        angles = np.unique(np.round(angles, 12))
        for angle in angles:
            if abs(angle) < 1e-9:
                continue
            trial = apply_rotation(state, pairs, -float(angle))
            remaining = np.count_nonzero(abs(trial) > 1e-10)
            if support - remaining >= minimum:
                choices.append((remaining, np.sum(abs(trial)), label, float(angle), trial))
    choices.sort(key=lambda entry: entry[:2])
    return choices


def main():
    for case in load_cases():
        print('\nCASE', case.case_id, flush=True)
        gates = allowed_excitations(case.n_orbitals)
        pairs_list = [rotation_pairs(case.n_orbitals, case.n_electrons, gate) for gate in gates]
        state = case.target.copy()
        path = []
        for depth in range(case.max_gates):
            options = candidates(state, pairs_list)
            print('depth', depth, 'support', np.count_nonzero(abs(state) > 1e-10), 'choices', [(entry[0], round(entry[1], 3), gates[entry[2]], round(entry[3], 8)) for entry in options[:4]], flush=True)
            if not options:
                break
            remaining, norm, label, angle, state = options[0]
            path.append((label, angle))
        print('end', [(case.determinants[index], value) for index, value in enumerate(state) if abs(value) > 1e-9], flush=True)
        with open(case.case_id + '_peel.json', 'w') as handle:
            json.dump({'path': path, 'state': state.tolist()}, handle)


if __name__ == '__main__':
    main()
