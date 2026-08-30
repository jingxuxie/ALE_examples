import json
import time
import numpy as np
from oracle import DeterminantCC
from api import CONSTRAINTS, artifact, robust_screen

oracle = DeterminantCC()
axes = []
for row in range(15):
    for column in range(row, 15):
        axis = np.zeros((15,15))
        axis[row,column] = axis[column,row] = 1 if row == column else 1/np.sqrt(2)
        axes.append(axis)
axes = np.array(axes)
haxes = np.array([oracle.hamiltonian(np.zeros(6), axis)[0] for axis in axes])
hzero = oracle.hamiltonian(CONSTRAINTS['orbital_energies'], np.zeros((15,15)))[0]
inverse = np.linalg.pinv(haxes.reshape(120,-1).T, rcond=1e-12)
print('rank', np.linalg.matrix_rank(haxes.reshape(120,-1)), flush=True)
source = json.load(open('candidate_73_0.json'))
matrix = np.array(source['pair_matrix'])
hamiltonian = oracle.hamiltonian(CONSTRAINTS['orbital_energies'],matrix)[0]
result = oracle.solve(hamiltonian,source['amplitudes'])
occupations = [[orbital for orbital in range(6) if bits & (1<<orbital)] for bits in oracle.bits]
rng = np.random.default_rng(8402)
best = 1e9
for trial in range(100):
    rotation = np.eye(6)
    for offset in [0,3]:
        block = np.linalg.qr(rng.normal(size=(3,3)))[0]
        block[:,0] *= np.linalg.det(block)
        rotation[offset:offset+3,offset:offset+3] = block
    sector = np.array([[np.linalg.det(rotation[np.ix_(row,column)]) for column in occupations] for row in occupations])
    desired = sector @ hamiltonian @ sector.T
    coordinates = inverse @ (desired-hzero).ravel()
    transformed = np.einsum('k,kij->ij', coordinates, axes)
    error = np.linalg.norm(hzero+np.einsum('k,kij->ij',coordinates,haxes)-desired)
    if trial == 0:
        print('fit', error,'norm',np.linalg.norm(transformed),'entry',np.max(abs(transformed)),flush=True)
    if error > 1e-9:
        break
    right = sector @ result.right
    initial = right[oracle.targets].copy()
    singles = np.zeros(18)
    singles[:9] = initial[:9]
    positive = oracle.exponentials(singles)[0]
    initial[9:] -= positive[oracle.targets[9:],0]
    solved = oracle.solve(desired, initial)
    multipliers,left,_ = oracle.lambda_state(solved)
    exact_values,exact_vectors=np.linalg.eigh(desired)
    gradient = np.einsum('i,kij,j->k',left,haxes,solved.right)-np.einsum('i,kij,j->k',exact_vectors[:,0],haxes,exact_vectors[:,0])
    value=np.max(abs(gradient))
    if value < best:
        best=value
        json.dump(artifact(transformed,solved.amplitudes),open('rotated.json','w'))
        print('rotation',trial,'gradient',value,'residual',solved.residual,'entry',np.max(abs(transformed)),'norm',np.linalg.norm(transformed),flush=True)
print('done',flush=True)
