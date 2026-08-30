import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'participant/workspace'))
sys.path.insert(0, str(ROOT / 'adversary/generation2_archive/adversary'))
from atlas import Atlas, orthonormalize, single_descent
from generate import direct_flux, eigensystem

FAMILIES = ('narrow_gap', 'scenario_frustration', 'heterogeneous_costs', 'multiple_cones')


def reference(nx, ny, parameters, scenario):
    horizontal = np.tile(np.arange(nx) * 2 * np.pi / nx, ny) + parameters['shift_x']
    vertical = np.repeat(np.arange(ny) * 2 * np.pi / ny, nx) + parameters['shift_y']
    mass = parameters['mass'] + parameters['uncertainty'] * (-1.0, -0.3, 0.35, 1.0)[scenario]
    eigenvalues, vectors = eigensystem(parameters['winding'] * horizontal, vertical, mass,
                                      parameters['anisotropy'], parameters['warp'])
    remote_values, remote_vectors = eigensystem(horizontal + 0.23, vertical - 0.17,
                                               parameters['remote_mass'], 0.9, 0.05)
    frames = np.zeros((nx * ny, 6, 2), dtype=complex)
    complements = np.zeros_like(frames)
    frames[:, :2, 0] = vectors[:, :, 0]
    frames[:, 2:4, 1] = remote_vectors[:, :, 0]
    complements[:, :2, 0] = vectors[:, :, 1]
    complements[:, 2:4, 1] = remote_vectors[:, :, 1]
    guide = np.sort(np.stack((eigenvalues[:, 0], 0.3 * remote_values[:, 0] - 2.2), axis=1), axis=1)
    return frames, complements, guide, horizontal, vertical


