"""Independent real-space and Fourier checks of the repaired pipeline."""

import itertools
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from numpy.testing import assert_allclose

from historical_model import Model
from import_atom import AtomLoader
from import_xyz import CartesianLoader
from pipeline import solve


def integer_inverse(cell):
    inverse = np.column_stack((
        np.cross(cell[1], cell[2]),
        np.cross(cell[2], cell[0]),
        np.cross(cell[0], cell[1]),
    ))
    np.testing.assert_array_equal(cell @ inverse, np.eye(3, dtype=int))
    return inverse


def fourier(hoppings, kpoints, half=False):
    vectors = np.asarray(list(hoppings))
    matrices = np.asarray(list(hoppings.values()))
    phases = np.exp(2j * np.pi * np.asarray(kpoints) @ vectors.T)
    result = np.einsum('qr,rij->qij', phases, matrices)
    return result + result.conj().transpose(0, 2, 1) if half else result


def change_phase(matrices, kpoints, positions):
    phases = np.exp(2j * np.pi * np.asarray(kpoints) @ positions.T)
    return phases.conj()[:, :, None] * matrices * phases[:, None, :]


def direct_supercell(hoppings, positions, size, kpoints):
    """Enumerate every directed bond independently of the Model methods."""
    size = np.asarray(size)
    images = list(itertools.product(*(range(int(count)) for count in size)))
    image_indices = {image: index for index, image in enumerate(images)}
    orbital_count = len(positions)
    shifts = np.floor(positions).astype(int)
    reduced = positions - shifts
    new_positions = np.concatenate([(reduced + image) / size for image in images])
    matrices = np.zeros((len(kpoints), len(new_positions), len(new_positions)), complex)
    for image_index, image in enumerate(images):
        for vector, hopping in hoppings.items():
            for source, target in itertools.product(range(orbital_count), repeat=2):
                endpoint = np.asarray(image) + vector + shifts[target] - shifts[source]
                cell_vector, target_image = np.divmod(endpoint, size)
                target_index = image_indices[tuple(target_image)]
                phases = np.exp(2j * np.pi * np.asarray(kpoints) @ cell_vector)
                matrices[:, image_index * orbital_count + source,
                         target_index * orbital_count + target] += hopping[source, target] * phases
    return new_positions, matrices


def random_half_model(generator, orbital_count=6):
    cell = np.array([[2.1, 0.7, -0.2], [-0.4, 1.6, 0.5], [0.6, -0.3, 2.7]])
    positions = generator.uniform(-1.5, 2.5, (orbital_count, 3))
    vectors = [(0, 0, 0), (1, 0, 0), (-1, 0, 0), (2, -3, 1), (-2, 1, -1)]
    hopping = {
        vector: generator.normal(size=(orbital_count, orbital_count))
        + 1j * generator.normal(size=(orbital_count, orbital_count))
        for vector in vectors
    }
    return cell, positions, hopping


