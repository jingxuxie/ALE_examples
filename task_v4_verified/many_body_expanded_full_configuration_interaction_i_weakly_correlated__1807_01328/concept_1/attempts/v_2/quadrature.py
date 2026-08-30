import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np
from scipy.linalg import solve

ORDERS = np.array([mask.bit_count() for mask in range(256)])
MASKS = np.arange(256)
BITS = ((MASKS[:, None] >> np.arange(8)) & 1).astype(float)
SUBSET = (MASKS[:, None] & MASKS[None, :]) == MASKS[None, :]
HIGH = np.flatnonzero(ORDERS >= 4)
CANDIDATES = np.flatnonzero((ORDERS >= 4) & (ORDERS <= 6))
TRIPLES = np.flatnonzero(ORDERS == 3)
QUADS = np.flatnonzero(ORDERS == 4)
SINGLE = 1 << np.arange(8)
LEFT, RIGHT = np.triu_indices(8, 1)
PAIR = (1 << LEFT) | (1 << RIGHT)
TRIPLE_IN_QUAD = np.array([TRIPLES[SUBSET[mask, TRIPLES]] for mask in QUADS])
SELECTOR = SUBSET[np.r_[CANDIDATES, 255]][:, HIGH].astype(float)
COSTS = np.array([4 ** (ORDERS[mask]-3) for mask in CANDIDATES])

def mobius(values):
    result = np.array(values, copy=True)
    for bit in range(8):
        selected = (MASKS & (1 << bit)) != 0
        result[selected] -= result[MASKS[selected] ^ (1 << bit)]
    return result

def features(energies):
    observed = np.zeros(256)
    observed[ORDERS <= 3] = energies[ORDERS <= 3]
    terms = mobius(observed)
    terms[ORDERS > 3] = 0
    sources = np.maximum(-terms[SINGLE], 1e-14)
    source_sum = BITS @ sources
    pair_sum = SUBSET[:, PAIR] @ terms[PAIR]
    triple_sum = SUBSET[:, TRIPLES] @ terms[TRIPLES]
    norm = np.maximum(source_sum, sources.sum() * 1e-4)
    pair_ratio = np.clip(pair_sum / norm, -2, 2)
    triple_ratio = np.clip(triple_sum / norm, -2, 2)
    values = []
    for degree in range(2, 5):
        for triple_power in range(degree + 1):
            values.append(norm * pair_ratio ** (degree-triple_power) * triple_ratio ** triple_power)
    for rate in [0.25, 0.5, 1., 2., 4.]:
        values.append(triple_sum * pair_ratio / (1 + rate * abs(pair_ratio)))
        values.append(triple_sum * abs(pair_ratio) / (1 + rate * abs(pair_ratio)))
        values.append(triple_sum * triple_ratio / (1 + rate * abs(pair_ratio)))
    rooted = np.zeros((256, 8))
    for site in range(8):
        adjacent = PAIR[(PAIR & (1 << site)) != 0]
        rooted[:, site] = SUBSET[:, adjacent] @ terms[adjacent]
    for floor in [0.01, 0.1, 1.]:
        divisor = sources + floor*sources.mean()
        for degree in [2, 3, 4]:
            values.append(np.sum(rooted ** degree / divisor[None] ** (degree-1), axis=1))
        rooted_triples = np.zeros((256, 8))
        for site in range(8):
            adjacent = TRIPLES[(TRIPLES & (1 << site)) != 0]
            rooted_triples[:, site] = SUBSET[:, adjacent] @ terms[adjacent]
        values.append(np.sum(rooted * rooted_triples / divisor[None], axis=1))
        values.append(np.sum(rooted_triples ** 2 / divisor[None], axis=1))
    feature = mobius(np.array(values).T)[HIGH]
    magnitudes = np.sort(abs(terms[TRIPLE_IN_QUAD]), axis=1)
    score = np.sqrt(magnitudes[:, -1] * magnitudes[:, -2])
    score = 0.5 * score + 0.5 * magnitudes[:, -2]
    weights = np.zeros(256)
    weights[QUADS] = score**2
    for order in range(5, 9):
        weights[ORDERS == order] = (SUBSET[ORDERS == order][:, QUADS] @ weights[QUADS]) * 0.025**(order-4)
    weights = np.maximum(weights[HIGH], 1e-24)
    return feature, weights, SUBSET @ terms

def prepare(tables, path):
    all_features = []
    all_weights = []
    targets = []
    for table in tables:
        feature, weights, low = features(table)
        all_features.append(feature)
        all_weights.append(weights)
        targets.append(mobius(table)[HIGH])
    all_features = np.array(all_features)
    all_weights = np.array(all_weights)
    targets = np.array(targets)
    np.savez_compressed(path, features=all_features, weights=all_weights, targets=targets)
    return all_features, all_weights, targets

