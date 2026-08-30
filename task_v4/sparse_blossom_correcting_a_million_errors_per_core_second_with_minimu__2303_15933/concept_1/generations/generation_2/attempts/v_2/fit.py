from pathlib import Path
import argparse
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

parser = argparse.ArgumentParser()
parser.add_argument('--train', nargs='+', default=['featpub','feattrain'])
parser.add_argument('--test', nargs='+', default=['featpub','feattrain','featvalid'])
args = parser.parse_args()

def load(prefixes):
    all_features, all_truth = [], []
    for prefix in prefixes:
        for path in sorted(Path('.').glob(prefix+'_*.npz')):
            data = np.load(path)
            feature = data['features'].astype(float)
            truth = data['labels'] @ np.array([1,2,4,8])
            present = np.any(feature != 0,axis=(1,2))
            present &= feature[np.arange(len(truth)),truth,0] > -1e5
            feature = feature[present]
            truth = truth[present]
            mask = feature[:,:,0] > -1e5
            feature -= feature[np.arange(len(truth)),truth,None,:]
            feature[~mask] = 0
            feature[:,:,0][~mask] = -1e5
            all_features.append(feature)
            all_truth.append(truth)
    return np.concatenate(all_features), np.concatenate(all_truth)

features, truth = load(args.train)
initial = np.zeros(12); initial[:2] = 1
print('TRAIN',len(truth),flush=True)
for mode, columns in [('entropy', [1,2,3,11]),('all',list(range(1,12)))]:
    for regularization in [3,10,30]:
        def objective(parameters):
            weights = initial.copy(); weights[columns] = parameters
            logits = features @ weights
            normalizers = logsumexp(logits,axis=1)
            loss = (normalizers-logits[np.arange(len(truth)),truth]).sum()
            probabilities = np.exp(logits-normalizers[:,None]); probabilities[np.arange(len(truth)),truth] -= 1
            gradient = np.einsum('nc,nck->k', probabilities, features) + regularization*(weights-initial)
            loss += regularization/2 * ((weights-initial)**2).sum()
            return loss, gradient[columns]
        bounds = [(0,2) if column == 1 else (0,1) if column in [2,3,11] else (-1,1) for column in columns]
        fit = minimize(objective, initial[columns], jac=True, method='L-BFGS-B', bounds=bounds)
        weights = initial.copy(); weights[columns] = fit.x
        print(mode,regularization,np.round(weights,4),flush=True)
        for prefix in args.test:
            counts = []
            for path in sorted(Path('.').glob(prefix+'_*.npz')):
                data=np.load(path); feature=data['features']; target=data['labels']@np.array([1,2,4,8]); prediction=data['predictions']@np.array([1,2,4,8])
                present=np.any(feature!=0,axis=(1,2)); prediction[present]=(feature[present]@weights).argmax(1)
                counts.append(int((prediction!=target).sum()))
            print(prefix,sum(counts),counts,flush=True)
        np.save('weights_'+mode+'_'+str(regularization)+'.npy',weights)
