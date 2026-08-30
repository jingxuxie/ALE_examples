import numpy as np

from invert import OUT


def broaden(model, eta):
    fitted = np.load(OUT / 'spectral_fit.npz')
    values = []
    for condition in model.conditions:
        positive = fitted['poles'][condition]
        poles = np.concatenate([-positive[::-1], positive])
        coefficients = fitted['coefficients'][condition]
        spectral = eta / np.pi / ((model.energies[:, None] - poles[None, :]) ** 2 + eta ** 2)
        output = spectral @ coefficients[:20]
        sample_energies = np.linspace(-.3, .3, 5)
        original = sample_energies + .01j
        powers = np.arange(1, 6)
        mapping = -np.imag(original[:, None] ** powers[None, :]) / np.pi
        background = np.polynomial.polynomial.polyval(sample_energies, coefficients[20:]).T
        analytic = np.linalg.solve(mapping, background)
        corrected = -np.imag((model.energies[:, None] + 1j * eta) ** powers[None, :]) / np.pi @ analytic
        values.append((output + corrected).T)
    model.target = np.asarray(values)
    model.scales = np.maximum(np.sqrt(np.mean(model.target ** 2, axis=2, keepdims=True)), .02)
    model.config['broadening'] = eta
