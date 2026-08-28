"""Independent invariance, synthetic recovery, and scale checks."""

import sys
import time
import itertools
import numpy as np
from scipy import linalg
import solve


def expanded(tensor, data, suffix):
    row_map = data['s2p' + suffix]
    mapping = data['compact_map' + suffix]
    if tensor.ndim == 4:
        return tensor[row_map[:, None], mapping]
    return tensor[row_map[:, None, None], mapping[:, :, None], mapping[:, None, :]]


def predict(fc2, fc3, displacements, data):
    harmonic = expanded(fc2, data, '3')
    forces = -np.einsum('ijab,sjb->sia', harmonic, displacements, optimize=True)
    for atom in range(displacements.shape[1]):
        frame = displacements[:, np.argsort(data['compact_map3'][atom]), :]
        forces[:, atom] -= 0.5 * np.einsum(
            'jkabd,sjb,skd->sa', fc3[data['s2p3'][atom]], frame, frame,
            optimize=True
        )
    return forces


def invariances(tensor, data, suffix):
    order = tensor.ndim // 2
    full = expanded(tensor, data, suffix)
    errors = {'asr': np.max(np.abs(tensor.sum(axis=order - 1)), initial=0.0)}
    if order == 2:
        errors['permutation'] = np.max(np.abs(full - full.transpose(1, 0, 3, 2)))
    else:
        errors['permutation'] = max(
            np.max(np.abs(full - full.transpose(1, 0, 2, 4, 3, 5))),
            np.max(np.abs(full - full.transpose(0, 2, 1, 3, 5, 4)))
        )
        errors['support'] = np.max(np.abs(tensor[~data['triplet_mask3']]), initial=0.0)
    maximum = 0.0
    for rotation, permutation in zip(data['cart_rotations' + suffix], data['permutations' + suffix]):
        if order == 2:
            transformed = np.einsum('ad,be,ijde->ijab', rotation, rotation, full, optimize=True)
            actual = full[permutation[:, None], permutation]
        else:
            transformed = np.einsum('ad,be,cf,ijkdef->ijkabc', rotation, rotation, rotation, full, optimize=True)
            actual = full[permutation[:, None, None], permutation[None, :, None], permutation[None, None, :]]
        maximum = max(maximum, np.max(np.abs(actual - transformed)))
    errors['crystal'] = maximum
    return errors


def cell_data(positions, cell, labels, representatives, rotations, translations, cart_rotations):
    atom_count = len(positions)
    coordinate_lookup = {tuple(np.round(position % 1, 9)): index for index, position in enumerate(positions)}
    def match(coordinates):
        rounded = np.round(coordinates % 1, 9) % 1
        return np.array([coordinate_lookup[tuple(position)] for position in rounded])
    mapping = np.empty((atom_count, atom_count), dtype=int)
    for atom in range(atom_count):
        shift = positions[representatives[labels[atom]]] - positions[atom]
        mapping[atom] = match(positions + shift)
    permutations = np.array([match(positions @ rotation.T + translation)
                             for rotation, translation in zip(rotations, translations)])
    return dict(positions=positions, cell=cell, numbers=np.full(atom_count, 14, dtype=np.int64),
                p2s=np.asarray(representatives), s2p=labels, compact_map=mapping,
                rotations=rotations, translations=translations,
                cart_rotations=cart_rotations, permutations=permutations)


def diamond(base, repeats, shuffle=False, rotation=None):
    shifts = np.array(list(itertools.product(range(repeats), repeat=3)))
    positions = ((shifts[:, None, :] + base['positions3']) / repeats).reshape(-1, 3)
    labels = np.tile(base['s2p3'], len(shifts))
    representatives = base['p2s3'].copy()
    cell = base['cell3'] * repeats
    rotations = base['rotations3']
    translations = base['translations3'] / repeats
    cart_rotations = base['cart_rotations3'].copy()
    if rotation is not None:
        cell = cell @ rotation.T
        cart_rotations = rotation @ cart_rotations @ rotation.T
    if shuffle:
        permutation = np.random.default_rng(884).permutation(len(positions))
        inverse = np.argsort(permutation)
        positions = positions[permutation]
        labels = labels[permutation]
        representatives = inverse[representatives]
    return cell_data(positions, cell, labels, representatives, rotations, translations, cart_rotations)


