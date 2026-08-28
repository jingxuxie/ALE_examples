import argparse
import hashlib
import importlib.util
import json
import pathlib
import shutil
import time

import numpy as np
from scipy.spatial.transform import Rotation


ROOT = pathlib.Path(__file__).resolve().parents[1]
PILOT = ROOT / 'pilots/04_effective_physics'
SPEC = importlib.util.spec_from_file_location('upstream', PILOT / 'private/reference/upstream.py')
UPSTREAM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPSTREAM)
MATERIALS = {
    'bulk_bi2se3': 'Example/Bi2Se3/mat2kp',
    'monolayer_mose2': 'Example/1H-TMD/MoSe2/mat2kp',
    'monolayer_mote2': 'Example/1H-TMD/MoTe2/mat2kp',
    'monolayer_wte2': 'Example/1H-TMD/WTe2/mat2kp',
}


def base_material(name):
    directory = PILOT / 'private/reference/base'
    directory.mkdir(parents=True, exist_ok=True)
    input_path = directory / (name + '_input.npz')
    reference_path = directory / (name + '_reference.npz')
    if input_path.exists() and reference_path.exists():
        return dict(np.load(input_path)), dict(np.load(reference_path))
    started = time.monotonic()
    case, unitary, log = UPSTREAM.load_material(MATERIALS[name])
    np.savez_compressed(input_path, **case)
    (directory / (name + '_load.log')).write_text(log)
    reference = UPSTREAM.coefficients(case)
    reference['U'] = unitary
    np.savez_compressed(reference_path, **reference)
    report = {'seconds': time.monotonic() - started, 'bands': len(case['energy']), 'target': case['target'].tolist(), 'gauge_residual': UPSTREAM.gauge_residual(case, unitary), 'hermitian_residuals': {key: float(np.linalg.norm(value - value.swapaxes(0, 1).conj()) / max(1, np.linalg.norm(value))) for key, value in reference.items() if key != 'U'}}
    (directory / (name + '_validation.json')).write_text(json.dumps(report, indent=2))
    print(name, report, flush=True)
    return case, reference


def selected_doublet(case, reference, upper):
    selected = np.arange(2, 4) if upper else np.arange(2)
    result = {key: value.copy() for key, value in case.items()}
    result['target'] = case['target'][selected]
    result['spin'] = case['spin'][:, selected][:, :, selected]
    result['dft_repr'] = case['dft_repr'][:, selected][:, :, selected]
    result['standard_repr'] = case['standard_repr'][:, selected][:, :, selected]
    unitary = reference['U'][np.ix_(selected, selected)]
    left, singular, right = np.linalg.svd(unitary)
    unitary = left @ right
    coefficients = UPSTREAM.coefficients(result)
    coefficients['U'] = unitary
    return result, coefficients


def unitary_blocks(energies, random):
    dimension = len(energies)
    unitary = np.zeros((dimension, dimension), dtype=complex)
    unused = set(range(dimension))
    while unused:
        first = min(unused)
        group = np.asarray([index for index in sorted(unused) if abs(energies[index] - energies[first]) < 1e-9])
        matrix = random.normal(size=(len(group), len(group))) + 1j * random.normal(size=(len(group), len(group)))
        orthogonal, triangular = np.linalg.qr(matrix)
        unitary[np.ix_(group, group)] = orthogonal
        unused.difference_update(group)
    return unitary


