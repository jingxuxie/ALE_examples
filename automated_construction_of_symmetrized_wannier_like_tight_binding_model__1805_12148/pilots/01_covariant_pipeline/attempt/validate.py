"""Independent full-hopping and gauge-covariance regression checks."""

import argparse
import io
import itertools
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

from historical_model import Model
from import_atom import AtomLoader
from import_xyz import CartesianLoader
from pipeline import sample, solve


ERRORS = {}


def check_close(name, actual, expected, tolerance=3e-10):
    actual = np.asarray(actual)
    expected = np.asarray(expected)
    if actual.shape != expected.shape:
        raise AssertionError(f'{name}: shape {actual.shape} != {expected.shape}')
    error = float(np.max(np.abs(actual - expected), initial=0))
    ERRORS[name] = max(ERRORS.get(name, 0), error)
    if not np.all(np.isfinite(actual)) or error > tolerance:
        raise AssertionError(f'{name}: error {error:.6g} > {tolerance:.6g}')


def direct_import(case, spec):
    with (case / spec['win']).open() as stream:
        lines = [line.split('!')[0].strip().lower() for line in stream]
    start = next(index for index, line in enumerate(lines)
                 if 'begin' in line and 'unit_cell_cart' in line) + 1
    factor = 1.0
    if lines[start] in ('ang', 'bohr'):
        factor = 0.52917721092 if lines[start] == 'bohr' else 1.0
        start += 1
    cell = factor * np.array([[float(value) for value in line.split()]
                             for line in lines[start:start + 3]])
    xyz_rows = [line.split() for line in (case / spec['xyz']).read_text().splitlines()[2:]
                if line.strip()]
    centres = np.array([[float(value) for value in row[1:]]
                        for row in xyz_rows if row[0] == 'X'])
    if spec['pos_kind'] == 'nearest_atom':
        atoms = np.array([[float(value) for value in row[1:]]
                          for row in xyz_rows if row[0] != 'X'])
        centres = np.array([min(enumerate(atoms),
                                key=lambda pair: sum((centre - pair[1]) ** 2))[1]
                            for centre in centres])
    positions = centres @ np.linalg.inv(cell)
    shifts = np.floor(positions).astype(int)
    positions = positions - shifts
    size = len(positions)
    factors = np.asarray(spec['supercell'])
    images = list(itertools.product(*(range(factor) for factor in factors)))
    image_indices = {image: index for index, image in enumerate(images)}
    super_positions = np.concatenate([(positions + image) / factors for image in images])
    kpoints = np.asarray(spec['kpoints'])
    matrices = np.zeros((len(kpoints), size * len(images), size * len(images)), complex)
    ws_mapping = {}
    if spec.get('wsvec'):
        rows = iter((case / spec['wsvec']).read_text().splitlines()[1:])
        for row in rows:
            if not row.strip():
                continue
            key = tuple(map(int, row.split()))
            count = int(next(rows))
            ws_mapping[key] = [np.array(list(map(int, next(rows).split())))
                               for _ in range(count)]
    with (case / spec['hr']).open() as stream:
        next(stream)
        assert int(next(stream)) == size
        block_count = int(next(stream))
        degeneracies = []
        while len(degeneracies) < block_count:
            degeneracies.extend(map(int, next(stream).split()))
        rows = np.loadtxt(stream, ndmin=2)
    assert len(rows) == block_count * size ** 2
    for index, row in enumerate(rows):
        vector = row[:3].astype(int)
        orbital_one, orbital_two = row[3:5].astype(int) - 1
        strength = complex(*row[5:7]) / degeneracies[index // size ** 2]
        corrections = ws_mapping.get((*vector, orbital_one + 1, orbital_two + 1),
                                     [np.zeros(3, dtype=int)])
        for correction in corrections:
            shifted_vector = vector + correction + shifts[orbital_two] - shifts[orbital_one]
            for image_index, image in enumerate(images):
                destination = np.asarray(image) + shifted_vector
                target_image = tuple(destination % factors)
                super_vector = destination // factors
                target_index = image_indices[target_image] * size + orbital_two
                phases = np.exp(2j * np.pi * (kpoints @ super_vector))
                matrices[:, image_index * size + orbital_one, target_index] += (
                    strength / len(corrections) * phases
                )
    permutation = spec['permutation']
    return super_positions[permutation], matrices[:, permutation][:, :, permutation]


def direct_mapping(cell, positions, vectors, hopping, spec):
    target = np.asarray(spec['uc'], dtype=float)
    offset = np.asarray(spec['offset'], dtype=float)
    if spec['cartesian']:
        transform = target @ np.linalg.inv(cell)
        offset = offset @ np.linalg.inv(cell)
        target_cell = target
    else:
        transform = target
        target_cell = target @ cell
    transform = np.rint(transform).astype(int)
    inverse = np.rint(np.linalg.inv(transform)).astype(int)
    raw_positions = (positions - offset) @ inverse
    shifts = np.floor(raw_positions)
    positions_new = raw_positions - shifts
    kpoints = np.asarray(spec['kpoints'])
    old_kpoints = kpoints @ inverse.T
    fourier = np.einsum('ql,lij->qij', np.exp(2j * np.pi * (old_kpoints @ vectors.T)),
                        hopping)
    matrices = fourier + fourier.conj().transpose(0, 2, 1)
    phases = np.exp(2j * np.pi * (kpoints @ shifts.T))
    matrices = phases.conj()[:, :, None] * matrices * phases[:, None, :]
    permutation = spec['permutation']
    return (positions_new[permutation], target_cell,
            matrices[:, permutation][:, :, permutation])


def check_case(case):
    spec = json.loads((case / 'case.json').read_text())
    result = solve(case)
    assert set(result) == {
        'import_pos', 'import_h1', 'import_h2', 'import_bands',
        'map_pos', 'map_uc', 'map_h1', 'map_h2', 'map_bands'
    }
    positions, matrices = direct_import(case, spec['import'])
    check_close('import_positions', result['import_pos'], positions)
    check_close('import_full_matrix', result['import_h2'], matrices)
    check_close('import_spectrum', result['import_bands'], np.linalg.eigvalsh(matrices))
    with np.load(case / spec['mapping']['model']) as arrays:
        positions, cell, matrices = direct_mapping(
            arrays['uc'], arrays['pos'], arrays['R'], arrays['hop'], spec['mapping']
        )
    check_close('map_positions', result['map_pos'], positions)
    check_close('map_cell', result['map_uc'], cell)
    check_close('map_full_matrix', result['map_h2'], matrices)
    check_close('map_spectrum', result['map_bands'], np.linalg.eigvalsh(matrices))
    for prefix, track in (('import', 'import'), ('map', 'mapping')):
        positions = result[f'{prefix}_pos']
        matrices = result[f'{prefix}_h2']
        phases = np.exp(2j * np.pi * (np.asarray(spec[track]['kpoints']) @ positions.T))
        check_close(prefix + '_convention', result[f'{prefix}_h1'],
                    phases.conj()[:, :, None] * matrices * phases[:, None, :])
        check_close(prefix + '_hermiticity', matrices, matrices.conj().transpose(0, 2, 1))
        assert np.all((positions >= 0) & (positions < 1))


def smoke_variant_checks(source, root, rng):
    with tempfile.TemporaryDirectory(prefix='validation-', dir=root) as directory:
        case = Path(directory)
        spec = json.loads((source / 'case.json').read_text())
        for filename in [spec['import'][key] for key in ('win', 'hr', 'xyz', 'wsvec')
                         if spec['import'].get(key)] + [spec['mapping']['model']]:
            destination = case / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / filename, destination)
        with np.load(case / spec['mapping']['model']) as arrays:
            old_cell = arrays['uc']
        with (case / spec['import']['hr']).open() as stream:
            next(stream)
            primitive_size = int(next(stream))
        spec['import']['supercell'] = [1, 1, 3]
        spec['import']['permutation'] = rng.permutation(primitive_size * 3).tolist()
        spec['mapping']['kpoints'] = rng.uniform(-1, 1, (5, 3)).tolist()
        transform = np.array([[1, 3, 0], [1, 4, 2], [0, 0, 1]])
        offset = np.array([.21, -.32, .43])
        for pos_kind in ('wannier', 'nearest_atom'):
            for cartesian in (False, True):
                spec['import']['pos_kind'] = pos_kind
                spec['mapping']['cartesian'] = cartesian
                spec['mapping']['uc'] = (
                    transform @ old_cell if cartesian else transform
                ).tolist()
                spec['mapping']['offset'] = (
                    offset @ old_cell if cartesian else offset
                ).tolist()
                (case / 'case.json').write_text(json.dumps(spec))
                check_case(case)


