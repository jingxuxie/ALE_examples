import numpy as np
from scipy.linalg import eigh
from .reservoirs import fermi


def prepare(case, hamiltonian, interfaces, ends, config):
    energies, vectors = eigh(hamiltonian.toarray())
    chemical_potential = np.mean([lead['mu'] for lead in case['leads']]) if case['leads'] else case['bound_mu']
    temperature = max([lead['temperature'] for lead in case['leads']] + [case['bound_temperature']])
    weights = fermi(energies, chemical_potential, temperature)
    selected = weights > 1e-12
    return energies[selected], vectors[:, selected] * np.sqrt(weights[selected]), {'initial_states': int(np.sum(selected)), 'initialization': 'finite_eigenstates'}