def train(feature, weights, target):
    order_weight = np.array([1. if ORDERS[mask] == 4 else 0.3 for mask in HIGH])
    normalizer = np.sqrt(weights) + 2e-6
    design = (feature / normalizer[:, :, None] * order_weight[None, :, None]).reshape(-1, feature.shape[-1])
    response = (target / normalizer * order_weight).ravel()
    scale = np.sqrt(np.mean(design**2, axis=0)) + 1e-10
    design /= scale
    gram = design.T @ design
    coefficient = solve(gram + np.eye(len(scale))*len(design)*0.001, design.T @ response, assume_a='pos')
    residual = target - (feature/scale) @ coefficient
    variance_scale = np.array([np.mean(residual[:, ORDERS[HIGH] == order]**2) / np.mean(weights[:, ORDERS[HIGH] == order]) for order in range(4,9)])
    print('variance factors', variance_scale, flush=True)
    return scale, coefficient, variance_scale

def predict(feature, weights, target, model, strength=1., noise=1., mode='greedy'):
    scale, coefficient, variance_scale = model
    feature = feature / scale
    feature = np.clip(feature, -0.1, 0.1)
    prior = feature @ coefficient
    variance = weights * variance_scale[ORDERS[HIGH]-4]
    covariance = np.diag(variance * noise) + (feature @ feature.T) * strength
    matrix = SELECTOR @ covariance @ SELECTOR.T
    estimates = SELECTOR @ prior
    truth = SELECTOR @ target
    remaining = 104
    chosen = []
    while remaining >= 4:
        available = (COSTS <= remaining)
        available[chosen] = False
        variances = np.diag(matrix)[:-1]
        utility = matrix[-1, :-1] ** 2 / np.maximum(variances, 1e-28) / COSTS
        utility[~available] = -1
        utility[variances < 1e-25] = -1
        if mode == 'anchor' and not chosen:
            utility[ORDERS[CANDIDATES] != 6] = -1
        best = int(np.argmax(utility))
        if utility[best] < 0:
            break
        remaining -= int(COSTS[best])
        chosen.append(best)
        direction = matrix[:, best].copy()
        denominator = max(matrix[best, best], 1e-28)
        estimates += direction * (truth[best] - estimates[best]) / denominator
        matrix -= np.outer(direction, direction) / denominator
        matrix = (matrix + matrix.T) * .5
    return estimates[-1] - target.sum(), [int(CANDIDATES[index]) for index in chosen]

if __name__ == '__main__':
    import sys
    import time
    ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
    start = time.process_time()
    synthetic = np.load('synthetic.npz')['energies']
    if os.path.exists('feature_cache.npz'):
        cache = np.load('feature_cache.npz')
        feature, weights, target = [cache[name] for name in ['features','weights','targets']]
    else:
        feature, weights, target = prepare(synthetic, 'feature_cache.npz')
    practice = np.load(ASSETS+'/input/practice.npz')['energies']
    practice_feature, practice_weights, practice_target = prepare(practice, 'practice_features.npz')
    training = np.arange(len(synthetic)) % 5 != 0
    model = train(feature[training], weights[training], target[training])
    np.savez('quadrature_model.npz', scale=model[0], coefficient=model[1], variance_scale=model[2])
    print('prepared cpu', time.process_time()-start, flush=True)
    for strength in [0., .001, .01, .1, 1., 10., 100.]:
        for mode in ['greedy', 'anchor']:
            errors = []
            selections = []
            for row in range(len(practice)):
                error, chosen = predict(practice_feature[row], practice_weights[row], practice_target[row], model, strength=strength, mode=mode)
                errors.append(error * 1e6)
                selections.append([sum(ORDERS[mask] == order for mask in chosen) for order in [4,5,6]])
            validation_errors = []
            for row in np.flatnonzero(~training)[:60]:
                error, chosen = predict(feature[row], weights[row], target[row], model, strength=strength, mode=mode)
                validation_errors.append(error * 1e6)
            print(strength, mode, 'practice', round(np.sqrt(np.mean(np.array(errors)**2)),3), 'max', round(max(abs(np.array(errors))),2), 'holdout', round(np.sqrt(np.mean(np.array(validation_errors)**2)),3), 'selection', np.mean(selections, axis=0).round(2), 'hard', np.round(np.array(errors)[[3,14,15,19,26,29,32]],2), flush=True)
    print('cpu', time.process_time()-start, flush=True)
