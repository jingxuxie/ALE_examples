import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
import sys
ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
sys.path.insert(0, ASSETS+'/workspace')
from pair_model import increments

ORDERS = np.array([mask.bit_count() for mask in range(256)])
SUBSET = (np.arange(256)[:, None] & np.arange(256)[None, :]) == np.arange(256)[None, :]
GROUPS = [np.flatnonzero(ORDERS == order) for order in range(9)]
triplets = np.array([GROUPS[3][SUBSET[mask, GROUPS[3]]] for mask in GROUPS[4]])
data = np.load(ASSETS+'/input/practice.npz')['energies']
terms = np.array([increments(table) for table in data])
for kind in ['sum', 'second', 'third', 'fourth', 'sqrt12', 'geometric', 'rmslow']:
    for nfives in [0, 1, 2, 4, 6]:
        estimates = []
        for row in terms:
            magnitudes = np.sort(abs(row[triplets]), axis=1)[:, ::-1] + 1e-20
            if kind == 'sum':
                score = magnitudes.sum(axis=1)
            elif kind == 'second':
                score = magnitudes[:, 1]
            elif kind == 'third':
                score = magnitudes[:, 2]
            elif kind == 'fourth':
                score = magnitudes[:, 3]
            elif kind == 'sqrt12':
                score = np.sqrt(magnitudes[:, 0] * magnitudes[:, 1])
            elif kind == 'geometric':
                score = np.prod(magnitudes, axis=1) ** .25
            else:
                score = np.sqrt((magnitudes[:, 1:] ** 2).sum(axis=1))
            weights = np.zeros(256)
            weights[GROUPS[4]] = score ** 2
            for order in range(5, 9):
                weights[GROUPS[order]] = (SUBSET[GROUPS[order]][:, GROUPS[4]] @ weights[GROUPS[4]]) * (0.03 ** (order-4))
            high = np.flatnonzero(ORDERS >= 4)
            covariance = np.diag(weights[high])
            selector = SUBSET[:, high].astype(float)
            residual = np.zeros(len(high))
            chosen = []
            for stage in range(nfives + 26 - 4*nfives):
                candidates = GROUPS[5] if stage < nfives else GROUPS[4]
                candidates = np.array([mask for mask in candidates if mask not in chosen])
                observation_cov = selector[candidates] @ covariance
                target_cov = observation_cov.sum(axis=1)
                variance = np.sum(observation_cov * selector[candidates], axis=1)
                utility = target_cov ** 2 / np.maximum(variance, 1e-30)
                utility[variance < 1e-25] = -1
                best = int(np.argmax(utility))
                mask = candidates[best]
                chosen.append(mask)
                innovation = row[high] @ selector[mask] - residual @ selector[mask]
                direction = observation_cov[best]
                residual += direction * innovation / max(variance[best], 1e-100)
                covariance -= np.outer(direction, direction) / max(variance[best], 1e-100)
            estimates.append(row[ORDERS <= 3].sum() + residual.sum())
        error = (np.array(estimates)-data[:, -1])*1e6
        print(kind, nfives, 'rmse', round(np.sqrt(np.mean(error**2)), 3), 'max', round(max(abs(error)), 2), 'hard', np.round(error[[3, 14, 15, 19, 26, 29, 32]], 2).tolist(), flush=True)