def random_mapping_checks(rng):
    for trial in range(32):
        size = 16
        cell = rng.normal(size=(3, 3)) + 4 * np.eye(3)
        positions = rng.uniform(-2, 3, size=(size, 3))
        vectors = np.array(list(itertools.product(range(-2, 3), repeat=3)))
        hopping = rng.normal(size=(len(vectors), size, size))
        hopping = hopping + 1j * rng.normal(size=hopping.shape)
        transform = np.eye(3, dtype=int)
        for _ in range(5):
            row, other = rng.choice(3, 2, replace=False)
            transform[row] += rng.choice([-2, -1, 1, 2]) * transform[other]
        offset = rng.uniform(-1.5, 1.5, 3)
        kpoints = rng.uniform(-1, 1, (4, 3))
        if trial == 0:
            transform = np.array([[1, 3, 0], [1, 4, 2], [0, 0, 1]])
        if trial % 4 == 0:
            inverse = np.rint(np.linalg.inv(transform)).astype(int)
            boundary_positions = np.tile([0., 0.17, 0.43], (3, 1))
            boundary_positions[:, 0] = [-2e-10, 3e-10, 2e-10]
            positions[:3] = offset + boundary_positions @ transform
            raw_positions = (positions[:3] - offset) @ inverse
            if np.max(np.abs(raw_positions - boundary_positions)) > 1e-12:
                raise AssertionError('Synthetic boundary construction failed.')
        spec = dict(uc=transform.tolist(), offset=offset.tolist(), cartesian=False,
                    permutation=rng.permutation(size).tolist(), kpoints=kpoints.tolist())
        model = Model(uc=cell, pos=positions,
                      hop=dict(zip(map(tuple, vectors), hopping)), contains_cc=False)
        for cartesian in (False, True):
            spec['cartesian'] = cartesian
            spec['uc'] = (transform @ cell).tolist() if cartesian else transform.tolist()
            spec['offset'] = (offset @ cell).tolist() if cartesian else offset.tolist()
            expected_pos, expected_uc, expected_h2 = direct_mapping(
                cell, positions, vectors, hopping, spec
            )
            mapped = model.change_unit_cell(uc=spec['uc'], offset=spec['offset'],
                                           cartesian=cartesian)
            actual = sample(mapped, kpoints, spec['permutation'], 'map')
            check_close('random_map_positions', actual['map_pos'], expected_pos)
            check_close('random_map_uc', mapped.uc, expected_uc)
            check_close('random_map_matrix', actual['map_h2'], expected_h2, 2e-8)
            check_close('random_map_bands', actual['map_bands'],
                        np.linalg.eigvalsh(expected_h2), 2e-8)
            inverse = np.rint(np.linalg.inv(transform)).astype(int)
            old_h1 = np.einsum(
                'ql,lij->qij', np.exp(2j * np.pi * ((kpoints @ inverse.T) @ vectors.T)),
                hopping
            )
            old_h1 += old_h1.conj().transpose(0, 2, 1)
            phases = np.exp(2j * np.pi * ((kpoints @ inverse.T) @ positions.T))
            old_h1 = phases.conj()[:, :, None] * old_h1 * phases[:, None, :]
            permutation = spec['permutation']
            check_close('origin_independent_h1', actual['map_h1'],
                        old_h1[:, permutation][:, :, permutation], 2e-8)


