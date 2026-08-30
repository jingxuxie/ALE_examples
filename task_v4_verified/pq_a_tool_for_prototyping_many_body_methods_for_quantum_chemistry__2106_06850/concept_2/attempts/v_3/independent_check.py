import itertools
import json
from pathlib import Path
import numpy as np
from scipy.linalg import expm

source = json.loads(Path('rotated.json').read_text())
pair_matrix = np.array(source['pair_matrix'])
amplitudes = np.array(source['amplitudes'])
sector = np.array([bits for bits in range(64) if bits.bit_count() == 3])
reference = int(np.flatnonzero(sector == 7)[0])
pairs = list(itertools.combinations(range(6), 2))
annihilators = []
for orbital in range(6):
    operator = np.zeros((64, 64))
    for bits in range(64):
        if bits & (1 << orbital):
            operator[bits ^ (1 << orbital), bits] = (-1)**((bits & ((1 << orbital)-1)).bit_count())
    annihilators.append(operator)
creators = [operator.T for operator in annihilators]
tensor = np.zeros((6,6,6,6))
for row, (first,second) in enumerate(pairs):
    for column, (third,fourth) in enumerate(pairs):
        value = pair_matrix[row,column]
        tensor[first,second,third,fourth] = value
        tensor[second,first,third,fourth] = -value
        tensor[first,second,fourth,third] = -value
        tensor[second,first,fourth,third] = value
one_body = np.diag(source['orbital_energies'])-sum(tensor[:,occupied,:,occupied] for occupied in range(3))
full_hamiltonian = np.zeros((64,64))
one = np.empty((6,6,20,20))
for first in range(6):
    for second in range(6):
        operator = creators[first] @ annihilators[second]
        full_hamiltonian += one_body[first,second]*operator
        one[first,second] = operator[np.ix_(sector,sector)]
for row, (first,second) in enumerate(pairs):
    for column, (third,fourth) in enumerate(pairs):
        full_hamiltonian += pair_matrix[row,column]*(creators[first] @ creators[second] @ annihilators[fourth] @ annihilators[third])
hamiltonian = full_hamiltonian[np.ix_(sector,sector)]
generators = []
targets = []
for rank in (1,2):
    for holes in itertools.combinations(range(3),rank):
        for particles in itertools.combinations(range(3,6),rank):
            operator = np.eye(64)
            for hole in holes:
                operator = annihilators[hole] @ operator
            for particle in reversed(particles):
                operator = creators[particle] @ operator
            operator = operator[np.ix_(sector,sector)]
            target = int(np.argmax(abs(operator[:,reference])))
            operator *= operator[target,reference]
            generators.append(operator)
            targets.append(target)
targets = np.array(targets)
cluster = np.einsum('k,kij->ij', amplitudes, generators)
positive, negative = expm(cluster), expm(-cluster)
transformed = negative @ hamiltonian @ positive
commutators = np.array([transformed @ generator-generator @ transformed for generator in generators])
jacobian = commutators[:,targets,reference].T
gradient = commutators[:,reference,reference]
multipliers = np.linalg.solve(jacobian.T,-gradient)
left_row = np.zeros(20)
left_row[reference] = 1
left_row[targets] = multipliers
left = left_row @ negative
right = positive[:,reference]
gamma = np.einsum('i,pqij,j->pq',left,one,right)
occupations, orbitals = np.linalg.eigh((gamma+gamma.T)/2)
energies, states = np.linalg.eigh(hamiltonian)
fock = one_body+sum(tensor[:,occupied,:,occupied] for occupied in range(3))
summary = {
    'construction': '64-dimensional Fock-space products and scipy.linalg.expm',
    'cc_residual': float(max(abs(transformed[targets,reference]))),
    'lambda_residual': float(max(abs(jacobian.T@multipliers+gradient))),
    'energy_error': float(abs(transformed[reference,reference]-energies[0])),
    'ground_overlap': float((states[:,0]@right)**2/(right@right)),
    'rdm_dad': float(np.linalg.norm(gamma-gamma.T)/np.sqrt(3)),
    'occupations': occupations.tolist(),
    'witness_orbital': orbitals[:,0].tolist(),
    'witness_population': float(orbitals[:,0]@gamma@orbitals[:,0]),
    'biorthogonal_norm': float(left@right),
    'particle_number': float(np.trace(gamma)),
    'fock_error': float(np.max(abs(fock-np.diag(source['orbital_energies'])))),
}
assert summary['cc_residual'] < 2e-9
assert summary['lambda_residual'] < 2e-9
assert summary['energy_error'] < 1e-4
assert summary['rdm_dad'] < .001
assert summary['witness_population'] < -.02
Path('independent_validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
