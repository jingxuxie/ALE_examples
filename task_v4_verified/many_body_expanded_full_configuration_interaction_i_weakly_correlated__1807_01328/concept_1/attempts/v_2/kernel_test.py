import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from quadrature import ORDERS, SUBSET, HIGH, CANDIDATES, SELECTOR, COSTS, features, mobius

overlap = np.array([mask.bit_count() for mask in range(256)])[HIGH[:,None] & HIGH[None,:]]
same_order = ORDERS[HIGH,None] == ORDERS[None,HIGH]
overlap_normalized = overlap / np.sqrt(ORDERS[HIGH,None]*ORDERS[None,HIGH])

def run(weights, target, kernel, mode, mean=None):
    sigma = np.sqrt(weights)
    covariance = kernel * sigma[:,None] * sigma[None,:]
    matrix = SELECTOR @ covariance @ SELECTOR.T
    estimates = np.zeros(len(CANDIDATES)+1) if mean is None else SELECTOR @ mean
    truth = SELECTOR @ target
    remaining = 104
    chosen = []
    while remaining >= 4:
        available = COSTS <= remaining
        available[chosen] = False
        variances = np.diag(matrix)[:-1]
        utility = matrix[-1,:-1]**2 / np.maximum(variances,1e-28) / COSTS
        utility[~available] = -1
        utility[variances < 1e-25] = -1
        if mode == 'anchor' and not chosen:
            utility[ORDERS[CANDIDATES] != 6] = -1
        if mode == 'five' and len(chosen) < 6:
            utility[ORDERS[CANDIDATES] != 5] = -1
        best = int(np.argmax(utility))
        if utility[best] < 0:
            break
        remaining -= int(COSTS[best])
        chosen.append(best)
        direction = matrix[:,best].copy()
        denominator = max(matrix[best,best],1e-28)
        estimates += direction*(truth[best]-estimates[best])/denominator
        matrix -= np.outer(direction,direction)/denominator
        matrix = (matrix+matrix.T)*.5
    return estimates[-1]-target.sum(), [int(CANDIDATES[index]) for index in chosen]

if __name__ == '__main__':
    import time
    start = time.process_time()
    cache = np.load('practice_features.npz')
    weights, target = cache['weights'],cache['targets']
    all_cache = np.load('feature_cache.npz')
    validation = np.arange(0, 1200, 15)
    validation_weights = all_cache['weights'][validation]
    validation_targets = all_cache['targets'][validation]
    factor = np.load('quadrature_model.npz')['variance_scale'][ORDERS[HIGH]-4]
    weights = weights*factor
    validation_weights = validation_weights*factor
    results = []
    for power in [0,1,2,4,8]:
        for correlation in [.03,.1,.3,.7,.95]:
            for mode in ['greedy','anchor','five']:
                kernel = np.eye(len(HIGH))*(1-correlation) + correlation*overlap_normalized**power*same_order
                errors = np.array([run(weights[row],target[row],kernel,mode)[0] for row in range(len(weights))])*1e6
                validation_errors = np.array([run(validation_weights[row],validation_targets[row],kernel,mode)[0] for row in range(len(validation))])*1e6
                rmse = np.sqrt(np.mean(errors**2))
                validation_rmse = np.sqrt(np.mean(validation_errors**2))
                results.append([rmse,validation_rmse,power,correlation,mode])
                print(power,correlation,mode,'practice',round(rmse,2),'validation',round(validation_rmse,2),'hard',np.round(errors[[14,26,29,32]],2).tolist(),flush=True)
    print('best',sorted(results)[:12],flush=True)
    print('cpu',time.process_time()-start,flush=True)
