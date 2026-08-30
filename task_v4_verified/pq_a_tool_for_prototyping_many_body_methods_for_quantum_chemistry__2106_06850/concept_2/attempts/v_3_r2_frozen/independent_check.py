import os
for variable in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[variable]='1'
import itertools
import json
import sys
import time
from pathlib import Path
import numpy as np
from scipy.linalg import expm
from scipy.optimize import root

payload=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else 'submission.json').read_text())
output=sys.argv[2] if len(sys.argv)>2 else 'independent.json'
pairs=list(itertools.combinations(range(6),2))
pair_index={pair:index for index,pair in enumerate(pairs)}
sector=np.array([bits for bits in range(64) if bits.bit_count()==3])
annihilation=np.zeros((6,64,64))
for orbital in range(6):
    for bits in range(64):
        if bits&(1<<orbital):
            annihilation[orbital,bits^(1<<orbital),bits]=(-1)**((bits&((1<<orbital)-1)).bit_count())
creation=annihilation.transpose(0,2,1)
one_full=np.array([[creation[left]@annihilation[right] for right in range(6)] for left in range(6)])
two_full=np.array([[creation[first]@creation[second]@annihilation[fourth]@annihilation[third]
                    for third,fourth in pairs] for first,second in pairs])
one=one_full[:,:,sector[:,None],sector[None,:]]
two=two_full[:,:,sector[:,None],sector[None,:]]
generators=[]
targets=[]
for holes in range(3):
    for particle in range(3,6):
        operator=(creation[particle]@annihilation[holes])[np.ix_(sector,sector)]
        target=int(np.argmax(np.abs(operator[:,0])))
        generators.append(operator*operator[target,0])
        targets.append(target)
for first,second in itertools.combinations(range(3),2):
    for third,fourth in itertools.combinations(range(3,6),2):
        operator=(creation[third]@creation[fourth]@annihilation[second]@annihilation[first])[np.ix_(sector,sector)]
        target=int(np.argmax(np.abs(operator[:,0])))
        generators.append(operator*operator[target,0])
        targets.append(target)
generators=np.array(generators)
targets=np.array(targets)
reference=np.eye(20)[:,0]

def make_hamiltonian(matrix):
    one_body=np.diag(payload['orbital_energies']).copy()
    for left in range(6):
        for right in range(6):
            for occupied in range(3):
                if left!=occupied and right!=occupied:
                    row=pair_index[tuple(sorted((left,occupied)))]
                    column=pair_index[tuple(sorted((right,occupied)))]
                    sign=(1 if left<occupied else -1)*(1 if right<occupied else -1)
                    one_body[left,right]-=sign*matrix[row,column]
    return np.einsum('pq,pqij->ij',one_body,one)+np.einsum('ab,abij->ij',matrix,two)

def equations(hamiltonian,amplitudes):
    cluster=np.einsum('a,aij->ij',amplitudes,generators)
    positive=expm(cluster)
    negative=expm(-cluster)
    transformed=negative@hamiltonian@positive
    commutators=np.array([transformed@generator-generator@transformed for generator in generators])
    residual=transformed[targets,0]
    jacobian=commutators[:,targets,0].T
    return residual,jacobian,transformed,positive,negative

def hf_minima(hamiltonian):
    minima=[]
    for rotations in (generators[:9]-generators[:9].transpose(0,2,1),
                      1j*(generators[:9]+generators[:9].transpose(0,2,1))):
        first_commutators=np.array([hamiltonian@rotation-rotation@hamiltonian for rotation in rotations])
        hessian=np.array([[(first_commutators[row]@rotations[column]-rotations[column]@first_commutators[row])[0,0].real
                           for column in range(9)] for row in range(9)])
        minima.append(float(np.linalg.eigvalsh((hessian+hessian.T)/2)[0]))
    return minima

