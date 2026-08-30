import itertools
import json
from pathlib import Path

import numpy as np

FAMILIES = ('local', 'collective', 'frustrated', 'bridge', 'density', 'mixed')


ORDERS = np.array([mask.bit_count() for mask in range(256)])
MASKS = [np.flatnonzero(ORDERS == order) for order in range(9)]
SUBSETS = (np.arange(256)[None, :] & np.arange(256)[:, None]) == np.arange(256)[None, :]


def transform(energy):
    terms = np.array(energy, copy=True)
    for orbital in range(8):
        selected = np.flatnonzero(np.arange(256) & (1 << orbital))
        terms[..., selected] -= terms[..., selected ^ (1 << orbital)]
    return terms


def report(errors, families, name):
    print(name, 'overall', round(np.sqrt(np.mean(errors ** 2)) * 1e6, 3),
          {family: round(np.sqrt(np.mean(errors[families == index] ** 2)) * 1e6, 3)
           for index, family in enumerate(FAMILIES)}, flush=True)


def practice():
    root = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/participant/input')
    models = json.loads((root / 'practice_models.json').read_text())
    return np.load(root / 'practice.npz')['energies'], np.array([model['orbital_energy'] for model in models]), np.array([FAMILIES.index(model['family']) for model in models])


def main():
    data = np.load('train.npz')
    energy, families = data['energies'][-1800:], data['families'][-1800:]
    terms = transform(energy)
    for order in range(3, 7):
        report(terms[:, ORDERS > order].sum(1), families, 'MBE' + str(order))
    for variant in range(4):
        errors = []
        for row, table in zip(terms, energy):
            strengths = np.sum(np.abs(row[MASKS[3]])[None, :] * SUBSETS[MASKS[3]][:, MASKS[1]].T, axis=1)
            if variant % 2:
                strengths = -row[MASKS[1]]
            ordering = np.argsort(-strengths)
            core = sum(1 << int(orbital) for orbital in ordering[:4])
            weak = ordering[4:]
            best = None
            for permutation in [(0, 1, 2, 3), (0, 2, 1, 3), (0, 3, 1, 2)]:
                first = core | (1 << int(weak[permutation[0]])) | (1 << int(weak[permutation[1]]))
                second = core | (1 << int(weak[permutation[2]])) | (1 << int(weak[permutation[3]]))
                missing = ~(SUBSETS[first] | SUBSETS[second])
                score = np.sum(np.abs(row[(ORDERS == 2) & missing]))
                if best is None or score < best[0]:
                    best = score, first, second, missing
            _, first, second, missing = best
            if variant < 2:
                remainder = row[(ORDERS >= 4) & missing].sum()
            else:
                missing_four = MASKS[4][missing[MASKS[4]]]
                weights = np.sum(SUBSETS[missing_four][:, MASKS[3]] * np.abs(row[MASKS[3]])[None, :], axis=1)
                selected = missing_four[np.argsort(-weights)[:2]]
                remainder = row[(ORDERS >= 4) & missing].sum() - row[selected].sum()
            errors.append(remainder)
        report(np.array(errors), families, 'two six variant ' + str(variant))


if __name__ == '__main__':
    main()
