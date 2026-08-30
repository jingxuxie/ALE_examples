import numpy as np
from scipy.optimize import least_squares
from invert import Model, OUT


def fit():
    model = Model(stride=1)
    energies = model.energies
    starts = [[.026, .079, .095, .130, .180, .211, .264, .291, .34, .40],
              [.03, .077, .087, .115, .174, .199, .244, .290, .34, .40],
              [.025, .078, .102, .140, .185, .219, .277, .292, .35, .40]]
    all_poles = []
    all_weights = []
    full_poles = []
    full_coefficients = []
    for condition in range(3):
        target = model.target[condition].T
        scales = model.scales[condition, :, 0]
        def basis(positive):
            poles = np.concatenate([-positive[::-1], positive])
            lorentz = .01 / np.pi / ((energies[:, None] - poles[None, :]) ** 2 + .01 ** 2)
            return np.column_stack([lorentz, np.ones_like(energies), energies, energies ** 2, energies ** 3, energies ** 4])
        def objective(positive):
            design = basis(positive)
            coefficients = np.linalg.lstsq(design, target, rcond=1e-12)[0]
            return ((design @ coefficients - target) / scales).flatten()
        initial = np.array(starts[condition])
        lower = initial.copy() - .012
        upper = initial.copy() + .012
        lower[-2:] = [.315, .36]
        upper[-2:] = [.40, .8]
        result = least_squares(objective, initial, bounds=(lower, upper), xtol=1e-13, ftol=1e-13, gtol=1e-13, max_nfev=500)
        design = basis(result.x)
        coefficients = np.linalg.lstsq(design, target, rcond=1e-12)[0]
        weights = np.concatenate([coefficients[2:10], coefficients[10:18]], axis=0).T
        all_poles.append(result.x[:9])
        all_weights.append(weights)
        full_poles.append(result.x)
        full_coefficients.append(coefficients)
        print('POLES', condition, np.linalg.norm(result.fun) / np.sqrt(result.fun.size), result.x, 'minweight', weights.min(), flush=True)
        print('WEIGHTS', np.round(weights, 5), flush=True)
    np.savez(OUT / 'poles.npz', poles=np.asarray(all_poles), weights=np.asarray(all_weights))
    np.savez(OUT / 'spectral_fit.npz', poles=np.asarray(full_poles), coefficients=np.asarray(full_coefficients))


if __name__ == '__main__':
    fit()
