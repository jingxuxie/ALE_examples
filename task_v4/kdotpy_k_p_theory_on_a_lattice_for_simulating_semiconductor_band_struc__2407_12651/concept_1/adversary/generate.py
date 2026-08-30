import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
from atlas import Atlas, orthonormalize, single_descent, torus, wrap_phase

FAMILIES = ('gap_hotspots', 'inversion_proximity', 'anisotropic_warping', 'scenario_competition')


def eigensystem(horizontal, vertical, mass, anisotropy, warp):
    first = anisotropy * np.sin(horizontal)
    second = np.sin(vertical) / anisotropy
    third = mass + np.cos(horizontal) + np.cos(vertical) + warp * (np.cos(2 * horizontal) - np.cos(2 * vertical))
    matrix = np.zeros((len(horizontal), 2, 2), dtype=complex)
    matrix[:, 0, 0] = third
    matrix[:, 1, 1] = -third
    matrix[:, 0, 1] = first - 1j * second
    matrix[:, 1, 0] = first + 1j * second
    return np.linalg.eigh(matrix)


def reference_frames(nx, ny, parameters, scenario):
    horizontal = np.tile(np.arange(nx) * 2 * np.pi / nx, ny) + parameters['shift_x']
    vertical = np.repeat(np.arange(ny) * 2 * np.pi / ny, nx) + parameters['shift_y']
    offset = (-1.0, -0.3, 0.35, 1.0)[scenario]
    mass = parameters['mass'] + parameters['uncertainty'] * offset
    energies, vectors = eigensystem(horizontal, vertical, mass, parameters['anisotropy'], parameters['warp'])
    remote_energies, remote_vectors = eigensystem(horizontal + 0.23, vertical - 0.17, 3.4, 0.9, 0.05)
    frames = np.zeros((nx * ny, 6, 2), dtype=complex)
    complements = np.zeros_like(frames)
    frames[:, :2, 0] = vectors[:, :, 0]
    frames[:, 2:4, 1] = remote_vectors[:, :, 0]
    complements[:, :2, 0] = vectors[:, :, 1]
    complements[:, 2:4, 1] = remote_vectors[:, :, 1]
    guide = np.sort(np.stack((energies[:, 0], 0.3 * remote_energies[:, 0] - 2.2), axis=1), axis=1)
    return frames, complements, guide, horizontal, vertical


def direct_flux(frames, nx, ny):
    bases = np.array([np.linalg.qr(frame)[0] for frame in frames])
    edges, plaquettes = torus(nx, ny)
    fluxes = []
    for corners in plaquettes:
        product = 1 + 0j
        for position in range(4):
            source, destination = corners[position], corners[(position + 1) % 4]
            product *= np.linalg.det(bases[source].conj().T @ bases[destination])
        fluxes.append(np.angle(product))
    return np.array(fluxes)