def combine(large, small, cutoff=4.0):
    data = {'schema_version': np.array(1), 'fit_mode': np.array(1), 'cutoff3': np.array(cutoff)}
    data.update({key + '2': value for key, value in large.items()})
    data.update({key + '3': value for key, value in small.items()})
    difference = small['positions'][:, None, :] - small['positions'][None, :, :]
    best = np.full(difference.shape[:2], np.inf)
    for shift in itertools.product((-1, 0, 1), repeat=3):
        distance = np.linalg.norm((difference + shift) @ small['cell'], axis=-1)
        best = np.minimum(best, distance)
    adjacency = best <= cutoff + 1e-8
    data['triplet_mask3'] = np.array([adjacency[atom, :, None] & adjacency[atom, None, :] & adjacency
                                    for atom in small['p2s']])
    fold = []
    for representative in range(len(large['p2s'])):
        coordinates = ((large['positions'] - large['positions'][large['p2s'][representative]]) @
                       large['cell'] @ np.linalg.inv(small['cell']) +
                       small['positions'][small['p2s'][representative]])
        delta = coordinates[:, None, :] - small['positions'][None, :, :]
        delta -= np.rint(delta)
        fold.append(np.argmin(np.linalg.norm(delta, axis=-1), axis=1))
    data['fold2to3'] = np.array(fold)
    return data


def independent_basis(data, order):
    atom_count = len(data['numbers3'])
    row_count = len(data['p2s3'])
    shape = (row_count,) + (atom_count,) * (order - 1) + (3,) * order
    indices = np.arange(np.prod(shape)).reshape(shape)
    full = expanded(indices, data, '3')
    swapped = [full.transpose(1, 0, 3, 2)] if order == 2 else [
        full.transpose(1, 0, 2, 4, 3, 5), full.transpose(0, 2, 1, 3, 5, 4)]
    rows = []
    for permutation in swapped:
        distinct = full != permutation
        original = full[distinct]
        target = permutation[distinct]
        constraint = np.zeros((len(original), indices.size))
        constraint[np.arange(len(original)), original] = 1
        constraint[np.arange(len(original)), target] -= 1
        rows.append(constraint)
    sums = np.moveaxis(indices, order - 1, -1).reshape(-1, atom_count)
    constraint = np.zeros((len(sums), indices.size))
    constraint[np.arange(len(sums))[:, None], sums] = 1
    rows.append(constraint)
    return linalg.null_space(np.concatenate(rows), rcond=1e-11)


