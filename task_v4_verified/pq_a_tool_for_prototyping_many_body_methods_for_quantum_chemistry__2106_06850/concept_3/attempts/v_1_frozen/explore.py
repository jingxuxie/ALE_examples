import sys
import math
import numpy as np

sys.path.insert(0, '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/pq_a_tool_for_prototyping_many_body_methods_for_quantum_chemistry__2106_06850/concept_3/participant/workspace')
from fermion import *


def choices(state, pairs_list, tolerance=1e-10):
    result = []
    for label_index, pairs in enumerate(pairs_list):
        sources, destinations, signs = pairs
        source_values = state[sources]
        destination_values = signs * state[destinations]
        active = np.hypot(source_values, destination_values) > tolerance
        if not np.any(active):
            continue
        angles = (np.arctan2(-destination_values[active], source_values[active]) + math.pi / 4) % (math.pi / 2) - math.pi / 4
        unique_angles = np.unique(np.round(angles, 10))
        for angle in unique_angles:
            if abs(angle) < tolerance:
                continue
            angle = angles[np.argmin(np.abs(angles-angle))]
            for shift in [0, math.pi / 2]:
                theta = angle + shift
                candidate = apply_rotation(state, pairs, theta)
                support = np.count_nonzero(np.abs(candidate) > tolerance)
                entropy = -np.sum(candidate**2 * np.log(candidate**2+1e-100))
                result.append((support, entropy, label_index, theta, candidate))
    return sorted(result, key=lambda choice: choice[:2])


if __name__ == '__main__':
    for case in load_cases():
        labels = allowed_excitations(case.n_orbitals)
        pairs_list = [rotation_pairs(case.n_orbitals,case.n_electrons,label) for label in labels]
        state = case.target.copy()
        print('\nCASE',case.case_id, flush=True)
        for depth in range(case.max_gates):
            options = choices(state,pairs_list)
            print('DEPTH',depth,'SUPPORT',np.count_nonzero(np.abs(state)>1e-10),'TOP',[(entry[0],round(entry[1],4),labels[entry[2]],round(entry[3],6)) for entry in options[:4]],flush=True)
            if not options:
                break
            state = options[0][4]
        print('END',np.max(state**2),case.determinants[np.argmax(state**2)],flush=True)
