import argparse
import time

from optimize import OUTPUT, SpectralFit, assess
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares


class TransformedFit:
    def __init__(self, fit, sigma=0, cumulative=0, budget=2, binary=0):
        self.fit = fit
        self.sigma = sigma
        self.cumulative = cumulative
        self.budget = budget
        self.binary = binary

    def transform(self, values):
        shape = self.fit.target.shape + values.shape[1:]
        values = values.reshape(shape)
        if self.sigma:
            values = gaussian_filter1d(values, self.sigma, axis=2, mode='nearest')
        if self.cumulative:
            values = np.cumsum(values, axis=2) / np.sqrt(len(self.fit.energies))
        return values.reshape((-1,) + values.shape[3:])

    def residual(self, pattern):
        residual = self.transform(self.fit.residual(pattern))
        return np.concatenate([residual, [self.budget * (pattern.sum() - 24)], self.binary * pattern * (1 - pattern)])

    def jacobian(self, pattern):
        jacobian = self.transform(self.fit.jacobian(pattern))
        return np.concatenate([jacobian, np.full((1, 64), self.budget), np.diag(self.binary * (1 - 2 * pattern))])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=10)
    parser.add_argument('--starts', type=int, default=1)
    parser.add_argument('--nfev', type=int, default=180)
    parser.add_argument('--mode', default='smooth')
    parser.add_argument('--initial')
    arguments = parser.parse_args()
    random = np.random.default_rng(arguments.seed)
    for iteration in range(arguments.starts):
        fit = SpectralFit()
        if arguments.initial:
            pattern = np.clip(np.load(arguments.initial)['continuous'], 1e-8, 1 - 1e-8)
        elif iteration == 0:
            pattern = np.full(64, 0.375) + random.normal(0, 0.03, 64)
        else:
            pattern = random.uniform(0.02, 0.73, 64)
        if arguments.mode == 'smooth':
            stages = [(3, 0, 0), (1.5, 0, 0), (0.6, 0, 0), (0, 0, 0)]
        elif arguments.mode == 'cdf':
            stages = [(0, 1, 0), (1, 0, 0), (0, 0, 0)]
        elif arguments.mode == 'binary':
            stages = [(1.5, 0, 0), (0.6, 0, 1), (0, 0, 2), (0, 0, 0)]
        else:
            stages = [(0, 0, 1), (0, 0, 3), (0, 0, 0)]
        for stage, (sigma, cumulative, binary) in enumerate(stages):
            transformed = TransformedFit(fit, sigma=sigma, cumulative=cumulative, binary=binary)
            start = time.monotonic()
            result = least_squares(transformed.residual, np.clip(pattern, 1e-9, 1 - 1e-9), jac=transformed.jacobian, bounds=(0, 1), max_nfev=arguments.nfev, ftol=1e-7, xtol=1e-7, gtol=1e-7)
            pattern = result.x
            label = f'{arguments.mode}_{arguments.seed}_{iteration}_{stage}'
            print(label, 'nfev', result.nfev, 'time', time.monotonic() - start, 'cost', np.sqrt(np.mean(fit.residual(pattern) ** 2)), 'sum', pattern.sum(), 'binary distance', np.mean(np.minimum(pattern, 1 - pattern)), flush=True)
            assess(fit, pattern, label)


if __name__ == '__main__':
    main()