def diagnostic(matrix,amplitudes):
    hamiltonian=make_hamiltonian(matrix)
    residual,jacobian,transformed,positive,negative=equations(hamiltonian,amplitudes)
    gradient=np.array([(transformed@generator-generator@transformed)[0,0] for generator in generators])
    multipliers=np.linalg.solve(jacobian.T,-gradient)
    left_seed=reference.copy()
    left_seed[targets]=multipliers
    left=left_seed@negative
    right=positive[:,0]
    density=np.einsum('i,pqij,j->pq',left,one,right)
    occupations=np.linalg.eigvalsh((density+density.T)/2)
    exact_energies,exact_vectors=np.linalg.eigh(hamiltonian)
    exact_density=np.einsum('i,pqij,j->pq',exact_vectors[:,0],one,exact_vectors[:,0])
    right_density=np.einsum('i,pqij,j->pq',right,one,right)/(right@right)
    minima=hf_minima(hamiltonian)
    return {
        'energy_error':float(abs(transformed[0,0]-exact_energies[0])),
        'cc_residual':float(np.max(np.abs(residual))),
        'lambda_residual':float(np.max(np.abs(jacobian.T@multipliers+gradient))),
        'rdm_dad':float(np.linalg.norm(density-density.T)/np.sqrt(3)),
        'occupation_violation':float(max(0,-occupations[0],occupations[-1]-1)),
        'occupations':occupations.tolist(),
        'exact_occupations':np.linalg.eigvalsh(exact_density).tolist(),
        'right_occupations':np.linalg.eigvalsh(right_density).tolist(),
        'ground_overlap':float((exact_vectors[:,0]@right)**2/(right@right)),
        'reference_weight':float(exact_vectors[0,0]**2),
        'fci_gap':float(exact_energies[1]-exact_energies[0]),
        'hf_real_min':minima[0],
        'hf_imaginary_min':minima[1],
        'jacobian_condition':float(np.linalg.cond(jacobian)),
        'eom_real_min':float(np.min(np.linalg.eigvals(jacobian).real)),
        'amplitude_norm':float(np.linalg.norm(amplitudes)),
        'lambda_norm':float(np.linalg.norm(multipliers)),
        'biorthogonal_norm':float(left@right),
        'rdm_trace':float(np.trace(density)),
        'pair_entry_max':float(np.max(np.abs(matrix))),
        'pair_frobenius':float(np.linalg.norm(matrix))
    }

started=time.time()
base=np.array(payload['pair_matrix'])
base_amplitudes=np.array(payload['amplitudes'])
points=[base]
for row in range(15):
    for column in range(row,15):
        direction=np.zeros((15,15))
        direction[row,column]=.001/(1 if row==column else np.sqrt(2))
        direction[column,row]=direction[row,column]
        points.extend((base+direction,base-direction))
records=[]
for index,matrix in enumerate(points):
    if index:
        hamiltonian=make_hamiltonian(matrix)
        def combined(amplitudes):
            values=equations(hamiltonian,amplitudes)
            return values[0],values[1]
        answer=root(combined,base_amplitudes,jac=True,method='hybr',options={'xtol':2e-11,'maxfev':250})
        amplitudes=answer.x
    else:
        amplitudes=base_amplitudes
    records.append({'point':index,**diagnostic(matrix,amplitudes)})
upper=['energy_error','cc_residual','lambda_residual','rdm_dad','jacobian_condition','amplitude_norm','lambda_norm','pair_entry_max','pair_frobenius']
lower=['occupation_violation','ground_overlap','reference_weight','fci_gap','hf_real_min','hf_imaginary_min','eom_real_min']
summary={key:max(row[key] for row in records) for key in upper}
summary.update({key:min(row[key] for row in records) for key in lower})
report={'construction':'64-dimensional Fock operators, projected sector, scipy matrix exponentials','point_count':len(points),
        'seconds':time.time()-started,'extrema':summary,'points':records}
Path(output).write_text(json.dumps(report,indent=2))
print(json.dumps({key:value for key,value in report.items() if key!='points'},indent=2),flush=True)
