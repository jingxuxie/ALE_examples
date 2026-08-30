import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from scipy.linalg import solve
from quadrature import ORDERS, SUBSET, HIGH, CANDIDATES, SELECTOR, COSTS, SINGLE, PAIR, TRIPLES, mobius, features
from kernel_test import run, overlap_normalized, same_order
from neural import SUBSETS, SITES

def variance_features(table, mean, order):
    terms = mobius(table)
    single = np.maximum(-terms[SINGLE],1e-14)
    result = []
    for local, mask in enumerate(SUBSETS[order]):
        source = single[SUBSET[mask,SINGLE]]
        average = source.mean()
        pairs = np.sort(abs(terms[PAIR[SUBSET[mask,PAIR]]])) / average
        triples = np.sort(abs(terms[TRIPLES[SUBSET[mask,TRIPLES]]])) / average
        scale = np.r_[source.min()/average, source.max()/average, pairs[[0,len(pairs)//2,-2,-1]], triples[[0,len(triples)//2,-2,-1]], abs(mean[local])/average]
        logs = np.log(np.maximum(scale,1e-7))
        result.append(np.r_[1.,logs,logs**2/10,np.log(average/.005)])
    return np.array(result)

def variance_train(tables, means, targets, order, prefix='variance_'):
    designs = np.array([variance_features(table,mean,order) for table,mean in zip(tables,means)])
    source_average = np.array([np.array([-table[1 << site] for site in range(8)])[SITES[order]].mean(axis=1) for table in tables])
    scale = np.sqrt(np.mean(designs.reshape(-1,designs.shape[-1])**2,axis=0)) + 1e-10
    design = designs.reshape(-1,designs.shape[-1])/scale
    response = np.log(np.maximum(abs(targets-means)/source_average,1e-8)).ravel()
    coefficient = solve(design.T@design + np.eye(len(scale))*len(design)*.01,design.T@response,assume_a='pos')
    sigma = np.exp(np.clip(design @ coefficient,-20,2)).reshape(means.shape)*source_average
    multiplier = np.sqrt(np.mean((targets-means)**2)/np.mean(sigma**2))
    np.savez(prefix+str(order)+'.npz',scale=scale,coefficient=coefficient,multiplier=multiplier)
    return scale,coefficient,multiplier

def variance_predict(table, mean, order, model):
    scale,coefficient,multiplier = model
    design = variance_features(table,mean,order)/scale
    source_average = np.array([-table[1 << site] for site in range(8)])[SITES[order]].mean(axis=1)
    return (np.exp(np.clip(design@coefficient,-20,2))*source_average*multiplier)**2

if __name__ == '__main__':
    import time
    ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
    start = time.process_time()
    model_kind = os.environ.get('MODEL_KIND','neural')
    practice = np.load(ASSETS+'/input/practice.npz')['energies']
    tables = np.concatenate((np.load('synthetic.npz')['energies'],np.load('cancellation.npz')['energies']))
    validation = np.arange(0,len(tables),5)
    all_tables = np.concatenate((practice,tables[validation]))
    target = np.array([mobius(table)[HIGH] for table in all_tables])
    means = np.zeros_like(target)
    weights = np.zeros_like(target)
    for order in [4,5]:
        predicted = np.load(model_kind+'_predictions_'+str(order)+'.npz')
        all_predicted = np.concatenate((predicted['practice'],predicted['validation']))
        model = variance_train(tables[validation[::2]],predicted['validation'][::2],np.array([mobius(table)[SUBSETS[order]] for table in tables[validation[::2]]]),order,prefix='variance_' if model_kind=='neural' else model_kind+'_variance_')
        means[:,ORDERS[HIGH] == order] = all_predicted
        for row, table in enumerate(all_tables):
            weights[row,ORDERS[HIGH] == order] = variance_predict(table,all_predicted[row],order,model)
    for order in range(6,9):
        parents = ORDERS[HIGH] == 5
        raw = (weights[:,parents]+means[:,parents]**2) @ SUBSET[HIGH[ORDERS[HIGH] == order]][:,HIGH[parents]].T
        observed_variance = np.mean(target[36:,ORDERS[HIGH] == order]**2)
        multiplier = observed_variance / np.mean(raw[36:])
        weights[:,ORDERS[HIGH] == order] = raw*multiplier
        print('higher factor',order,multiplier,flush=True)
    np.savez(model_kind+'_policy_cache.npz',weights=weights,means=means,target=target,validation=validation)
    results = []
    for power in [0,2,4,8]:
        for correlation in [0.,.03,.1,.3,.7]:
            for mode in ['greedy','anchor','five']:
                kernel = np.eye(len(HIGH))*(1-correlation) + correlation*overlap_normalized**power*same_order
                errors = np.array([run(weights[row],target[row],kernel,mode,means[row])[0] for row in range(len(weights))])*1e6
                practice_rmse = np.sqrt(np.mean(errors[:36]**2))
                ordinary_rmse = np.sqrt(np.mean(errors[37:156:2]**2))
                stress_rmse = np.sqrt(np.mean(errors[157:276:2]**2))
                cancellation_rmse = np.sqrt(np.mean(errors[277::2]**2))
                results.append([practice_rmse,ordinary_rmse,stress_rmse,cancellation_rmse,power,correlation,mode])
                print(power,correlation,mode,'practice',round(practice_rmse,2),'ordinary',round(ordinary_rmse,2),'stress',round(stress_rmse,2),'cancel',round(cancellation_rmse,2),'hard',np.round(errors[[14,26,29,32]],2).tolist(),flush=True)
    print('best',sorted(results)[:10],flush=True)
    print('cpu',time.process_time()-start,flush=True)
