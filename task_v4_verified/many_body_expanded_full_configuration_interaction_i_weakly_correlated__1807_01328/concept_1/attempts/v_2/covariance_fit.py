import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np
from scipy.optimize import least_squares
from response_fit import ORDERS, MASKS, LEFT, RIGHT

class CovarianceFit:
    def __init__(self, energies, masks, beta=0.0, orbital=None):
        self.masks = np.array(masks)
        self.observed = energies[self.masks]
        self.single = np.maximum(-energies[1 << np.arange(8)], 1e-15)
        self.scale = max(np.max(self.single), 1e-5)
        self.beta = beta
        self.denominator = np.array(orbital)[3:] + 0.22 if orbital is not None else np.full(8, 1.7)
        self.source = np.sqrt(self.single * (1 + beta * self.single / self.denominator))
        self.last_parameters = None
        contained = (self.masks[:, None] & self.masks[None, :]) == self.masks[None, :]
        self.transform = np.eye(len(self.masks))
        for row, mask in enumerate(self.masks):
            if ORDERS[mask] == 3:
                self.transform[row, (ORDERS[self.masks] == 2) & contained[row]] = -1
        self.transform[ORDERS[self.masks] == 2] *= 0.25

    def evaluate(self, parameters, masks, energy=None, jacobian=False):
        hopping = 0.8 * np.tanh(parameters[:28])
        correlation = np.tanh(parameters[28:])
        active = MASKS[masks]
        edge_active = active[:, LEFT] * active[:, RIGHT]
        matrices = np.broadcast_to(np.eye(8), (len(masks), 8, 8)).copy()
        matrices[:, LEFT, RIGHT] = -hopping * edge_active
        matrices[:, RIGHT, LEFT] = -hopping * edge_active
        covariance = np.diag(self.source ** 2)
        covariance[LEFT, RIGHT] = self.source[LEFT] * self.source[RIGHT] * correlation
        covariance[RIGHT, LEFT] = covariance[LEFT, RIGHT]
        selected_cov = covariance[None] * active[:, :, None] * active[:, None, :]
        diagonal = np.arange(8)
        if energy is not None:
            matrices[:, diagonal, diagonal] -= self.beta * energy[:, None] / self.denominator
        inverse = np.linalg.inv(matrices)
        prediction = -np.sum(inverse * selected_cov, axis=(1, 2))
        if not jacobian:
            return prediction
        intermediate = inverse @ selected_cov @ inverse
        edge_gradient = -2 * intermediate[:, LEFT, RIGHT] * 0.8 * (1-np.tanh(parameters[:28])**2)
        covariance_gradient = -2 * inverse[:, LEFT, RIGHT] * self.source[LEFT] * self.source[RIGHT] * (1-correlation**2) * edge_active
        gradient = np.concatenate((edge_gradient, covariance_gradient), axis=1)
        return prediction, gradient

    def residual(self, parameters):
        prediction, gradient = self.evaluate(parameters, self.masks, self.observed, True)
        values = self.transform @ ((prediction - self.observed) / self.scale)
        self.last_gradient = self.transform @ (gradient / self.scale)
        correlation = np.eye(8)
        correlation[LEFT, RIGHT] = np.tanh(parameters[28:])
        correlation[RIGHT, LEFT] = correlation[LEFT, RIGHT]
        eigenvalues, eigenvectors = np.linalg.eigh(correlation)
        eig_gradient = 0.03 * np.concatenate((np.zeros((8, 28)), 2 * eigenvectors[LEFT].T * eigenvectors[RIGHT].T * (1-np.tanh(parameters[28:])**2)), axis=1)
        eig_gradient[eigenvalues >= 0] = 0
        values = np.concatenate((values, 0.03 * np.minimum(eigenvalues, 0), 1e-5 * parameters))
        self.last_gradient = np.concatenate((self.last_gradient, eig_gradient, 1e-5 * np.eye(56)), axis=0)
        self.last_parameters = parameters.copy()
        return values

    def jacobian(self, parameters):
        if self.last_parameters is None or np.any(parameters != self.last_parameters):
            self.residual(parameters)
        return self.last_gradient

    def fit(self, starts=3, max_nfev=200, seed=127, initial=None):
        generator = np.random.default_rng(seed)
        best = None
        self.fits = []
        pair_values = np.zeros(28)
        lookup = dict(zip(self.masks, self.observed))
        for index, (left, right) in enumerate(zip(LEFT, RIGHT)):
            pair_values[index] = -lookup[(1 << left) | (1 << right)]
        for start in range(starts):
            hopping = generator.normal(0, 0.08 + 0.06*start, 28)
            hopping = np.clip(hopping, -0.5, 0.5)
            covariance = (pair_values * (1-hopping**2) - self.single[LEFT] - self.single[RIGHT]) / (2 * hopping * self.source[LEFT] * self.source[RIGHT])
            covariance = np.clip(covariance, -0.95, 0.95)
            parameters = np.concatenate((np.arctanh(hopping / .8), np.arctanh(covariance))) if initial is None or start else initial
            fitted = least_squares(self.residual, parameters, jac=self.jacobian, method='lm', max_nfev=max_nfev, ftol=1e-8, xtol=1e-8, gtol=1e-8)
            matrix = np.eye(8)
            matrix[LEFT, RIGHT] = -0.8*np.tanh(fitted.x[:28])
            matrix[RIGHT, LEFT] = matrix[LEFT, RIGHT]
            minimum = np.linalg.eigvalsh(matrix)[0]
            score = np.linalg.norm(fitted.fun) + max(0.08-minimum, 0) * 2
            self.fits.append((score, fitted, minimum))
            if best is None or score < best[0]:
                best = self.fits[-1]
        self.parameters = best[1].x
        self.score = best[0]
        self.minimum = best[2]
        prediction = self.evaluate(self.parameters, np.arange(256))
        if self.beta:
            for iteration in range(8):
                prediction = self.evaluate(self.parameters, np.arange(256), prediction)
        return prediction

