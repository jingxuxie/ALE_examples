import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
import solver
from development import synthetic


def variance_project(counts, depths, jackknife=False):
    eigenvalues, uncertainty, details = solver.fit_modes(counts, depths)
    size = len(eigenvalues)
    raw = solver.hadamard(eigenvalues)/size
    influence = np.pad(details['influence'], ((0,0),(1,0)))
    kernel = solver.hadamard(influence)/size
    variances = solver.hadamard(details['spectrum'] * solver.hadamard(kernel*kernel))/size
    means = solver.hadamard(details['spectrum'] * influence)/size
    variance = np.sum((variances-means*means)/details['shots'][:,None],axis=0)
    if jackknife:
        prediction = np.pad(details['amplitudes'][None,:]*np.exp(-details['times'][:,None]*details['rates'][None,:]),((0,0),(1,0)),constant_values=1)
        residual = details['spectrum'] - prediction
        pseudo = solver.hadamard(influence*residual)/size
        degrees = max(len(depths)-2,1)
        empirical = np.sum(pseudo*pseudo,axis=0)*len(depths)/degrees
        variance = np.maximum(variance, empirical)
    variance = np.maximum(variance,1e-25)
    ratio = raw/variance
    order = np.argsort(-ratio)
    cutoffs = (np.cumsum(raw[order])-1)/np.cumsum(variance[order])
    feasible = np.flatnonzero(ratio[order]>cutoffs)
    threshold = cutoffs[feasible[-1]]
    result = np.maximum(raw-threshold*variance,0)
    return result/result.sum()


if __name__=='__main__':
    for qubits in [6,10,14]:
        for shots in [10000,1000000]:
            for jitter, floor in [(0.,0.),(.04,0.),(0.,.008)]:
                counts, depths, true = synthetic(qubits,37,shots=shots,jitter=jitter,floor=floor)
                print('n',qubits,'shots',shots,'jitter',jitter,'floor',floor,flush=True)
                for name, function in [('spectral',solver.reconstruct),('variance',variance_project),('jackknife',lambda counts,depths:variance_project(counts,depths,True))]:
                    recovered=function(counts,depths)
                    error=np.abs(recovered[1:]-true[1:]).sum()/true[1:].sum()
                    print(name,round(error,5),'identity',round(recovered[0],6),flush=True)
