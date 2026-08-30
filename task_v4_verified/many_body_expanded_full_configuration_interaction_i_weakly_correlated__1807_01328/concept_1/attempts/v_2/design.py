import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from scipy.linalg import cho_factor, cho_solve
from quadrature import ORDERS,HIGH,CANDIDATES,SELECTOR,COSTS
from kernel_test import overlap_normalized,same_order

def covariance(weights,correlation=.3,power=4):
    sigma = np.sqrt(weights)
    kernel = np.eye(len(HIGH))*(1-correlation) + correlation*overlap_normalized**power*same_order
    return SELECTOR @ (kernel*sigma[:,None]*sigma[None,:]) @ SELECTOR.T

def greedy(matrix,initial=None,forced_fives=0):
    matrix = matrix.copy()
    chosen = []
    remaining = 104
    for stage in range(26):
        variance = np.diag(matrix)[:-1]
        utility = matrix[-1,:-1]**2 / np.maximum(variance,1e-28) / COSTS
        utility[COSTS > remaining] = -1
        utility[chosen] = -1
        utility[variance < 1e-25] = -1
        if initial is not None and 1<=stage<=forced_fives:
            utility[ORDERS[CANDIDATES]!=5]=-1
        best = int(np.argmax(utility)) if stage or initial is None else initial
        if utility[best] < 0:
            break
        chosen.append(best)
        remaining -= int(COSTS[best])
        direction = matrix[:,best].copy()
        matrix -= np.outer(direction,direction)/max(matrix[best,best],1e-28)
        matrix = (matrix+matrix.T)*.5
    return matrix[-1,-1],chosen

def design(matrix,mode='optimal'):
    if mode == 'greedy':
        return greedy(matrix)[1]
    starts = np.flatnonzero(ORDERS[CANDIDATES] == 6)
    forced_fives=2 if mode=='anchor_two_fives' else 0
    options = [greedy(matrix,int(initial),forced_fives) for initial in starts]
    if mode == 'optimal':
        options.append(greedy(matrix))
    return min(options,key=lambda item:item[0])[1]

def estimate(matrix,mean,truth,chosen):
    selected = np.array(chosen)
    gram = matrix[np.ix_(selected,selected)]
    gram += np.eye(len(gram))*max(np.max(np.diag(gram))*1e-12,1e-26)
    factor = cho_factor(gram,lower=True,check_finite=False)
    residual = truth[selected]-mean[selected]
    solution = cho_solve(factor,residual,check_finite=False)
    prediction = mean[-1] + matrix[-1,selected] @ solution
    norm = max(residual@solution,1e-20)
    likelihood = len(selected)*np.log(norm/len(selected)) + 2*np.log(np.diag(factor[0])).sum()
    return prediction,likelihood

if __name__ == '__main__':
    import time
    start = time.process_time()
    cache = np.load(os.environ.get('POLICY_CACHE','neural_policy_cache.npz'))
    weights,means,target = [cache[key] for key in ['weights','means','target']]
    indices = np.r_[np.arange(36),np.arange(37,len(weights),2)]
    for correlation,power in [(0.,4),(.1,4),(.3,4),(.7,4),(.3,8)]:
        for mode in ['optimal','anchor']:
            errors = []
            mixture_errors = []
            for row in indices:
                matrix = covariance(weights[row],correlation,power)
                chosen = design(matrix,mode)
                mean = SELECTOR@means[row]
                truth = SELECTOR@target[row]
                predicted = estimate(matrix,mean,truth,chosen)[0]
                errors.append((predicted-truth[-1])*1e6)
                candidates = []
                likelihoods = []
                for alternate_correlation in [0.,.03,.1,.3,.7,.95]:
                    alternate = covariance(weights[row],alternate_correlation,power)
                    prediction,likelihood = estimate(alternate,mean,truth,chosen)
                    candidates.append(prediction)
                    likelihoods.append(likelihood)
                likelihoods = np.array(likelihoods)
                mixture = np.exp(-.25*(likelihoods-likelihoods.min()))
                prediction = np.array(candidates) @ mixture/mixture.sum()
                mixture_errors.append((prediction-truth[-1])*1e6)
            for name,values in [('fixed',errors),('mixture',mixture_errors)]:
                errors_array = np.array(values)
                print(correlation,power,mode,name,'practice',round(np.sqrt(np.mean(errors_array[:36]**2)),2),'ordinary',round(np.sqrt(np.mean(errors_array[36:96]**2)),2),'stress',round(np.sqrt(np.mean(errors_array[96:156]**2)),2),'cancel',round(np.sqrt(np.mean(errors_array[156:]**2)),2),'hard',np.round(errors_array[[14,26,29,32]],2).tolist(),flush=True)
    print('cpu',time.process_time()-start,flush=True)