def transformed(case, reference, seed, rotate, energy_shift):
    random = np.random.default_rng(seed)
    selected = case['target']
    unitary = unitary_blocks(case['energy'][selected], random)
    axes = Rotation.random(random_state=random).as_matrix() if rotate else np.eye(3)
    result = {key: value.copy() for key, value in case.items()}
    momentum = np.einsum('ab,bij->aij', axes, case['momentum'], optimize=True)
    momentum[:, selected, :] = np.einsum('ij,ajk->aik', unitary.conj().T, momentum[:, selected, :], optimize=True)
    momentum[:, :, selected] = np.einsum('aij,jk->aik', momentum[:, :, selected], unitary, optimize=True)
    result['momentum'] = momentum
    result['spin'] = np.einsum('ab,bij->aij', axes, np.asarray([UPSTREAM.rotate_basis(matrix, unitary) for matrix in case['spin']]), optimize=True)
    result['energy'] += energy_shift
    result['dft_repr'] = np.asarray([unitary.conj().T @ matrix @ (unitary.conj() if anti else unitary) for matrix, anti in zip(case['dft_repr'], case['antiunitary'])])
    result['cart_rotation'] = np.einsum('ab,gbc,dc->gad', axes, case['cart_rotation'], axes, optimize=True)
    target = {key: UPSTREAM.rotate_basis(value, unitary) for key, value in reference.items() if key != 'U'}
    target['H0'] += energy_shift * np.eye(len(selected))
    target['H1'] = np.einsum('ijb,ab->ija', target['H1'], axes, optimize=True)
    target['H2'] = np.einsum('ijbc,ab,dc->ijad', target['H2'], axes, axes, optimize=True)
    target['H3'] = np.einsum('ijbce,ab,dc,fe->ijadf', target['H3'], axes, axes, axes, optimize=True)
    target['G'] = np.einsum('ijb,ab->ija', target['G'], axes, optimize=True)
    target['U'] = unitary.conj().T @ reference['U']
    return result, target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--material', choices=list(MATERIALS))
    parser.add_argument('--assemble', action='store_true')
    arguments = parser.parse_args()
    if arguments.material:
        base_material(arguments.material)
        return
    bases = {name: base_material(name) for name in MATERIALS}
    if not arguments.assemble:
        return
    for directory in ['participant/input', 'private/challenge_pool', 'private/reference/outputs', 'attempt']:
        (PILOT / directory).mkdir(parents=True, exist_ok=True)
    manifest = []
    for material_index, (name, (case, reference)) in enumerate(bases.items()):
        for split, seeds in [('test', [11, 23]), ('challenge', [107, 211, 307]), ('confirmation', [4001, 5003, 6007])]:
            for ordinal, seed in enumerate(seeds):
                identifier = f'{split}_{name}_{ordinal}'
                input_case, expected = transformed(case, reference, seed + 10000 * material_index, rotate=ordinal > 0, energy_shift=0.7 * ordinal)
                input_path = PILOT / 'private/challenge_pool' / (identifier + '.npz')
                reference_path = PILOT / 'private/reference/outputs' / (identifier + '.npz')
                np.savez_compressed(input_path, **input_case)
                np.savez_compressed(reference_path, **expected)
                manifest.append({'id': identifier, 'split': split, 'family': name, 'source': MATERIALS[name], 'seed': seed + 10000 * material_index, 'input': str(input_path.relative_to(PILOT / 'private')), 'reference': str(reference_path.relative_to(PILOT / 'private')), 'bands': len(case['energy']), 'target_dimension': len(case['target'])})
    bulk_case, bulk_reference = bases['bulk_bi2se3']
    for upper in [False, True]:
        name = 'bulk_conduction_doublet' if upper else 'bulk_valence_doublet'
        case, reference = selected_doublet(bulk_case, bulk_reference, upper)
        for split, seeds in [('challenge', [1201, 1303]), ('confirmation', [17011, 19013, 23003])]:
            for ordinal, seed in enumerate(seeds):
                identifier = f'{split}_{name}_{ordinal}'
                input_case, expected = transformed(case, reference, seed, rotate=True, energy_shift=0.3 * ordinal)
                input_path = PILOT / 'private/challenge_pool' / (identifier + '.npz')
                reference_path = PILOT / 'private/reference/outputs' / (identifier + '.npz')
                np.savez_compressed(input_path, **input_case)
                np.savez_compressed(reference_path, **expected)
                manifest.append({'id': identifier, 'split': split, 'family': name, 'source': MATERIALS['bulk_bi2se3'], 'seed': seed, 'input': str(input_path.relative_to(PILOT / 'private')), 'reference': str(reference_path.relative_to(PILOT / 'private')), 'bands': len(case['energy']), 'target_dimension': len(case['target'])})
    (PILOT / 'private/challenge_pool/manifest.json').write_text(json.dumps(manifest, indent=2))
    smoke, smoke_reference = bases['monolayer_mose2']
    np.savez_compressed(PILOT / 'participant/input/smoke.npz', **smoke)
    source = ROOT / 'authoring/sources/VASP2KP'
    hashes = {str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (source / 'VASP2KP==1.1.5/VASP2KP').glob('*.py')}
    (PILOT / 'private/reference/source_hashes.json').write_text(json.dumps(hashes, indent=2))
    shutil.copyfile(source / 'LICENSE.txt', PILOT / 'participant/input/DATA_LICENSE.txt')
    print('Assembled', len(manifest), 'private cases', flush=True)


if __name__ == '__main__':
    main()