def make_case(family, seed, level, mesh=None):
    random = np.random.default_rng(seed)
    nx, ny = (10, 8) if level == 0 else (12, 8)
    parameters = {'mass': -1.05, 'uncertainty': 0.12, 'anisotropy': 1.0,
                  'warp': 0.0, 'winding': 1, 'remote_mass': 3.4,
                  'shift_x': float(random.uniform(0.09, 0.24)),
                  'shift_y': float(random.uniform(0.07, 0.22)), 'regime_level': level}
    if family == 'narrow_gap':
        parameters.update(mass=(-1.72, -1.86, -0.18)[level], uncertainty=(0.12, 0.065, 0.06)[level],
                          anisotropy=(1.0, 1.3, 1.5)[level])
    elif family == 'scenario_frustration':
        parameters.update(mass=-0.95, uncertainty=0.38, anisotropy=1.3, warp=0.10)
    elif family == 'heterogeneous_costs':
        parameters.update(mass=-1.30, uncertainty=0.24, anisotropy=1.45, warp=0.10)
    elif family == 'multiple_cones':
        nx = 12 if level == 0 else 16
        parameters.update(winding=2, mass=-1.15, uncertainty=0.18,
                          remote_mass=-1.1 if level == 2 else 3.4)
    if mesh is not None:
        nx, ny = mesh
        parameters['mesh_reason'] = 'Resolve the previously rejected narrow-gap Berry-curvature hotspot without changing its physical parameters.'
    vertices, scenarios, candidates = nx * ny, 4, 4
    frames = np.empty((scenarios, vertices, candidates, 6, 2), dtype=complex)
    energies = np.empty((scenarios, vertices, candidates, 2))
    spatial_noise = random.normal(size=(vertices, candidates, 2))
    phase_noise = random.uniform(-np.pi, np.pi, (vertices, candidates, 2))
    costs = np.tile(np.array([1, 3, 2, 0]), (vertices, 1))
    allowance = 0.50 * vertices
    if family == 'scenario_frustration':
        costs = np.tile(np.array([2, 3, 3, 0]), (vertices, 1))
        allowance = (0.40 + 0.1 * level) * vertices
    if family == 'heterogeneous_costs':
        costs[:, 0] = 2
        costs[:, 1] = random.integers(3, 8 + level, vertices)
        costs[:, 2] = random.integers(1, 5 + level, vertices)
        allowance = (0.65 + 0.1 * level) * vertices
    budget = int(costs[:, 0].sum() + allowance)
    guides, target_flux, scenario_metadata, refinement = [], [], [], []
    for scenario in range(scenarios):
        basis, complement, guide, horizontal, vertical = reference(nx, ny, parameters, scenario)
        flux = direct_flux(basis, nx, ny)
        chern = int(round(float(flux.sum() / (2 * np.pi))))
        refined, _, _, _, _ = reference(2 * nx, 2 * ny, parameters, scenario)
        refined_chern = float(direct_flux(refined, 2 * nx, 2 * ny).sum() / (2 * np.pi))
        if abs(chern - refined_chern) > 1e-8 or chern == 0:
            raise ValueError(f'reference Chern unresolved: {chern} versus {refined_chern}')
        refinement.append({'coarse_chern': chern, 'double_mesh_chern': refined_chern})
        guides.append(guide)
        target_flux.append(flux)
        loss_weights = [0.7, 0.32, 0.055, 0.55]
        if family in ('narrow_gap', 'scenario_frustration'):
            loss_weights = [0.7, 0.25, 0.055, 0.9 + 0.2 * level]
        scenario_metadata.append({'id': f'strain_{scenario}', 'weight': [1.0, 1.4, 1.2, 1.0][scenario],
                                  'normalizer': 1.0, 'target_chern': chern, 'loss_weights': loss_weights})
        for candidate in range(candidates):
            amplitude = [0.25, 0.035, 0.15 + 0.065 * abs(scenario - 1), 1.25][candidate]
            if family == 'scenario_frustration':
                amplitude = [[0.29] * 4, [0.04, 0.08, 0.32, 0.39],
                             [0.38, 0.31, 0.075, 0.035], [1.25] * 4][candidate][scenario]
            texture = 0.75 + 0.35 * np.sin(horizontal + 0.7 * scenario) ** 2
            angles = amplitude * texture[:, None] * (0.8 + 0.75 * spatial_noise[:, candidate])
            if family == 'scenario_frustration' and candidate in (1, 2):
                angles += (0.04 + 0.025 * level) * np.sin(horizontal + vertical)[:, None]
            if candidate == 3:
                angles[:, 0] = 1.30 + 0.17 * np.sin(horizontal - vertical)
                angles[:, 1] *= 0.12
            physical = basis * np.cos(angles)[:, None, :] + complement * (np.sin(angles) * np.exp(1j * phase_noise[:, candidate]))[:, None, :]
            leakage = random.normal(size=(vertices, 2, 2)) + 1j * random.normal(size=(vertices, 2, 2))
            physical[:, 4:6] += amplitude * 0.11 * leakage
            unitary = orthonormalize(random.normal(size=(vertices, 2, 2)) + 1j * random.normal(size=(vertices, 2, 2)))
            frames[scenario, :, candidate] = (orthonormalize(physical) @ unitary) * np.exp(random.uniform(-0.5, 0.5, (vertices, 2)))[:, None, :]
            energies[scenario, :, candidate] = np.sort(guide + amplitude * 0.20 * spatial_noise[:, candidate], axis=-1)
    permutations = np.stack([random.permutation(candidates) for vertex in range(vertices)])
    indices = np.arange(vertices)
    seed_choices = np.argmax(permutations == 0, axis=1)
    arrays = {'frames': frames[:, indices[:, None], permutations],
              'energies': energies[:, indices[:, None], permutations],
              'costs': costs[indices[:, None], permutations], 'guide': np.array(guides),
              'target_flux': np.array(target_flux), 'seed_choices': seed_choices}
    metadata = {'schema_version': 1, 'family': family, 'nx': nx, 'ny': ny, 'rank': 2,
                'ambient_dimension': 6, 'candidates': 4, 'budget': budget,
                'anchors': {str(vertex): int(seed_choices[vertex]) for vertex in [0, vertices // 2]},
                'scenarios': scenario_metadata, 'lambda_mean': 0.25, 'minimum_link': 1e-6,
                'branch_margin': 1e-5, 'chern_tolerance': 5e-7, 'parameters': parameters}
    atlas = Atlas(metadata, arrays)
    seed_score = atlas.score(seed_choices)
    if not seed_score['feasible']:
        raise ValueError(f'infeasible seed: {seed_score}')
    for scenario, row in enumerate(scenario_metadata):
        row['normalizer'] = seed_score['raw_loss'][scenario]
    atlas = Atlas(metadata, arrays)
    baseline = single_descent(atlas, seed_choices)
    arrays['baseline_choices'] = baseline
    baseline_score = atlas.score(baseline)
    metadata['baseline_objective'] = baseline_score['objective']
    metadata['baseline_algorithm'] = 'feasible best-improvement single-site descent from seed_choices'
    return metadata, arrays, {'seed': seed_score, 'baseline': baseline_score, 'reference_refinement': refinement}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=928173)
    parser.add_argument('--levels', type=int, default=3)
    parser.add_argument('--family', choices=FAMILIES)
    parser.add_argument('--level', type=int, choices=range(3))
    parser.add_argument('--mesh', type=int, nargs=2)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    output.relative_to(ROOT / 'adversary/ratchet3')
    output.mkdir(parents=True, exist_ok=False)
    rows, rejected = [], []
    for family_index, family in enumerate(FAMILIES):
        if arguments.family is not None and family != arguments.family:
            continue
        for level in range(arguments.levels):
            if arguments.level is not None and level != arguments.level:
                continue
            case_id = f'{family}_{level}'
            seed = arguments.seed + family_index * 1009 + level * 31
            try:
                metadata, arrays, checks = make_case(family, seed, level, arguments.mesh)
            except ValueError as error:
                rejected.append({'id': case_id, 'seed': seed, 'reason': str(error)})
                print('REJECT', case_id, str(error), flush=True)
                continue
            directory = output / case_id
            directory.mkdir()
            metadata['case_id'] = case_id
            (directory / 'case.json').write_text(json.dumps(metadata, indent=2) + '\n')
            np.savez_compressed(directory / 'arrays.npz', **arrays)
            rows.append({'id': case_id, 'family': family, 'directory': case_id, 'seed': seed, 'checks': checks})
            print('CASE', case_id, metadata['baseline_objective'], flush=True)
            (output / 'manifest.json').write_text(json.dumps({'cases': rows, 'rejected': rejected}, indent=2) + '\n')


if __name__ == '__main__':
    main()
