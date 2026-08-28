"""Additional low-symmetry, hexagonal, and noisy least-squares checks."""

import itertools
import sys
import time
import numpy as np
from scipy import linalg
import solve
import validate


def hexagonal(repeats):
    primitive_cell = np.array([[3.2, 0, 0], [-1.6, 3.2 * np.sqrt(3) / 2, 0], [0, 0, 5.2]])
    primitive_positions = np.array([[1 / 3, 2 / 3, 1 / 4], [2 / 3, 1 / 3, 3 / 4]])
    turn = np.array([[1, -1, 0], [1, 0, 0], [0, 0, 1]])
    mirror = np.array([[1, -1, 0], [0, -1, 0], [0, 0, 1]])
    rotations = []
    translations = []
    for power, reflect, flip in itertools.product(range(6), range(2), range(2)):
        rotation = np.linalg.matrix_power(turn, power) @ np.linalg.matrix_power(mirror, reflect) @ np.diag([1, 1, (-1) ** flip])
        for target in primitive_positions:
            translation = (target - primitive_positions[0] @ rotation.T) % 1
            images = (primitive_positions @ rotation.T + translation) % 1
            delta = images[:, None] - primitive_positions[None]
            delta -= np.rint(delta)
            if np.all(np.min(np.linalg.norm(delta, axis=-1), axis=1) < 1e-8):
                rotations.append(rotation)
                translations.append(translation)
                break
    assert len(rotations) == 24
    rotations = np.array(rotations)
    translations = np.array(translations)
    cart_rotations = primitive_cell.T @ rotations @ np.linalg.inv(primitive_cell.T)
    shifts = np.array(list(itertools.product(*[range(repeat) for repeat in repeats])))
    positions = ((shifts[:, None] + primitive_positions) / repeats).reshape(-1, 3)
    labels = np.tile([0, 1], len(shifts))
    permutation = np.random.default_rng(432).permutation(len(positions))
    inverse = np.argsort(permutation)
    positions = positions[permutation]
    labels = labels[permutation]
    cell = np.diag(repeats) @ primitive_cell
    rotations = np.rint(np.diag(1 / np.array(repeats)) @ rotations @ np.diag(repeats)).astype(int)
    return validate.cell_data(positions, cell, labels, inverse[:2], rotations,
                              translations / repeats, cart_rotations)


def recovery(data, snapshots=40, noisy=False):
    rng = np.random.default_rng(812)
    harmonic_basis = solve.TensorBasis(data, 2, 2)
    cubic_basis = solve.TensorBasis(data, 3, 3)
    harmonic_coefficients = rng.normal(size=harmonic_basis.parameter_count)
    cubic_coefficients = rng.normal(size=cubic_basis.parameter_count)
    fc2 = harmonic_basis.tensor(harmonic_coefficients)
    fc3 = cubic_basis.tensor(cubic_coefficients)
    for tensor, suffix in [(fc2, '2'), (fc3, '3')]:
        errors = validate.invariances(tensor, data, suffix)
        print('invariances', suffix, errors, flush=True)
        assert max(errors.values()) < 1e-10
    data['u2'] = rng.normal(scale=0.03, size=(snapshots, len(data['numbers2']), 3))
    data['u3'] = rng.normal(scale=0.05, size=(snapshots, len(data['numbers3']), 3))
    data['f2'] = solve.harmonic_forces(fc2, data['u2'], data['s2p2'], data['compact_map2'])
    folded = solve.fold_harmonic(fc2, data['fold2to3'], len(data['numbers3']))
    data['f3'] = validate.predict(folded, fc3, data['u3'], data)
    if noisy:
        data['f2'] += rng.normal(scale=0.002, size=data['f2'].shape)
        data['f3'] += rng.normal(scale=0.002, size=data['f3'].shape)
    started = time.monotonic()
    result = solve.solve(data)
    print('fit time', time.monotonic() - started, flush=True)
    if not noisy:
        errors = [np.linalg.norm(result['fc2'] - fc2) / np.linalg.norm(fc2),
                  np.linalg.norm(result['fc3'] - fc3) / np.linalg.norm(fc3)]
        print('relative recovery errors', errors, flush=True)
        assert max(errors) < 1e-8
    else:
        cubic_design = cubic_basis.design(data['u3'])
        if int(data['fit_mode']) == 0:
            harmonic_design = harmonic_basis.design(data['u3'])
            design = np.concatenate([harmonic_design, cubic_design], axis=1)
            reference = linalg.lstsq(design, data['f3'].ravel(), cond=1e-11)[0]
            expected2 = harmonic_basis.tensor(reference[:harmonic_basis.parameter_count])
            expected3 = cubic_basis.tensor(reference[harmonic_basis.parameter_count:])
        else:
            harmonic_design = harmonic_basis.design(data['u2'])
            reference2 = linalg.lstsq(harmonic_design, data['f2'].ravel(), cond=1e-11)[0]
            expected2 = harmonic_basis.tensor(reference2)
            folded = solve.fold_harmonic(expected2, data['fold2to3'], len(data['numbers3']))
            residual = data['f3'] - solve.harmonic_forces(folded, data['u3'], data['s2p3'], data['compact_map3'])
            reference3 = linalg.lstsq(cubic_design, residual.ravel(), cond=1e-11)[0]
            expected3 = cubic_basis.tensor(reference3)
        errors = [np.linalg.norm(result['fc2'] - expected2), np.linalg.norm(result['fc3'] - expected3)]
        print('normal versus SVD errors', errors, flush=True)
        assert max(errors) < 1e-8
    return data


def low_symmetry():
    positions = np.array([[0, 0, 0], [1 / 3, 0, 0], [2 / 3, 0, 0],
                          [0.13, 0.27, 0.39], [0.13 + 1 / 3, 0.27, 0.39],
                          [0.13 + 2 / 3, 0.27, 0.39]])
    cell = validate.cell_data(positions, np.array([[6, 0, 0], [1, 5, 0], [-1, 1, 4]]),
                              np.array([0, 0, 0, 1, 1, 1]), [2, 4],
                              np.eye(3, dtype=int)[None], np.zeros((1, 3)), np.eye(3)[None])
    cell['numbers'] = np.array([14, 14, 14, 8, 8, 8])
    data = validate.combine(cell, cell, 10)
    data['fit_mode'] = np.array(0)
    recovery(data, 80)
    recovery(data, 80, noisy=True)


def main():
    low_symmetry()
    data = validate.combine(hexagonal((6, 6, 4)), hexagonal((3, 3, 2)), 3.3)
    data['fit_mode'] = np.array(1)
    recovery(data, 30)
    recovery(data, 30, noisy=True)
    np.savez_compressed(sys.argv[1], **data)
    print('additional checks passed')


if __name__ == '__main__':
    main()