def parser_edge_checks():
    vectors = np.array([[-1, 0, 0], [0, 0, 0], [1, 0, 0]])
    forward = np.array([[1 + 2j, 3 - 4j], [-2 + 1j, 5 + 3j]])
    onsite = np.array([[2, 1 + 1j], [1 - 1j, -3]])
    matrices = np.array([forward.conj().T, onsite, forward])
    degeneracies = [2, 3, 4]
    text = io.StringIO('Synthetic parser fixture\n2\n3\n2\n3\n4\n')
    text.seek(0, io.SEEK_END)
    for vector, matrix, degeneracy in zip(vectors, matrices, degeneracies):
        for row, column in ((1, 1), (0, 1), (1, 0), (0, 0)):
            value = matrix[row, column] * degeneracy
            real = f'{value.real:.16e}'.replace('e', 'D')
            imaginary = f'{value.imag:.16e}'.replace('e', 'd')
            text.write(' '.join(map(str, (*vector, row + 1, column + 1)))
                       + f' {real} {imaginary}\n\n')
    text.seek(0)
    size, entries = Model._read_hr(text, ignore_orbital_order=True)
    model = Model.from_hop_list(size=size, hop_list=entries)
    kpoints = np.array([[.13, .1, .2], [-.57, -.3, .7]])
    expected = np.einsum('ql,lij->qij', np.exp(2j * np.pi * (kpoints @ vectors.T)), matrices)
    check_close('hr_explicit_indices_and_degeneracies', model.hamilton(kpoints), expected)
    win = io.StringIO('# header\nBEGIN UNIT_CELL_CART\nang\n'
                      '2D0\t0\t0 # row one\n0\t3d0\t0\n0\t0\t4\nEND UNIT_CELL_CART\n')
    check_close('win_whitespace_comments', Model._read_win(win)['unit_cell_cart'],
                np.diag([2, 3, 4]))
    xyz = io.StringIO('2\nXYZ parser fixture\n\nX 1d0 2D0 3.0\n\nSi 4 5 6\n')
    centres, atoms = Model._read_xyz(xyz)
    check_close('xyz_whitespace', centres, [[1, 2, 3]])
    check_close('xyz_atoms', [atom.pos for atom in atoms], [[4, 5, 6]])
    wsvec = io.StringIO('WS parser fixture\n\n1 0 0 1 2\n\n2\n0 0 0\n\n-1 1 0\n')
    records = dict(Model._read_wsvec(wsvec))
    check_close('wsvec_whitespace', records[(0, 1, (1, 0, 0))], [[0, 0, 0], [-1, 1, 0]])


