import numpy as np
from scipy.special import expit


def fermi(energies, chemical_potential, temperature):
    if temperature == 0:
        return (np.asarray(energies) < chemical_potential).astype(float)
    return expit((chemical_potential - np.asarray(energies)) / temperature)


def surface(energy, cell, hop, eta=1e-9):
    size = len(cell)
    spectral = complex(energy, eta) * np.eye(size)
    bulk = cell.copy()
    edge = cell.copy()
    outward = hop.conj().T.copy()
    inward = hop.copy()
    for iteration in range(120):
        inverse = np.linalg.inv(spectral - bulk)
        addition = outward @ inverse @ inward
        reverse = inward @ inverse @ outward
        edge = edge + addition
        bulk = bulk + addition + reverse
        outward, inward = outward @ inverse @ outward, inward @ inverse @ inward
        if np.linalg.norm(outward) + np.linalg.norm(inward) < 1e-13:
            break
    return np.linalg.inv(spectral - edge)


def band_samples(cell, hop, count=257):
    momenta = np.linspace(-np.pi, np.pi, count)
    values = [np.linalg.eigvalsh(cell + np.exp(-1j * momentum) * hop + np.exp(1j * momentum) * hop.conj().T) for momentum in momenta]
    return momenta, np.asarray(values)
