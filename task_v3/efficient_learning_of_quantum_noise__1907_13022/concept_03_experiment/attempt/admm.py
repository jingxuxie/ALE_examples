import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import time
import numpy as np
import solver
from development import synthetic


def project(eigenvalues, uncertainty, cap=False):
    size=len(eigenvalues)
    good=np.isfinite(uncertainty[1:])
    reference=np.median(uncertainty[1:][good])
    weights=reference/(uncertainty+reference*.05) if cap else reference/np.maximum(uncertainty,1e-16)
    weights[0]=0
    probabilities=solver.simplex(solver.hadamard(eigenvalues)/size)
    dual=np.zeros(size)
    penalty=1.
    for iteration in range(1800):
        spectrum=solver.hadamard(probabilities-dual)
        spectrum=(weights*eigenvalues+penalty*spectrum)/(weights+penalty)
        unconstrained=solver.hadamard(spectrum)/size
        relaxed=1.6*unconstrained-.6*probabilities
        updated=solver.simplex(relaxed+dual)
        dual+=relaxed-updated
        primal_residual=unconstrained-updated
        dual_residual=penalty*(updated-probabilities)
        change=np.max(np.abs(updated-probabilities))
        probabilities=updated
        if iteration>40 and np.max(np.abs(primal_residual))<2e-10 and change<2e-10:
            break
        if iteration%25==24:
            primal_norm=np.linalg.norm(primal_residual)
            dual_norm=np.linalg.norm(dual_residual)
            if primal_norm>10*dual_norm and penalty<1e4:
                penalty*=2;dual/=2
            elif dual_norm>10*primal_norm and penalty>1e-4:
                penalty/=2;dual*=2
    return probabilities,iteration


if __name__=='__main__':
    for qubits in [6,10,14]:
        for shots in [10000,1000000]:
            for jitter in [0.,.04]:
                counts,depths,true=synthetic(qubits,37,shots=shots,jitter=jitter)
                original=solver.reconstruct(counts,depths)
                eigenvalues,variance,details=solver.fit_modes(counts,depths)
                start=time.monotonic()
                admm,iterations=project(eigenvalues,variance)
                runtime=time.monotonic()-start
                capped,capiterations=project(eigenvalues,variance,True)
                blocks=np.eye(qubits,dtype=np.uint8)
                parents=np.zeros((qubits,qubits),dtype=np.uint8)
                queries=np.zeros((0,3,qubits),dtype=np.uint8)
                true=np.maximum(true,0);true/=true.sum()
                true_correlations=solver.diagnostics(true,blocks,queries,parents)[0]
                errors=[np.abs(candidate[1:]-true[1:]).sum()/true[1:].sum() for candidate in [original,admm,capped]]
                corerrors=[np.sqrt(np.mean((solver.diagnostics(candidate,blocks,queries,parents)[0]-true_correlations)**2)) for candidate in [original,admm,capped]]
                print('n',qubits,'shots',shots,'jitter',jitter,'errors',np.round(errors,6),'corr_error',np.round(corerrors,6),
                      'iters',iterations,capiterations,'runtime',round(runtime,3),flush=True)