def boundary_mapping_checks(rng):
    size = 16
    cell = np.diag([2., 4., 8.])
    positions = rng.uniform(.1, .9, (size, 3))
    positions[:3, 0] = [.5 - 2e-10, .5, .5 + 2e-10]
    vectors = np.array([[0, 0, 0], [1, 0, 0], [0, -1, 1]])
    hopping = rng.normal(size=(3, size, size)) + 1j * rng.normal(size=(3, size, size))
    model = Model(uc=cell, pos=positions, hop=dict(zip(map(tuple, vectors), hopping)),
                  contains_cc=False)
    for cartesian in (False, True):
        spec = dict(uc=cell.tolist() if cartesian else np.eye(3).tolist(),
                    offset=[1., 0., 0.] if cartesian else [.5, 0., 0.],
                    cartesian=cartesian, permutation=rng.permutation(size).tolist(),
                    kpoints=rng.uniform(-1, 1, (4, 3)).tolist())
        mapped = model.change_unit_cell(uc=spec['uc'], offset=spec['offset'],
                                       cartesian=cartesian)
        result = sample(mapped, spec['kpoints'], spec['permutation'], 'map')
        expected_pos, _, expected_h2 = direct_mapping(cell, positions, vectors, hopping, spec)
        check_close('boundary_positions_no_snapping', result['map_pos'], expected_pos)
        check_close('boundary_matrix_gauge', result['map_h2'], expected_h2)


