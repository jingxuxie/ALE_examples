import copy
import json
from pathlib import Path
import sys

import numpy as np
from scipy.linalg import expm

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'solution/v_01/output/workspace'))
from oqs.baths import spectrum
from oqs.engine import solve
from oqs.spectral import redfield_generator
from generate_cases import make_case, pure, thermal, waveform, cases


def model(metadata, arrays):
    return dict(metadata, **arrays)


def main():
    options = {'engine': 'microscopic', 'rtol': 1e-10, 'atol': 1e-12, 'samples': 256, 'harmonics': 60}
    checks = {}
    lowering = np.array([[0, 1], [0, 0]], dtype=complex)
    population = np.diag([0, 1]).astype(complex)
    coupling = lowering + lowering.conj().T
    times = np.array([0.31, 0.47, 1.02, 2.57, 4.13])
    decay = model(*make_case('analytic', 'limit', 'lindblad', population,
                  pure([0, 1]), [population], times, c_ops=[lowering],
                  c_coeffs=[waveform('constant', value=[0.3, 0.4])]))
    result = solve(decay, options)
    checks['complex_collapse_amplitude'] = float(np.max(np.abs(result['expectations'][:, 0] - np.exp(-0.25 * (times - times[0])))))
    spectral = model(*make_case('thermal', 'limit', 'redfield', population,
                     pure([0, 1]), [population], times, a_ops=[coupling], baths=[thermal(0.23, 0)], secular=True))
    result = solve(spectral, options)
    checks['redfield_emission_sign_and_normalization'] = float(np.max(np.abs(result['expectations'][:, 0] - np.exp(-float(spectrum(spectral['baths'][0], 1)) * (times - times[0])))))
    floquet = copy.deepcopy(spectral)
    floquet.update(physics='floquet', period=0.73)
    periodic = solve(floquet, options)
    checks['static_floquet_equals_secular_redfield'] = float(np.max(np.abs(periodic['states'] - result['states'])))
    driven = model(*next(cases(False)))
    driven['baths'] = []
    driven['a_ops'] = np.empty((0, 2, 2), dtype=complex)
    driven['times'] = np.array([0.217, 0.63, 1.05, 1.887, 7.335])
    periodic = solve(driven, options)
    driven['physics'] = 'lindblad'
    direct = solve(driven, options)
    checks['driven_micromotion_vs_direct_integration'] = float(np.max(np.abs(periodic['states'] - direct['states'])))
    dark = model(*list(cases(False))[2])
    dark['rho0'] = pure([0, 1, -1])
    result = solve(dark, options)
    checks['collective_dark_state'] = float(np.max(np.abs(result['states'] - dark['rho0'])))

    coupled = model(*list(cases(True))[3])
    generator, basis = redfield_generator(coupled)
    energies = np.linalg.eigvalsh(coupled['H0'])
    dimension = len(energies)
    independent = np.zeros_like(generator)
    for row in range(dimension):
        for column in range(dimension):
            index = row + dimension * column
            independent[index, index] = -1j * (energies[row] - energies[column])
            for source_row in range(dimension):
                for source_column in range(dimension):
                    source = source_row + dimension * source_column
                    for operator, bath in zip(coupled['a_ops'], coupled['baths']):
                        transformed = basis.conj().T @ operator @ basis
                        term = transformed[row, source_row] * transformed[source_column, column] * (
                            spectrum(bath, energies[source_row] - energies[row]) +
                            spectrum(bath, energies[source_column] - energies[column])) / 2
                        if column == source_column:
                            term -= sum(transformed[row, inner] * transformed[inner, source_row] *
                                        spectrum(bath, energies[source_row] - energies[inner]) / 2 for inner in range(dimension))
                        if row == source_row:
                            term -= sum(transformed[source_column, inner] * transformed[inner, column] *
                                        spectrum(bath, energies[source_column] - energies[inner]) / 2 for inner in range(dimension))
                        independent[index, source] += term
    checks['redfield_tensor_independent_index_contraction'] = float(np.max(np.abs(generator - independent)))

    gate = copy.deepcopy(decay)
    gate['c_ops'] = np.empty((0, 2, 2), dtype=complex)
    gate.update(c_coeffs=[], process=True)
    gate['H0'] = population + 0.3 * coupling
    result = solve(gate, options)
    unitary = expm(-1j * gate['H0'] * (times[-1] - times[0]))
    checks['column_vectorized_unitary_channel'] = float(np.max(np.abs(result['channel'] - np.kron(unitary.conj(), unitary))))
    maximally_entangled = unitary.T.reshape(-1)
    checks['input_first_unnormalized_choi'] = float(np.max(np.abs(result['choi'] - np.outer(maximally_entangled, maximally_entangled.conj()))))
    if max(checks.values()) >= 2e-8:
        raise AssertionError(checks)
    destination = ROOT / 'screening/v_01/reference_independent_checks.json'
    destination.write_text(json.dumps({'passed': True, 'errors': checks}, indent=2))
    print(destination.read_text())


if __name__ == '__main__':
    main()
