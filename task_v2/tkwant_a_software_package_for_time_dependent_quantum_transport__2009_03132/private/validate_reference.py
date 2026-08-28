import importlib.util
import json
import sys
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
from scipy.integrate import solve_ivp


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / 'concept_01'
sys.path.insert(0, str(CONCEPT / 'solution' / 'v_01' / 'workspace'))
from transport.model import extend
from transport.reservoirs import fermi
from transport.spectral import prepare
from transport.simulate import CONFIGS, simulate
from transport.protocols import drive_entries, perturbation
from transport.observables import measure


def main():
    cases = json.loads((CONCEPT / 'participant/v_01/input/development.json').read_text())['cases']
    checks = []
    for index in [0, 4]:
        case = dict(cases[index])
        case['times'] = [0., .3]
        hamiltonian, interfaces, ends = extend(case, 85)
        config = dict(CONFIGS['production'])
        energies, state, metadata = prepare(case, hamiltonian, interfaces, ends, config)
        spectral_density = np.sum(abs(state[:len(case['hamiltonian']['real'])]) ** 2, axis=1)
        eigenvalues, vectors = eigh(hamiltonian.toarray())
        weights = fermi(eigenvalues, case['leads'][0]['mu'], case['leads'][0]['temperature'])
        finite_density = np.sum(abs(vectors[:len(spectral_density)]) ** 2 * weights, axis=1)
        discrepancy = float(np.max(abs(spectral_density - finite_density)))
        checks.append(dict(check='equilibrium_spectral_vs_finite_eigensystem', case=case['id'], error=discrepancy, passed=discrepancy < 2e-6, states=metadata))
    case = dict(cases[0])
    case['times'] = np.linspace(0, 8, 9).tolist()
    result, metadata = simulate(case)
    hamiltonian, interfaces, ends = extend(case, 65)
    eigenvalues, vectors = eigh(hamiltonian.toarray())
    weights = fermi(eigenvalues, case['leads'][0]['mu'], case['leads'][0]['temperature'])
    initial = vectors * np.sqrt(weights)
    entries = drive_entries(case, interfaces)
    def rhs(time, state):
        wavefunctions = state.reshape(initial.shape)
        dynamic = hamiltonian + perturbation(time, entries, hamiltonian.shape[0])
        return (-1j * (dynamic @ wavefunctions)).ravel()
    solved = solve_ivp(rhs, (0, 8), initial.ravel(), t_eval=case['times'], method='DOP853', rtol=2e-10, atol=2e-11)
    densities, currents = [], []
    for time, values in zip(solved.t, solved.y.T):
        density, current = measure(case, hamiltonian + perturbation(time, entries, hamiltonian.shape[0]), values.reshape(initial.shape))
        densities.append(density)
        currents.append(current)
    discrepancy = max(float(np.max(abs(np.asarray(densities) - result['density']))), float(np.max(abs(np.asarray(currents) - result['current']))))
    checks.append(dict(check='transient_vs_independent_finite_DOP853', error=discrepancy, passed=discrepancy < 2e-6))
    stationary = dict(cases[2], drives=[], times=[0., 10., 20.])
    result, metadata = simulate(stationary)
    discrepancy = max(float(np.max(abs(result['density'] - result['density'][0]))), float(np.max(abs(result['current'] - result['current'][0]))))
    checks.append(dict(check='nonequilibrium_stationarity', error=discrepancy, passed=discrepancy < 1e-12))
    path = CONCEPT / 'screening/reference_independent_checks.json'
    path.write_text(json.dumps({'checks': checks, 'all_pass': all(item['passed'] for item in checks)}, indent=2))
    print(path.read_text())


if __name__ == '__main__':
    main()
