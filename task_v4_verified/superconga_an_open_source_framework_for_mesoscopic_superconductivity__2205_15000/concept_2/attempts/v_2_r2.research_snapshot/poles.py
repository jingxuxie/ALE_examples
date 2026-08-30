import numpy as np
from scipy.linalg import eigvals, svd

from optimize import Inverse, OUTPUT


def aaa(grid, values, tolerance=1e-10, maximum=28):
    support = []
    approximant = np.tile(values.mean(axis=0), (len(grid), 1))
    for iteration in range(maximum):
        residual = np.sqrt(np.sum(np.abs(values - approximant) ** 2, axis=1))
        residual[support] = 0
        chosen = np.argmax(residual)
        support.append(chosen)
        remaining = np.setdiff1d(np.arange(len(grid)), support)
        cauchy = 1 / (grid[remaining, None] - grid[None, support])
        loewner = (values[remaining, None, :] - values[None, support, :]) * cauchy[:, :, None]
        loewner = loewner.transpose(0, 2, 1).reshape(-1, len(support))
        unused, singular_values, right = svd(loewner, full_matrices=False)
        weights = right[-1].conj()
        approximant[remaining] = (cauchy @ (weights[:, None] * values[support])) / (cauchy @ weights)[:, None]
        approximant[support] = values[support]
        error = np.max(np.abs(values - approximant))
        if error < tolerance:
            break
    support_grid = grid[support]
    pencil = np.zeros((len(support) + 1, len(support) + 1), dtype=complex)
    pencil[0, 1:] = weights
    pencil[1:, 0] = 1
    pencil[1:, 1:] = np.diag(support_grid)
    metric = np.eye(len(support) + 1)
    metric[0, 0] = 0
    poles = eigvals(pencil, metric)
    poles = poles[np.isfinite(poles)]
    residues = []
    for pole in poles:
        numerator = np.sum(weights[:, None] * values[support] / (pole - support_grid)[:, None], axis=0)
        derivative = -np.sum(weights / (pole - support_grid) ** 2)
        residues.append(numerator / derivative)
    return poles, np.asarray(residues), error


def main():
    inverse = Inverse(stride=1)
    for condition in range(3):
        target = inverse.target[condition].T / inverse.scales[condition, :, 0]
        poles, residues, error = aaa(inverse.energies, target)
        selected = np.flatnonzero(poles.imag > 0)
        print('CONDITION', condition, 'error', error)
        for index in selected[np.argsort(poles[selected].real)]:
            print(poles[index], 'residues', np.round(np.abs(residues[index]), 8))
        np.savez(OUTPUT / f'poles_{condition}.npz', poles=poles, residues=residues, error=error)


if __name__ == '__main__':
    main()