def make_import_fixture(directory, shuffled=True, bohr=False):
    generator = np.random.default_rng(438)
    orbital_count = 4
    cell = np.array([[2.1, 0.7, -0.2], [-0.4, 1.6, 0.5], [0.6, -0.3, 2.7]])
    positions = np.array([[1.2, -0.4, 0.37], [-0.35, 2.19, 1.03],
                          [0.62, 0.87, -1.2], [2.47, -1.8, 1.31]])
    centres = positions @ cell
    atoms = centres + generator.uniform(-0.15, 0.15, centres.shape)
    atoms = atoms[[2, 0, 3, 1]]
    zero = generator.normal(size=(orbital_count, orbital_count))
    zero = zero + 1j * generator.normal(size=zero.shape)
    hopping = {(0, 0, 0): zero + zero.conj().T}
    for vector in [(1, 0, 0), (0, -2, 1), (2, 1, -1)]:
        matrix = generator.normal(size=zero.shape) + 1j * generator.normal(size=zero.shape)
        matrix[1, 2] = 2e-14 + 3e-14j
        hopping[vector] = matrix
        hopping[tuple(-np.asarray(vector))] = matrix.conj().T
    corrections = {}
    for vector in hopping:
        for source, target in itertools.product(range(orbital_count), repeat=2):
            key = (*vector, source, target)
            if key in corrections:
                continue
            opposite = (*(-np.asarray(vector)), target, source)
            shifts = generator.integers(-2, 3, (int(generator.integers(1, 5)), 3))
            if key == opposite:
                shifts = np.concatenate((shifts, -shifts))
            corrections[key] = shifts
            corrections[opposite] = -shifts
    corrected = {}
    for vector, matrix in hopping.items():
        for source, target in itertools.product(range(orbital_count), repeat=2):
            shifts = corrections[(*vector, source, target)]
            for shift in shifts:
                new_vector = tuple(np.asarray(vector) + shift)
                corrected.setdefault(new_vector, np.zeros_like(matrix))[source, target] += (
                    matrix[source, target] / len(shifts)
                )
    vectors = list(hopping)
    generator.shuffle(vectors)
    degeneracies = generator.integers(1, 8, len(vectors))
    lines = ['Synthetic full Hermitian model', str(orbital_count), str(len(vectors)),
             ' '.join(str(value) for value in degeneracies)]
    for vector, degeneracy in zip(vectors, degeneracies):
        indices = [(source, target) for target in range(orbital_count)
                   for source in range(orbital_count)]
        if shuffled:
            generator.shuffle(indices)
        for source, target in indices:
            value = hopping[vector][source, target] * degeneracy
            fields = (*vector, source + 1, target + 1)
            lines.append(' '.join(map(str, fields)) + f' {value.real:.17g} {value.imag:.17g}')
    (directory / 'import_hr.dat').write_text('\n'.join(lines) + '\n')
    keys = list(corrections)
    generator.shuffle(keys)
    lines = ['# Independently shuffled wsvec records']
    for key in keys:
        fields = (*key[:3], key[3] + 1, key[4] + 1)
        lines.extend([' '.join(map(str, fields)), str(len(corrections[key]))])
        lines.extend(' '.join(map(str, vector)) for vector in corrections[key])
    (directory / 'import_wsvec.dat').write_text('\n'.join(lines) + '\n')
    file_cell = cell / 0.52917721092 if bohr else cell
    lines = ['begin unit_cell_cart', 'bohr' if bohr else 'ang']
    lines.extend(' '.join(f'{value:.17g}' for value in row) for row in file_cell)
    lines.append('end unit_cell_cart')
    (directory / 'import.win').write_text('\n'.join(lines) + '\n')
    lines = [str(len(centres) + len(atoms)), 'Unwrapped Cartesian centres and atoms']
    lines.extend('X ' + ' '.join(f'{value:.17g}' for value in row) for row in centres)
    lines.extend('Si ' + ' '.join(f'{value:.17g}' for value in row) for row in atoms)
    (directory / 'import_centres.xyz').write_text('\n'.join(lines) + '\n')
    return cell, positions, centres, atoms, hopping, corrected


class MappingTests(unittest.TestCase):
    def test_full_matrix_covariance(self):
        generator = np.random.default_rng(37)
        cell, positions, hopping = random_half_model(generator)
        model = Model(uc=cell, pos=positions, hop=hopping, contains_cc=False)
        transforms = [np.eye(3, dtype=int), np.diag([-1, -1, 1]),
                      np.array([[1, 2, -1], [0, 1, 3], [0, 0, 1]]),
                      np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]])]
        for trial in range(20):
            transform = np.eye(3, dtype=int)
            for operation in range(5):
                source, target = generator.choice(3, 2, replace=False)
                transform[target] += int(generator.integers(-2, 3)) * transform[source]
            transforms.append(transform)
        kpoints = generator.uniform(-0.8, 0.8, (5, 3))
        for transform in transforms:
            inverse = integer_inverse(transform)
            offset = generator.uniform(-2, 2, 3)
            target_cell = transform @ cell
            raw_positions = (positions - offset) @ inverse
            expected_positions = raw_positions - np.floor(raw_positions)
            old_kpoints = kpoints @ inverse.T
            expected_h2 = change_phase(fourier(hopping, old_kpoints, half=True),
                                       kpoints, np.floor(raw_positions))
            expected_h1 = change_phase(fourier(hopping, old_kpoints, half=True),
                                       old_kpoints, positions)
            for cartesian in (False, True):
                with self.subTest(transform=transform.tolist(), cartesian=cartesian):
                    mapped = model.change_unit_cell(
                        uc=target_cell if cartesian else transform,
                        offset=offset @ cell if cartesian else offset,
                        cartesian=cartesian,
                    )
                    assert_allclose(mapped.pos, expected_positions, atol=2e-12, rtol=0)
                    assert_allclose(mapped.uc, target_cell, atol=1e-12, rtol=0)
                    assert_allclose(mapped.hamilton(kpoints, convention=2), expected_h2,
                                    atol=2e-10, rtol=2e-12)
                    assert_allclose(mapped.hamilton(kpoints, convention=1), expected_h1,
                                    atol=2e-10, rtol=2e-12)

    def test_origin_boundary_gauges(self):
        generator = np.random.default_rng(912)
        cell, positions, hopping = random_half_model(generator, orbital_count=4)
        positions[:, 0] = [0.5 - 1e-10, 0.5 + 1e-10, -0.5 - 1e-10, 1.5 + 1e-10]
        offset = np.array([0.5, -0.8, 0.27])
        kpoints = generator.uniform(-1, 1, (6, 3))
        model = Model(uc=cell, pos=positions, hop=hopping, contains_cc=False)
        mapped = model.change_unit_cell(offset=offset)
        expected = change_phase(fourier(hopping, kpoints, half=True), kpoints,
                                np.floor(positions - offset))
        assert_allclose(mapped.pos, (positions - offset) % 1, atol=2e-15, rtol=0)
        assert_allclose(mapped.hamilton(kpoints), expected, atol=2e-13, rtol=0)

    def test_composition(self):
        generator = np.random.default_rng(890)
        cell, positions, hopping = random_half_model(generator)
        first = np.array([[1, -2, 0], [0, 1, 0], [0, 0, 1]])
        second = np.array([[1, 0, 0], [0, 1, 0], [2, -1, 1]])
        first_offset = np.array([0.21, -1.37, 0.43])
        second_offset = np.array([-0.75, 0.21, 1.02])
        model = Model(uc=cell, pos=positions, hop=hopping, contains_cc=False)
        sequential = model.change_unit_cell(uc=first, offset=first_offset).change_unit_cell(
            uc=second, offset=second_offset)
        direct = model.change_unit_cell(uc=second @ first,
                                        offset=first_offset + second_offset @ first)
        kpoints = generator.uniform(-1, 1, (7, 3))
        assert_allclose(sequential.pos, direct.pos, atol=5e-14, rtol=0)
        assert_allclose(sequential.hamilton(kpoints), direct.hamilton(kpoints), atol=5e-12, rtol=0)

    def test_half_stored_zero_block(self):
        matrix = np.array([[2 + 1j, 3 - 2j], [0.7j, -1 + 4j]])
        model = Model(uc=np.eye(3), pos=[[0.2, 0, 0], [0.7, 0, 0]],
                      hop={(0, 0, 0): matrix}, contains_cc=False)
        assert_allclose(model.hamilton([0, 0, 0]), matrix + matrix.conj().T, rtol=0, atol=0)