def write_synthetic_import(case, rng):
    size = 4
    vectors = np.array(list(itertools.product(range(-1, 2), repeat=3)))
    full_hopping = rng.normal(size=(len(vectors), size, size))
    full_hopping = full_hopping + 1j * rng.normal(size=full_hopping.shape)
    full_hopping = (full_hopping + full_hopping[::-1].conj().transpose(0, 2, 1)) / 2
    degeneracies = rng.integers(1, 7, len(vectors))
    with (case / 'synthetic_hr.dat').open('w') as stream:
        stream.write(f'Synthetic complete complex hopping fixture\n{size}\n{len(vectors)}\n')
        for start in range(0, len(vectors), 15):
            stream.write(' '.join(map(str, degeneracies[start:start + 15])) + '\n')
        for block, vector in enumerate(vectors):
            for column in range(size):
                for row in range(size):
                    value = full_hopping[block, row, column] * degeneracies[block]
                    stream.write(' '.join(map(str, (*vector, row + 1, column + 1)))
                                 + f' {value.real:.17g} {value.imag:.17g}\n')
    ws_mapping = {}
    for vector in vectors:
        for row in range(1, size + 1):
            for column in range(1, size + 1):
                key = (*vector, row, column)
                if key in ws_mapping:
                    continue
                partner = (*(-vector), column, row)
                corrections = rng.integers(-2, 3, (rng.integers(1, 4), 3))
                if key == partner:
                    corrections = np.concatenate((corrections, -corrections))
                ws_mapping[key] = corrections
                ws_mapping[partner] = -corrections
    keys = list(ws_mapping)
    rng.shuffle(keys)
    with (case / 'synthetic_wsvec.dat').open('w') as stream:
        stream.write('Shuffled Wigner-Seitz corrections\n')
        for key in keys:
            corrections = ws_mapping[key]
            stream.write(' '.join(map(str, key)) + f'\n{len(corrections)}\n')
            for correction in corrections:
                stream.write(' '.join(map(str, correction)) + '\n')
    cell = np.array([[2.1, 0.3, -0.2], [0.1, 2.8, 0.4], [-0.3, 0.2, 3.7]])
    centres = np.array([[0., 0., 0.], [4.2, -0.7, 1.2], [-1.1, 3.4, -0.8],
                        [0.9, 1.1, 6.9]])
    atoms = np.array([[1., 0., 0.], [-1., 0., 0.], [4., -0.5, 1.],
                     [-1., 3., -1.], [1., 1., 7.]])
    with (case / 'synthetic_centres.xyz').open('w') as stream:
        stream.write(f'{len(centres) + len(atoms)}\nCartesian off-cell positions and ties\n')
        for label, positions in (('X', centres), ('Si', atoms)):
            for position in positions:
                stream.write(label + ' ' + ' '.join(map(str, position)) + '\n')
    with (case / 'synthetic.win').open('w') as stream:
        stream.write('begin unit_cell_cart\nbohr\n')
        np.savetxt(stream, cell / 0.52917721092, fmt='%.17g')
        stream.write('end unit_cell_cart\n')
    return cell, centres, atoms


def synthetic_import_checks(rng, root):
    with tempfile.TemporaryDirectory(prefix='validation-', dir=root) as directory:
        case = Path(directory)
        cell, centres, atoms = write_synthetic_import(case, rng)
        for pos_kind in ('wannier', 'nearest_atom'):
            for use_wsvec in (False, True):
                for factors in ((2, 2, 1), (1, 2, 2), (2, 1, 3)):
                    spec = dict(hr='synthetic_hr.dat', win='synthetic.win',
                                xyz='synthetic_centres.xyz',
                                wsvec='synthetic_wsvec.dat' if use_wsvec else None,
                                pos_kind=pos_kind, supercell=factors,
                                permutation=rng.permutation(4 * np.prod(factors)).tolist(),
                                kpoints=rng.uniform(-1, 1, (5, 3)).tolist())
                    kwargs = {f'{key}_file': str(case / spec[key])
                              for key in ('hr', 'win', 'xyz', 'wsvec') if spec[key]}
                    loader = CartesianLoader if pos_kind == 'wannier' else AtomLoader
                    primitive = loader.from_wannier_files(**kwargs, pos_kind=pos_kind)
                    model = primitive.supercell(factors)
                    actual = sample(model, spec['kpoints'], spec['permutation'], 'import')
                    expected_pos, expected_h2 = direct_import(case, spec)
                    check_close('synthetic_import_positions', actual['import_pos'], expected_pos)
                    check_close('synthetic_import_matrix', actual['import_h2'], expected_h2)
                    check_close('synthetic_import_bands', actual['import_bands'],
                                np.linalg.eigvalsh(expected_h2))
                    if pos_kind == 'nearest_atom':
                        expected_atoms = atoms[[0, 2, 3, 4]] @ np.linalg.inv(cell)
                        check_close('cartesian_atom_tie', primitive.pos, expected_atoms % 1)
                    unfolded = []
                    for image in itertools.product(*(range(factor) for factor in factors)):
                        primitive_k = (np.asarray(spec['kpoints']) + image) / factors
                        unfolded.append(np.linalg.eigvalsh(primitive.hamilton(primitive_k)))
                    check_close('supercell_band_folding', actual['import_bands'],
                                np.sort(np.concatenate(unfolded, axis=1), axis=1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=Path,
                        default=Path(__file__).resolve().parent.parent / 'participant/input/smoke')
    args = parser.parse_args()
    rng = np.random.default_rng(20260827)
    check_case(args.case)
    parser_edge_checks()
    synthetic_import_checks(rng, Path(__file__).resolve().parent)
    random_mapping_checks(rng)
    boundary_mapping_checks(rng)
    smoke_variant_checks(args.case, Path(__file__).resolve().parent, rng)
    print(json.dumps(ERRORS, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
