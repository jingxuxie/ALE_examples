import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from quadrature import ORDERS, SUBSET, TRIPLES, QUADS, SINGLE, PAIR, LEFT, RIGHT, mobius, features
PARTITIONS = [(int(left),int(right)) for left in PAIR for right in PAIR if left < right and not left & right]
UNCOVERED = np.array([~(SUBSET[255^left] | SUBSET[255^right]) & (ORDERS >= 4) for left,right in PARTITIONS])

def predict(table, kind, power=1., correction=0.):
    terms = mobius(table)
    singles = np.maximum(-terms[SINGLE],1e-15)
    pair_strength = abs(terms[PAIR])
    if kind == 'single':
        weights = np.prod(np.where(SUBSET[:, SINGLE], singles[None]**power, 1),axis=1)
    elif kind in ['pair','normalized']:
        if kind == 'normalized':
            pair_strength = pair_strength / np.sqrt(singles[LEFT]*singles[RIGHT])
        matrix = np.zeros((8,8))
        matrix[LEFT,RIGHT] = pair_strength
        matrix[RIGHT,LEFT] = pair_strength
        weights = np.zeros(256)
        for mask in QUADS:
            sites = np.flatnonzero(SUBSET[mask,SINGLE])
            strengths = matrix[np.ix_(sites,sites)]
            laplacian = np.diag(strengths.sum(axis=0))-strengths
            weights[mask] = max(np.linalg.det(laplacian[:-1,:-1]),0)**power
    else:
        weights = np.zeros(256)
        weights[ORDERS >= 4] = features(table)[1]
    candidates = UNCOVERED @ weights
    best = int(np.argmin(candidates))
    left,right = PARTITIONS[best]
    missing = UNCOVERED[best].copy()
    score = np.zeros(256)
    cross_triples = ~(SUBSET[255^left] | SUBSET[255^right]) & (ORDERS == 3)
    for mask in QUADS:
        magnitudes = np.sort(abs(terms[TRIPLES[SUBSET[mask,TRIPLES] & cross_triples[TRIPLES]]]))
        score[mask] = magnitudes[-1] if len(magnitudes) == 1 else np.sqrt(magnitudes[-1]*magnitudes[-2]) if len(magnitudes) else 0
    selected = np.flatnonzero(missing & (ORDERS==4))
    selected = selected[np.argsort(-score[selected])[:2]]
    missing[selected] = False
    error = -terms[missing].sum()
    if correction:
        ratio = score[missing].sum() / max(score[selected].sum(),1e-30)
        error += correction * terms[selected].sum() * ratio
    return error

if __name__ == '__main__':
    ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
    tables = np.load(ASSETS+'/input/practice.npz')['energies']
    for kind in ['single','pair','normalized','oracle_triple']:
        for power in [.25,.5,1.,2.]:
            for correction in [0.,.25,.5,1.]:
                errors = np.array([predict(table,kind,power,correction) for table in tables])*1e6
                print(kind,power,correction,'rmse',round(np.sqrt(np.mean(errors**2)),2),'hard',np.round(errors[[14,26,29,32]],2).tolist(),flush=True)