class ImportTests(unittest.TestCase):
    def test_direct_bond_supercells(self):
        generator = np.random.default_rng(93)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            directory = Path(temporary)
            for bohr in (False, True):
                cell, positions, centres, atoms, hopping, corrected = make_import_fixture(
                    directory, bohr=bohr)
                nearest = np.argmin(np.sum((centres[:, None, :] - atoms[None, :, :]) ** 2,
                                           axis=2), axis=1)
                atom_positions = np.linalg.solve(cell.T, atoms[nearest].T).T
                self.assertEqual(len(np.unique(nearest)), len(centres))
                for pos_kind in ('wannier', 'nearest_atom'):
                    for use_wsvec in (False, True):
                        with self.subTest(bohr=bohr, pos_kind=pos_kind, wsvec=use_wsvec):
                            loader = CartesianLoader if pos_kind == 'wannier' else AtomLoader
                            kwargs = dict(hr_file=directory / 'import_hr.dat',
                                          win_file=directory / 'import.win',
                                          xyz_file=directory / 'import_centres.xyz',
                                          ignore_orbital_order=True)
                            if pos_kind == 'nearest_atom':
                                kwargs['pos_kind'] = pos_kind
                            if use_wsvec:
                                kwargs['wsvec_file'] = directory / 'import_wsvec.dat'
                            primitive = loader.from_wannier_files(**kwargs)
                            size = (2, 2, 2)
                            model = primitive.supercell(size)
                            kpoints = generator.uniform(-1, 1, (4, 3))
                            raw_positions = positions if pos_kind == 'wannier' else atom_positions
                            expected_pos, expected_h2 = direct_supercell(
                                corrected if use_wsvec else hopping, raw_positions, size, kpoints)
                            assert_allclose(model.pos, expected_pos, atol=1e-14, rtol=0)
                            assert_allclose(model.hamilton(kpoints), expected_h2, atol=2e-13, rtol=0)
                            assert_allclose(model.hamilton(kpoints, convention=1),
                                            change_phase(expected_h2, kpoints, expected_pos),
                                            atol=3e-13, rtol=0)
                            folds = np.asarray(list(itertools.product(range(2), repeat=3)))
                            for point, matrix in zip(kpoints, expected_h2):
                                folded = np.linalg.eigvalsh(primitive.hamilton((point + folds) / size))
                                assert_allclose(np.linalg.eigvalsh(matrix), np.sort(folded.ravel()),
                                                atol=1e-13, rtol=0)

    def test_explicit_nearest_atom_and_first_tie(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            directory = Path(temporary)
            (directory / 'model_hr.dat').write_text('test\n2\n1\n1\n'
                                                   '0 0 0 1 1 1 0\n0 0 0 2 1 0.3 -0.4\n'
                                                   '0 0 0 1 2 0.3 0.4\n0 0 0 2 2 2 0\n')
            (directory / 'model.win').write_text('begin unit_cell_cart\n'
                                                '1 0 0\n0 1 0\n0 0 1\nend unit_cell_cart\n')
            (directory / 'model.xyz').write_text('5\ntie and no periodic search\n'
                                                'X 0.5 0 0\nX 10.1 0 0\n'
                                                'A 0.25 0 0\nB 0.75 0 0\nC 9.9 0 0\n')
            model = AtomLoader.from_wannier_files(
                hr_file=directory / 'model_hr.dat', win_file=directory / 'model.win',
                xyz_file=directory / 'model.xyz', pos_kind='nearest_atom')
            assert_allclose(model.pos, [[0.25, 0, 0], [0.9, 0, 0]], atol=1e-15, rtol=0)
            expected = np.array([[[1, 0.3 + 0.4j], [0.3 - 0.4j, 2]]])
            expected = change_phase(expected, [[0.123, 0, 0]], np.array([[0, 0, 0], [9, 0, 0]]))
            assert_allclose(model.hamilton([[0.123, 0, 0]]), expected, atol=1e-15, rtol=0)

    def test_integrated_output_and_permutations(self):
        generator = np.random.default_rng(56)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            directory = Path(temporary)
            cell, positions, centres, atoms, hopping, corrected = make_import_fixture(directory)
            map_cell, map_positions, map_hopping = random_half_model(generator, orbital_count=16)
            transform = np.array([[1, 2, -1], [0, 1, 3], [0, 0, 1]])
            inverse = integer_inverse(transform)
            offset = generator.uniform(-2, 2, 3)
            np.savez(directory / 'mapping.npz', uc=map_cell, pos=map_positions,
                     R=np.array(list(map_hopping)), hop=np.array(list(map_hopping.values())))
            import_permutation = generator.permutation(16)
            map_permutation = generator.permutation(16)
            import_kpoints = generator.uniform(-1, 1, (4, 3))
            map_kpoints = generator.uniform(-1, 1, (7, 3))
            spec = {'format_version': 1, 'import': {
                'hr': 'import_hr.dat', 'win': 'import.win', 'xyz': 'import_centres.xyz',
                'wsvec': 'import_wsvec.dat', 'pos_kind': 'wannier', 'supercell': [2, 1, 2],
                'permutation': import_permutation.tolist(), 'kpoints': import_kpoints.tolist()},
                'mapping': {'model': 'mapping.npz', 'uc': (transform @ map_cell).tolist(),
                            'offset': (offset @ map_cell).tolist(), 'cartesian': True,
                            'permutation': map_permutation.tolist(), 'kpoints': map_kpoints.tolist()}}
            (directory / 'case.json').write_text(json.dumps(spec))
            result = solve(directory)
            self.assertEqual(set(result), {'import_pos', 'import_h1', 'import_h2', 'import_bands',
                                           'map_pos', 'map_uc', 'map_h1', 'map_h2', 'map_bands'})
            expected_pos, expected_h2 = direct_supercell(corrected, positions, [2, 1, 2], import_kpoints)
            assert_allclose(result['import_pos'], expected_pos[import_permutation], atol=1e-14, rtol=0)
            assert_allclose(result['import_h2'], expected_h2[:, import_permutation][:, :, import_permutation],
                            atol=2e-13, rtol=0)
            raw_positions = (map_positions - offset) @ inverse
            expected_h2 = change_phase(fourier(map_hopping, map_kpoints @ inverse.T, half=True),
                                       map_kpoints, np.floor(raw_positions))
            assert_allclose(result['map_pos'], (raw_positions % 1)[map_permutation], atol=2e-13, rtol=0)
            assert_allclose(result['map_h2'], expected_h2[:, map_permutation][:, :, map_permutation],
                            atol=3e-12, rtol=0)
            for prefix, kpoints in [('import', import_kpoints), ('map', map_kpoints)]:
                assert_allclose(result[f'{prefix}_h1'], change_phase(result[f'{prefix}_h2'], kpoints,
                                                                    result[f'{prefix}_pos']), atol=1e-13)
                assert_allclose(result[f'{prefix}_bands'], np.linalg.eigvalsh(result[f'{prefix}_h2']),
                                atol=1e-13, rtol=0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