def make_case(family, seed, nx=8, ny=8):
    random = np.random.default_rng(seed)
    vertices, scenarios, candidates = nx * ny, 4, 4
    parameters = {'mass': -1.05, 'uncertainty': 0.12, 'anisotropy': 1.0,
                  'warp': 0.0, 'shift_x': float(random.uniform(0.04, 0.25)),
                  'shift_y': float(random.uniform(0.05, 0.27))}
    if family == 'gap_hotspots':
        parameters.update(mass=-1.48, uncertainty=0.10)
    elif family == 'inversion_proximity':
        parameters.update(mass=-0.48, uncertainty=0.12)
    elif family == 'anisotropic_warping':
        parameters.update(anisotropy=1.45, warp=0.13)
    elif family == 'scenario_competition':
        parameters.update(mass=-1.15, uncertainty=0.32, anisotropy=1.15)
    frames = np.empty((scenarios, vertices, candidates, 6, 2), dtype=complex)
    energies = np.empty((scenarios, vertices, candidates, 2))
    guides, target_flux, scenario_metadata = [], [], []
    spatial_noise = random.normal(size=(vertices, candidates, 2))
    phase_noise = random.uniform(-np.pi, np.pi, (vertices, candidates, 2))
    costs = np.tile(np.array([1, 3, 2, 0]), (vertices, 1))
    for scenario in range(scenarios):
        reference, complement, guide, horizontal, vertical = reference_frames(nx, ny, parameters, scenario)
        flux = direct_flux(reference, nx, ny)
        chern = int(round(float(flux.sum() / (2 * np.pi))))
        if abs(chern) != 1:
            raise ValueError('reference does not have the intended nonzero Chern number')
        guides.append(guide)
        target_flux.append(flux)
        scenario_metadata.append({'id': f'strain_{scenario}', 'weight': [1.0, 1.4, 1.2, 1.0][scenario],
                                  'normalizer': 1.0, 'target_chern': chern,
                                  'loss_weights': [0.7, 0.32, 0.055, 0.55]})
        for candidate in range(candidates):
            amplitude = [0.25, 0.035, 0.15 + 0.065 * abs(scenario - 1), 1.25][candidate]
            if family == 'scenario_competition' and candidate == 2:
                amplitude = [0.045, 0.10, 0.25, 0.39][scenario]
            texture = 0.75 + 0.35 * np.sin(horizontal + 0.7 * scenario) ** 2
            angles = amplitude * texture[:, None] * (0.8 + 0.75 * spatial_noise[:, candidate])
            if candidate == 3:
                angles[:, 0] = 1.30 + 0.17 * np.sin(horizontal - vertical)
                angles[:, 1] *= 0.12
            physical = reference * np.cos(angles)[:, None, :] + complement * (np.sin(angles) * np.exp(1j * phase_noise[:, candidate]))[:, None, :]
            leakage = random.normal(size=(vertices, 2, 2)) + 1j * random.normal(size=(vertices, 2, 2))
            physical[:, 4:6] += amplitude * 0.11 * leakage
            basis = orthonormalize(physical)
            raw_gauge = random.normal(size=(vertices, 2, 2)) + 1j * random.normal(size=(vertices, 2, 2))
            unitary = orthonormalize(raw_gauge)
            scales = np.exp(random.uniform(-0.5, 0.5, (vertices, 2)))
            frames[scenario, :, candidate] = (basis @ unitary) * scales[:, None, :]
            energy_noise = amplitude * 0.20 * spatial_noise[:, candidate]
            energies[scenario, :, candidate] = np.sort(guide + energy_noise, axis=-1)
    permutations = np.stack([random.permutation(candidates) for vertex in range(vertices)])
    indices = np.arange(vertices)
    seed_choices = np.argmax(permutations == 0, axis=1)
    frames = frames[:, indices[:, None], permutations]
    energies = energies[:, indices[:, None], permutations]
    costs = costs[indices[:, None], permutations]
    anchors = {str(vertex): int(seed_choices[vertex]) for vertex in [0, vertices // 2]}
    metadata = {'schema_version': 1, 'family': family, 'nx': nx, 'ny': ny, 'rank': 2,
                'ambient_dimension': 6, 'candidates': candidates, 'budget': int(1.50 * vertices),
                'anchors': anchors, 'scenarios': scenario_metadata, 'lambda_mean': 0.25,
                'minimum_link': 1e-6, 'branch_margin': 1e-5, 'chern_tolerance': 5e-7,
                'parameters': parameters}
    arrays = {'frames': frames, 'energies': energies, 'costs': costs, 'guide': np.array(guides),
              'target_flux': np.array(target_flux), 'seed_choices': seed_choices}
    atlas = Atlas(metadata, arrays)
    seed_score = atlas.score(seed_choices)
    if not seed_score['feasible']:
        raise ValueError(f'infeasible initial atlas: {family} {seed} {seed_score}')
    for scenario, row in enumerate(scenario_metadata):
        row['normalizer'] = seed_score['raw_loss'][scenario]
    atlas = Atlas(metadata, arrays)
    baseline = single_descent(atlas, seed_choices)
    arrays['baseline_choices'] = baseline
    metadata['baseline_objective'] = atlas.score(baseline)['objective']
    metadata['baseline_algorithm'] = 'feasible best-improvement single-site descent from seed_choices'
    return metadata, arrays


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--replace-unfrozen', action='store_true')
    arguments = parser.parse_args()
    if (ROOT / 'frozen_manifest.json').exists():
        raise SystemExit('refusing to regenerate a frozen task')
    records = []
    for split, count, first_seed in [('public', 1, 1011), ('hidden', 2, 78123)]:
        base = ROOT / ('participant/input' if split == 'public' else 'evaluator/hidden/cases')
        cases = []
        for family_index, family in enumerate(FAMILIES):
            for replicate in range(count):
                name = f'{family}_{replicate}'
                directory = base / name
                if directory.exists() and not arguments.replace_unfrozen:
                    raise SystemExit('case already exists; explicit unfrozen replacement required')
                directory.mkdir(parents=True, exist_ok=True)
                metadata, arrays = make_case(family, first_seed + family_index * 101 + replicate * 17,
                                             nx=8 + replicate, ny=8)
                metadata['case_id'] = name
                (directory / 'case.json').write_text(json.dumps(metadata, indent=2) + '\n')
                np.savez_compressed(directory / 'arrays.npz', **arrays)
                score = Atlas(metadata, arrays).score(arrays['baseline_choices'])
                cases.append({'id': name, 'family': family, 'directory': name})
                records.append({'split': split, 'case_id': name, 'baseline': score})
                print(split, name, round(score['objective'], 6), flush=True)
        (base / 'manifest.json').write_text(json.dumps({'cases': cases}, indent=2) + '\n')
    (ROOT / 'adversary' / 'baseline_calibration.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