def small_independent():
    positions = np.array([[0.0, 0.0, 0.0], [1 / 3, 0.0, 0.0], [2 / 3, 0.0, 0.0]])
    cell = cell_data(positions, np.diag([6.0, 5.0, 4.0]), np.zeros(3, dtype=int), [0],
                     np.eye(3, dtype=int)[None], np.zeros((1, 3)), np.eye(3)[None])
    data = combine(cell, cell, 10.0)
    data['fit_mode'] = np.array(0)
    bases = [solve.TensorBasis(data, 3, order) for order in (2, 3)]
    independent = [independent_basis(data, order) for order in (2, 3)]
    for basis, reference in zip(bases, independent):
        actual = basis.basis @ basis.nullspace
        assert actual.shape == reference.shape, (actual.shape, reference.shape)
        assert np.linalg.norm(actual @ actual.T - reference @ reference.T) < 1e-9
        print('independent subspace', basis.order, actual.shape)
    rng = np.random.default_rng(391)
    data['u3'] = rng.normal(scale=0.06, size=(1, 3, 3))
    data['f3'] = rng.normal(size=(1, 3, 3))
    designs = []
    for order, reference in zip((2, 3), independent):
        shape = bases[order - 2].atom_shape + (3,) * order
        columns = []
        for column in reference.T:
            tensor = column.reshape(shape)
            if order == 2:
                force = solve.harmonic_forces(tensor, data['u3'], data['s2p3'], data['compact_map3'])
            else:
                force = predict(np.zeros(bases[0].atom_shape + (3, 3)), tensor, data['u3'], data)
            columns.append(force.ravel())
        designs.append(np.array(columns).T)
    joint = np.concatenate(designs, axis=1)
    coefficients = linalg.lstsq(joint, data['f3'].ravel(), cond=1e-11)[0]
    actual = solve.solve(data)
    split = independent[0].shape[1]
    for order, expected in [(2, independent[0] @ coefficients[:split]),
                            (3, independent[1] @ coefficients[split:])]:
        error = np.linalg.norm(actual['fc' + str(order)].ravel() - expected)
        assert error < 1e-8, error
    print('independent rank-deficient minimum-norm fit passed')


def recover(base, large_repeat, small_repeat, snapshots, rotate=False):
    rng = np.random.default_rng(71)
    rotation = linalg.qr(rng.normal(size=(3, 3)))[0] if rotate else None
    large = diamond(base, large_repeat, True, rotation)
    small = diamond(base, small_repeat, True, rotation)
    data = combine(large, small)
    data['fit_mode'] = np.array(int(large_repeat != small_repeat))
    harmonic_basis = solve.TensorBasis(data, 2, 2)
    cubic_basis = solve.TensorBasis(data, 3, 3)
    fc2 = harmonic_basis.tensor(rng.normal(size=harmonic_basis.parameter_count))
    fc3 = cubic_basis.tensor(rng.normal(size=cubic_basis.parameter_count))
    print('invariance harmonic', invariances(fc2, data, '2'))
    if len(small['numbers']) <= 64:
        errors = invariances(fc3, data, '3')
        print('invariance cubic', errors)
        assert max(errors.values()) < 1e-10
    data['u2'] = rng.normal(scale=0.04, size=(snapshots, len(large['numbers']), 3))
    data['u3'] = rng.normal(scale=0.08, size=(snapshots, len(small['numbers']), 3))
    data['f2'] = solve.harmonic_forces(fc2, data['u2'], data['s2p2'], data['compact_map2'])
    folded = solve.fold_harmonic(fc2, data['fold2to3'], len(small['numbers']))
    data['f3'] = predict(folded, fc3, data['u3'], data)
    if int(data['fit_mode']) == 0:
        data['u2'] = data['u2'][:0]
        data['f2'] = data['f2'][:0]
    started = time.monotonic()
    result = solve.solve(data)
    elapsed = time.monotonic() - started
    error2 = np.linalg.norm(result['fc2'] - fc2) / np.linalg.norm(fc2)
    error3 = np.linalg.norm(result['fc3'] - fc3) / np.linalg.norm(fc3)
    print('recovery', large_repeat, small_repeat, snapshots, rotate, error2, error3, 'seconds', elapsed, flush=True)
    assert error2 < 1e-8 and error3 < 1e-8
    return data


def main():
    base = dict(np.load(sys.argv[1], allow_pickle=False))
    small_independent()
    result = solve.solve(base)
    for order in (2, 3):
        errors = invariances(result['fc' + str(order)], base, str(order))
        print('smoke invariances', order, errors)
        assert max(errors.values()) < 1e-9
    predicted = predict(result['fc2'], result['fc3'], base['u3'], base)
    print('smoke training RMSE', np.mean((predicted - base['f3']) ** 2) ** 0.5)
    recover(base, 1, 1, 20, True)
    recover(base, 3, 1, 12, True)
    recover(base, 4, 2, 20, False)
    print('all checks passed')


if __name__ == '__main__':
    main()
