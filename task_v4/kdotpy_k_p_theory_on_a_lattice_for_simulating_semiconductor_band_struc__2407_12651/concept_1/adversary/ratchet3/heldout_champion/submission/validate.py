import copy
import json
from pathlib import Path
import sys

from solve import load_atlas
import numpy as np


ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parents[1] / 'participant' / 'input'
VALIDATION = ROOT / 'validation'


def read_case(name):
    directory = INPUT / name
    metadata = json.loads((directory / 'case.json').read_text())
    with np.load(directory / 'arrays.npz') as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    return metadata, arrays


def write_case(name, metadata, arrays, rebuild=False):
    directory = VALIDATION / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'case.json').write_text(json.dumps(metadata))
    np.savez(directory / 'arrays.npz', **arrays)
    atlas = load_atlas(directory)
    if rebuild:
        from atlas import single_descent
        raw_loss = atlas.score(atlas.seed)['raw_loss']
        for scenario, loss in enumerate(raw_loss):
            metadata['scenarios'][scenario]['normalizer'] = loss
        (directory / 'case.json').write_text(json.dumps(metadata))
        atlas = load_atlas(directory)
        arrays['baseline_choices'] = single_descent(atlas, atlas.seed)
        metadata['baseline_objective'] = atlas.score(arrays['baseline_choices'])['objective']
        (directory / 'case.json').write_text(json.dumps(metadata))
        np.savez(directory / 'arrays.npz', **arrays)
    assert atlas.score(arrays['seed_choices'])['feasible']
    assert atlas.score(arrays['baseline_choices'])['feasible']
    print(name, atlas.score(arrays['baseline_choices']), flush=True)


def create_cases():
    metadata, arrays = read_case('scenario_competition_0')
    generator = np.random.default_rng(10921)
    nx, ny = metadata['nx'], metadata['ny']
    vertex_map = np.array([row * nx + (-column) % nx for row in range(ny) for column in range(nx)])
    inverse = np.argsort(vertex_map)
    for key in ['frames', 'energies', 'guide']:
        arrays[key] = arrays[key][:, vertex_map]
    for key in ['costs', 'seed_choices', 'baseline_choices']:
        arrays[key] = arrays[key][vertex_map]
    flux_map = np.array([row * nx + (-column - 1) % nx for row in range(ny) for column in range(nx)])
    arrays['target_flux'] = -arrays['target_flux'][:, flux_map]
    metadata['anchors'] = {str(inverse[int(vertex)]): label for vertex, label in metadata['anchors'].items()}
    for scenario in metadata['scenarios']:
        scenario['target_chern'] *= -1
    permutation = np.array([generator.permutation(4) for vertex in range(nx * ny)])
    inverse_permutation = permutation.argsort(axis=1)
    arrays['frames'] = np.take_along_axis(arrays['frames'], permutation[None, :, :, None, None], axis=2)
    arrays['energies'] = np.take_along_axis(arrays['energies'], permutation[None, :, :, None], axis=2)
    arrays['costs'] = np.take_along_axis(arrays['costs'], permutation, axis=1)
    for key in ['seed_choices', 'baseline_choices']:
        arrays[key] = inverse_permutation[np.arange(nx * ny), arrays[key]]
    metadata['anchors'] = {vertex: int(inverse_permutation[int(vertex), label]) for vertex, label in metadata['anchors'].items()}
    matrices = generator.normal(size=(4, nx * ny, 4, 2, 2)) + 1j * generator.normal(size=(4, nx * ny, 4, 2, 2))
    unitary = np.stack([np.linalg.qr(matrix)[0] for matrix in matrices.reshape(-1, 2, 2)]).reshape(matrices.shape)
    scales = np.exp(generator.uniform(-1, 1, size=(4, nx * ny, 4, 1, 2)))
    arrays['frames'] = arrays['frames'] @ (unitary * scales)
    scenario_order = [2, 0, 3, 1]
    for key in ['frames', 'energies', 'guide', 'target_flux']:
        arrays[key] = arrays[key][scenario_order]
    metadata['scenarios'] = [metadata['scenarios'][scenario] for scenario in scenario_order]
    write_case('gauge_permutation_reflection', metadata, arrays)

    metadata, arrays = read_case('gap_hotspots_0')
    nx, ny = metadata['nx'], metadata['ny']
    vertex_map = np.array([row * nx + max(0, column - 1) for row in range(ny) for column in range(nx + 1)])
    for key in ['frames', 'energies', 'guide']:
        arrays[key] = arrays[key][:, vertex_map]
    for key in ['costs', 'seed_choices', 'baseline_choices']:
        arrays[key] = arrays[key][vertex_map]
    flux = arrays['target_flux'].reshape(4, ny, nx)
    arrays['target_flux'] = np.concatenate([np.zeros((4, ny, 1)), flux], axis=2).reshape(4, -1)
    metadata['nx'] = nx + 1
    metadata['budget'] = 108
    metadata['anchors'] = {str((int(vertex) // nx) * (nx + 1) + int(vertex) % nx): label
                           for vertex, label in metadata['anchors'].items()}
    write_case('nine_by_eight', metadata, arrays, rebuild=True)

    metadata, arrays = read_case('gap_hotspots_0')
    arrays['seed_choices'] = arrays['costs'].argmin(axis=1)
    for vertex, label in metadata['anchors'].items():
        arrays['seed_choices'][int(vertex)] = label
    for scenario in metadata['scenarios']:
        scenario['target_chern'] = 0
    arrays['baseline_choices'] = arrays['seed_choices'].copy()
    write_case('zero_chern', metadata, arrays, rebuild=True)


def check_outputs():
    for directory in sorted(VALIDATION.iterdir()):
        if not directory.is_dir():
            continue
        output_path = directory / 'solution.json'
        if not output_path.exists():
            continue
        atlas = load_atlas(directory)
        output = json.loads(output_path.read_text())
        assert set(output) == {'choices'}
        assert all(type(choice) is int for choice in output['choices'])
        result = atlas.score(output['choices'])
        assert result['feasible'], result
        assert result['objective'] <= atlas.metadata['baseline_objective'] + 1e-10
        print(directory.name, result, 'gain', 1 - result['objective'] / atlas.metadata['baseline_objective'], flush=True)


if __name__ == '__main__':
    if '--check' in sys.argv:
        check_outputs()
    else:
        create_cases()
