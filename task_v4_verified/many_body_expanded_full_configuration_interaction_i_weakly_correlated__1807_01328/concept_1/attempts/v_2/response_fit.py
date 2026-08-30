import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np
from scipy.optimize import least_squares

ORDERS = np.array([mask.bit_count() for mask in range(256)])
MASKS = ((np.arange(256)[:, None] >> np.arange(8)) & 1).astype(float)
LEFT, RIGHT = np.triu_indices(8, 1)

class ResponseFit:
    def __init__(self, energies, masks, rank=3, regularization=0.0):
        self.rank = rank
        self.masks = np.array(masks)
        self.observed = energies[self.masks]
        self.single = np.sqrt(np.maximum(-energies[1 << np.arange(8)], 1e-15))
        self.scale = max(np.max(self.single) ** 2, 1e-5)
        self.regularization = regularization
        self.last_parameters = None

    def evaluate(self, parameters, masks, jacobian=False):
        sources = parameters[28:].reshape(8, self.rank)
        norms = np.maximum(np.linalg.norm(sources, axis=1), 1e-10)
        unit = sources / norms[:, None]
        source = unit * self.single[:, None]
        active = MASKS[masks]
        matrices = np.broadcast_to(np.eye(8), (len(masks), 8, 8)).copy()
        edges = -parameters[:28] * active[:, LEFT] * active[:, RIGHT]
        matrices[:, LEFT, RIGHT] = edges
        matrices[:, RIGHT, LEFT] = edges
        selected_sources = source[None] * active[:, :, None]
        vectors = np.linalg.solve(matrices, selected_sources)
        prediction = -np.sum(selected_sources * vectors, axis=(1, 2))
        if not jacobian:
            return prediction
        edge_gradient = -2 * np.sum(vectors[:, LEFT] * vectors[:, RIGHT], axis=2)
        projection = vectors - np.sum(vectors * unit[None], axis=2)[:, :, None] * unit[None]
        source_gradient = -2 * projection * (self.single / norms)[None, :, None]
        gradient = np.concatenate((edge_gradient, source_gradient.reshape(len(masks), -1)), axis=1)
        return prediction, gradient

    def residual(self, parameters):
        prediction, gradient = self.evaluate(parameters, self.masks, True)
        self.last_parameters = parameters.copy()
        self.last_gradient = gradient / self.scale
        values = (prediction - self.observed) / self.scale
        if self.regularization:
            values = np.concatenate((values, self.regularization * parameters[:28]))
            self.last_gradient = np.concatenate((self.last_gradient, np.pad(np.eye(28) * self.regularization, ((0, 0), (0, 8*self.rank)))), axis=0)
        return values

    def jacobian(self, parameters):
        if self.last_parameters is None or np.any(parameters != self.last_parameters):
            self.residual(parameters)
        return self.last_gradient

    def fit(self, starts=3, max_nfev=150, seed=117):
        generator = np.random.default_rng(seed)
        best = None
        pair_mask = (1 << LEFT) | (1 << RIGHT)
        pair_delta = self.observed[0] if False else None
        self.fits = []
        for start in range(starts):
            sources = generator.normal(size=(8, self.rank))
            sources[:, 0] += 1.8 if start == 0 else 0.0
            initial = np.concatenate((generator.normal(0, 0.035, 28), sources.ravel()))
            fitted = least_squares(self.residual, initial, jac=self.jacobian, method='lm', max_nfev=max_nfev, ftol=1e-9, xtol=1e-9, gtol=1e-9)
            matrix = np.eye(8)
            matrix[LEFT, RIGHT] = -fitted.x[:28]
            matrix[RIGHT, LEFT] = -fitted.x[:28]
            minimum = np.linalg.eigvalsh(matrix)[0]
            score = np.linalg.norm(fitted.fun) + max(0.05-minimum, 0) * 10
            self.fits.append((score, fitted, minimum))
            if best is None or score < best[0]:
                best = self.fits[-1]
        self.parameters = best[1].x
        self.score = best[0]
        self.minimum = best[2]
        return self.evaluate(self.parameters, np.arange(256))

if __name__ == '__main__':
    import json
    import sys
    import time
    ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
    sys.path.insert(0, ASSETS+'/workspace')
    from pair_model import increments
    energies = np.load(ASSETS+'/input/practice.npz')['energies']
    families = np.array([model['family'] for model in json.load(open(ASSETS+'/input/practice_models.json'))])
    all_masks = np.arange(256)
    subset = (all_masks[:, None] & all_masks[None, :]) == all_masks[None, :]
    triples = np.flatnonzero(ORDERS == 3)
    quadruples = np.flatnonzero(ORDERS == 4)
    predictions = []
    corrected = []
    full_tables = []
    start_time = time.process_time()
    for index, table in enumerate(energies):
        fit = ResponseFit(table, np.flatnonzero((ORDERS >= 2) & (ORDERS <= 3)), regularization=1e-6)
        predicted = fit.fit(starts=3, max_nfev=180)
        full_tables.append(predicted)
        predictions.append(predicted[-1])
        delta = increments(table-predicted)
        actual = increments(table)
        score = np.abs(actual[triples]) @ subset[quadruples][:, triples].T
        selected = quadruples[np.argsort(-score)[:26]]
        corrected.append(predicted[-1] + delta[ORDERS <= 3].sum() + delta[selected].sum())
        print(index, families[index], 'fit', round(fit.score, 7), 'eigen', round(fit.minimum, 3), 'direct', round((predicted[-1]-table[-1])*1e6, 2), 'corrected', round((corrected[-1]-table[-1])*1e6, 2), 'cpu', round(time.process_time()-start_time, 2), flush=True)
    np.savez('response_predictions.npz', predicted=np.array(full_tables))
    for label, prediction in [('direct', predictions), ('corrected', corrected)]:
        error = (np.array(prediction)-energies[:,-1])*1e6
        print(label, np.sqrt(np.mean(error**2)), {family: np.sqrt(np.mean(error[families == family]**2)) for family in set(families)}, flush=True)