if __name__ == '__main__':
    import json
    import sys
    import time
    ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
    sys.path.insert(0, ASSETS+'/workspace')
    from pair_model import increments
    energies = np.load(ASSETS+'/input/practice.npz')['energies']
    models = json.load(open(ASSETS+'/input/practice_models.json'))
    all_masks = np.arange(256)
    subset = (all_masks[:, None] & all_masks[None, :]) == all_masks[None, :]
    triples = np.flatnonzero(ORDERS == 3)
    quadruples = np.flatnonzero(ORDERS == 4)
    predictions = []
    corrected = []
    full_tables = []
    start_time = time.process_time()
    for index, table in enumerate(energies):
        actual = increments(table)
        magnitudes = np.array([np.sort(np.abs(actual[triples[subset[mask, triples]]])) for mask in quadruples])
        score = np.sqrt(magnitudes[:, -1] * magnitudes[:, -2])
        selected = quadruples[np.argsort(-score)[:26]]
        fit = CovarianceFit(table, np.concatenate((np.flatnonzero((ORDERS >= 2) & (ORDERS <= 3)), selected)), beta=0.4, orbital=models[index]['orbital_energy'])
        predicted = fit.fit(starts=2, max_nfev=200)
        full_tables.append(predicted)
        predictions.append(predicted[-1])
        delta = increments(table-predicted)
        corrected.append(predicted[-1] + delta[ORDERS <= 3].sum() + delta[selected].sum())
        print(index, models[index]['family'], 'fit', round(fit.score, 7), 'eigen', round(fit.minimum, 3), 'direct', round((predicted[-1]-table[-1])*1e6, 2), 'corrected', round((corrected[-1]-table[-1])*1e6, 2), 'cpu', round(time.process_time()-start_time, 2), flush=True)
    np.savez('covariance_predictions.npz', predicted=np.array(full_tables))
    for label, prediction in [('direct', predictions), ('corrected', corrected)]:
        error = (np.array(prediction)-energies[:,-1])*1e6
        print(label, np.sqrt(np.mean(error**2)), flush=True)
