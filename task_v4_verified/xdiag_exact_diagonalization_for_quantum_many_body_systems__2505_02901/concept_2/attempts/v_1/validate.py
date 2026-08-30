import os

for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import expm


def main():
    start = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--pulse', type=Path, required=True)
    parser.add_argument('--report', type=Path, default=Path('validation.json'))
    arguments = parser.parse_args()
    specification = json.loads((arguments.input / 'spec.json').read_text())
    model = json.loads((arguments.input / 'model.json').read_text())
    payload = json.loads(arguments.pulse.read_text())
    assert type(payload) is dict and set(payload) == {'schema_version', 'amplitudes'}
    assert type(payload['schema_version']) is int and payload['schema_version'] == 1
    assert type(payload['amplitudes']) is list and len(payload['amplitudes']) == 24
    assert all(type(row) is list and len(row) == 3 and all(type(value) in (float, int) for value in row) for row in payload['amplitudes'])
    assert arguments.pulse.stat().st_size <= specification['submission_max_bytes']
    amplitudes = np.asarray(payload['amplitudes'], dtype=float)
    assert np.all(np.isfinite(amplitudes))
    sites = model['sites']
    basis = [state for state in range(1 << sites) if bin(state).count('1') == model['up_spins']]
    indices = {state: index for index, state in enumerate(basis)}
    dimension = len(basis)
    drifts = np.zeros((4, dimension, dimension), dtype=complex)
    controls = np.zeros((3, dimension, dimension), dtype=complex)
    for column, state in enumerate(basis):
        spins = np.asarray([.5 if state & (1 << site) else -.5 for site in range(sites)])
        controls[0, column, column] = np.dot(model['staggered_profile'], spins)
        for site in range(sites):
            neighbor = (site + 1) % sites
            controls[1, column, column] += model['bond_profile'][site] * model['bond_control_anisotropy'] * spins[site] * spins[neighbor]
            if spins[site] != spins[neighbor]:
                row = indices[state ^ (1 << site) ^ (1 << neighbor)]
                controls[1, row, column] += .5 * model['bond_profile'][site]
                controls[2, row, column] += (-.5j if spins[site] > 0 else .5j) * model['current_profile'][site]
        for member, calibration in enumerate(model['calibrations']):
            field = np.asarray(model['static_field']) + calibration['field_offset'] * np.asarray(model['field_error_profile'])
            drifts[member, column, column] += np.dot(field, spins)
            for distance, exchange, anisotropy in [(1, model['nearest_exchange'], model['nearest_anisotropy'] + calibration['anisotropy_shift']),
                                                    (2, model['next_exchange'] * (1 + calibration['next_exchange_fraction']), model['next_anisotropy'])]:
                for site in range(sites):
                    neighbor = (site + distance) % sites
                    drifts[member, column, column] += exchange * anisotropy * spins[site] * spins[neighbor]
                    if spins[site] != spins[neighbor]:
                        row = indices[state ^ (1 << site) ^ (1 << neighbor)]
                        drifts[member, row, column] += exchange / 2
    initial = np.zeros((dimension, 6), dtype=complex)
    for column, state in enumerate(model['initial_bitstrings']):
        initial[indices[state], column] = 1
    with np.load(arguments.input / 'hamiltonians.npz') as archive:
        source_error = max(np.max(abs(drifts - archive['drifts'])), np.max(abs(controls - archive['controls'])), np.max(abs(initial - archive['initial'])))
    with np.load(arguments.input / 'targets.npz') as archive:
        targets = archive['targets']
    members = []
    orthonormality_error = 0.
    for member, drift in enumerate(drifts):
        actual = initial.copy()
        for row in amplitudes:
            hamiltonian = drift + np.einsum('c,cij->ij', row, controls)
            actual = expm(-1j * specification['slice_duration'] * hamiltonian) @ actual
        overlap = targets[member].conj().T @ actual
        trace = np.trace(overlap)
        aligned = np.exp(-1j * np.angle(trace)) * overlap
        hermitian = (aligned + aligned.conj().T) / 2
        floor = max(0., np.linalg.eigvalsh(hermitian)[0]) ** 2
        members.append({'name': model['calibrations'][member]['name'],
                        'isometry_fidelity': float(np.clip(abs(trace / 6) ** 2, 0, 1)),
                        'minimum_column_fidelity': float(np.clip(np.min(abs(np.diag(overlap)) ** 2), 0, 1)),
                        'superposition_floor': float(np.clip(floor, 0, 1))})
        orthonormality_error = max(orthonormality_error, np.max(abs(actual.conj().T @ actual - np.eye(6))))
    limits = np.asarray(specification['amplitude_limits'])
    jumps = np.diff(np.vstack((np.zeros((1, 3)), amplitudes, np.zeros((1, 3)))), axis=0)
    exposure = float(specification['slice_duration'] * np.sum((amplitudes / limits) ** 2))
    tolerance = specification['physical_constraint_tolerance']
    physical = bool(np.all(abs(amplitudes) <= limits + tolerance)
                    and np.all(abs(jumps) <= np.asarray(specification['adjacent_jump_limits']) + tolerance)
                    and exposure <= specification['normalized_control_exposure_limit'] + tolerance)
    mean = float(np.mean([member['isometry_fidelity'] for member in members]))
    floor = min(member['superposition_floor'] for member in members)
    column = min(member['minimum_column_fidelity'] for member in members)
    report = {'schema_valid': True, 'physical_valid': physical, 'core_score': mean, 'worst_family_score': floor,
              'minimum_column_fidelity': column, 'normalized_control_exposure': exposure,
              'maximum_amplitude_by_channel': np.max(abs(amplitudes), axis=0).tolist(),
              'maximum_jump_by_channel': np.max(abs(jumps), axis=0).tolist(), 'members': members,
              'source_matrices_maximum_error': float(source_error), 'propagated_orthonormality_error': float(orthonormality_error),
              'passed': physical and mean >= specification['mean_isometry_fidelity_min'] and floor >= specification['worst_superposition_fidelity_min'] and column >= specification['minimum_column_fidelity_min'],
              'validation_seconds': time.monotonic() - start}
    arguments.report.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
