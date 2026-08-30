import argparse
import time
import numpy as np
from scipy.optimize import minimize
import fermion
from search import Engine, LIB, INT, DOUBLE


LIB.set_schmidt.argtypes = [INT, DOUBLE]
LIB.purity_options.argtypes = [DOUBLE, DOUBLE, DOUBLE]
parser = argparse.ArgumentParser()
parser.add_argument('--case', type=int, default=0)
parser.add_argument('--beam', type=int, default=20)
parser.add_argument('--depth', type=int, default=6)
args = parser.parse_args()
engine = Engine(fermion.load_cases()[args.case])
engine.initial = engine.target.copy()
masks = [mask for mask in engine.case.determinants if sum((mask >> orbital) & 1 for orbital in range(0,10,2)) == engine.case.n_alpha]
combos = [mask for mask in range(32) if mask.bit_count() == engine.case.n_alpha]
indices, phases = [], []
for mask in masks:
    alpha = sum(((mask >> (2 * orbital)) & 1) << orbital for orbital in range(5))
    beta = sum(((mask >> (2 * orbital + 1)) & 1) << orbital for orbital in range(5))
    indices.append(combos.index(alpha) * 10 + combos.index(beta))
    phases.append((-1)**sum(((alpha >> orbital) & 1) * ((beta & ((1 << orbital) - 1)).bit_count()) for orbital in range(5)))
indices = np.array(indices, np.int32)
phases = np.array(phases, np.float64)
LIB.set_schmidt(indices, phases)


def optimize(labels, angles):
    def objective(parameters):
        state, jacobian = engine.state_jac(labels, parameters)
        matrix = np.empty(100)
        matrix[indices] = phases * state
        matrix = matrix.reshape(10,10)
        reduced = matrix @ matrix.T
        derivative = (4 * reduced @ matrix).ravel()[indices] * phases
        return 1 - np.sum(reduced * reduced), -jacobian.T @ derivative
    result = minimize(objective, angles, jac=True, method='BFGS', options={'maxiter': 150, 'gtol': 1e-8})
    return np.array(labels,np.int32), (result.x + np.pi) % (2*np.pi) - np.pi, result.fun


beam = [(np.empty(0,np.int32),np.empty(0),1.0)]
for step in range(args.depth):
    trials = []
    for labels, angles, loss in beam:
        state, _ = engine.state_jac(labels, angles)
        values, optimal = np.empty(250), np.empty(250)
        LIB.purity_options(state, values, optimal)
        for label in np.argsort(values)[-10:][::-1]:
            result = optimize(np.append(labels,label), np.append(angles,optimal[label]))
            trials.append(result)
    trials.sort(key=lambda item:item[2])
    kept, fingerprints = [], set()
    for trial in trials:
        state, _ = engine.state_jac(trial[0], trial[1])
        fingerprint = np.round(state,5).tobytes()
        if fingerprint in fingerprints:
            continue
        fingerprints.add(fingerprint)
        kept.append(trial)
        if len(kept)>=args.beam:
            break
    beam = kept
    print('cool',step+1,'best',beam[0][2],'elapsed',time.time()-engine.started,flush=True)
    engine.save(*beam[0],suffix='cool')
    if beam[0][2]<1e-10:
        break
