import time

import numpy as np
from scipy.optimize import least_squares

from features import FeatureModel
from invert import OUT, save_binary


def main():
    model = FeatureModel()
    rng = np.random.default_rng(17)
    pattern = np.clip(.375 + rng.normal(0, .15, 144), .001, .999)
    coefficient = .15
    latent = pattern / (coefficient + (1 - coefficient) * pattern)
    started = time.time()
    for stage, binary in enumerate([0, .1, 1, 10, 100]):
        calls = [0]
        def convert(values):
            denominator = 1 - (1 - coefficient) * values
            physical = coefficient * values / denominator
            chain = coefficient / denominator ** 2
            return physical, chain
        def objective(values):
            physical, chain = convert(values)
            residual, derivative = model.objective(physical, binary=binary, budget=300)
            calls[0] += 1
            if calls[0] % 20 == 1:
                print('ITER', stage, calls[0], np.linalg.norm(residual), 'gray', np.mean(physical * (1 - physical)), 'sum', physical.sum(), 'time', round(time.time() - started, 1), flush=True)
            return residual
        def jacobian(values):
            physical, chain = convert(values)
            return model.objective(physical, binary=binary, budget=300)[1] * chain[None, :]
        result = least_squares(objective, latent, jac=jacobian, bounds=(0, 1), max_nfev=300 if stage == 0 else 150, ftol=1e-7, xtol=1e-8, gtol=1e-7)
        latent = result.x
        pattern = convert(latent)[0]
        np.save(OUT / f'reparam_{stage}.npy', pattern)
        print('STAGE', stage, np.linalg.norm(result.fun), flush=True)
        save_binary(model, pattern, f'reparam_{stage}')


if __name__ == '__main__':
    main()
