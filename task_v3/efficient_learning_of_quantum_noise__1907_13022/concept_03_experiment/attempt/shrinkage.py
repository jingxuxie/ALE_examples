import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from scipy.optimize import minimize_scalar
import solver
from development import synthetic


def reconstruct(counts,depths):
    eigenvalues, variance, details=solver.fit_modes(counts,depths)
    size=len(eigenvalues)
    states=np.arange(size)
    prior=np.ones(size)
    order=np.zeros(size,dtype=int)
    for qubit in range(size.bit_length()-1):
        selected=(states & (1<<qubit))!=0
        prior[selected]*=eigenvalues[1<<qubit]
        order[selected]+=1
    selected=(order>=2)&np.isfinite(variance)&(variance<.03**2)
    difference=eigenvalues-prior
    selected_variance=variance[selected]
    selected_difference=difference[selected]
    def objective(log_scale):
        total_variance=selected_variance+np.exp(log_scale)
        return np.mean(np.log(total_variance)+selected_difference**2/total_variance)
    fit=minimize_scalar(objective,bounds=(-30,0),method='bounded')
    tau=np.exp(fit.x)
    shrink=tau/(variance+tau)
    shrink[order<=1]=1
    target=prior+shrink*(eigenvalues-prior)
    weights=1/np.maximum(variance,1e-14)+1/tau
    weights[order<=1]=1/np.maximum(variance[order<=1],1e-14)
    weights[0]=0
    weights/=np.max(weights)
    probabilities=solver.simplex(solver.hadamard(target)/size)
    extrapolated=probabilities.copy()
    momentum=1.
    for iteration in range(900):
        gradient=solver.hadamard(weights*(solver.hadamard(extrapolated)-target))/size
        updated=solver.simplex(extrapolated-gradient)
        next_momentum=.5*(1+np.sqrt(1+4*momentum*momentum))
        next_extrapolated=updated+(momentum-1)/next_momentum*(updated-probabilities)
        if np.dot(extrapolated-updated,updated-probabilities)>0:
            next_extrapolated=updated.copy(); next_momentum=1.
        change=np.max(np.abs(updated-probabilities))
        probabilities,extrapolated,momentum=updated,next_extrapolated,next_momentum
        if iteration>40 and change<2e-11:break
    return probabilities, tau


def independent(qubits,seed,shots):
    random=np.random.default_rng(seed)
    size=1<<qubits
    rates=np.zeros(size)
    spam=np.zeros(size)
    for qubit in range(qubits):
        rates[1<<qubit]=random.uniform(.001,.014)
        spam[1<<qubit]=random.uniform(.02,.16)
    rates[0]=-rates.sum();spam[0]=-spam.sum()
    modes=np.exp(solver.hadamard(rates));amplitudes=np.exp(solver.hadamard(spam))
    true=solver.hadamard(modes)/size
    depths=np.array([1,5,10,15,20,30,45,60,75,90,105])
    counts=np.array([random.multinomial(shots,np.maximum(solver.hadamard(amplitudes*modes**depth)/size,0)) for depth in depths])
    return counts,depths,true


if __name__=='__main__':
    for qubits in [6,10,14]:
        for shots in [10000,1000000]:
            for kind in ['independent','sparse','jitter','dense']:
                if kind=='independent':counts,depths,true=independent(qubits,37,shots)
                else:counts,depths,true=synthetic(qubits,37,shots=shots,jitter=.04 if kind=='jitter' else 0,sparse=kind!='dense')
                original=solver.reconstruct(counts,depths)
                shrunk,tau=reconstruct(counts,depths)
                parents=np.zeros((qubits,qubits),dtype=np.uint8)
                blocks=np.eye(qubits,dtype=np.uint8)
                queries=np.zeros((0,3,qubits),dtype=np.uint8)
                distances=[float(solver.diagnostics(distribution,blocks,queries,parents)[2]) for distribution in [true,original,shrunk]]
                print('n',qubits,'shots',shots,'kind',kind,'errors',
                      round(np.abs(original[1:]-true[1:]).sum()/true[1:].sum(),5),
                      round(np.abs(shrunk[1:]-true[1:]).sum()/true[1:].sum(),5),
                      'tau',round(tau,8),'JSD',np.round(distances,5),flush=True)
