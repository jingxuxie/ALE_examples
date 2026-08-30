import json
import itertools
from pathlib import Path
import numpy as np
from oracle import DeterminantCC
from api import artifact

oracle = DeterminantCC()
for filename in ['basequiet_best.json', 'finite_0.json']:
    data = json.loads(Path(filename).read_text())
    original = np.array(data['pair_matrix'])
    for pairing in itertools.permutations([3,4,5]):
        permutation = [0,1,2] + list(pairing)
        matrix = np.zeros((15,15))
        for row, first_pair in enumerate(oracle.pairs):
            first = [permutation[orbital] for orbital in first_pair]
            first_sign = 1 if first[0] < first[1] else -1
            first_row = oracle.pairs.index(tuple(sorted(first)))
            for column, second_pair in enumerate(oracle.pairs):
                second = [permutation[orbital] for orbital in second_pair]
                second_sign = 1 if second[0] < second[1] else -1
                second_column = oracle.pairs.index(tuple(sorted(second)))
                matrix[first_row,second_column] = first_sign * second_sign * original[row,column]
        hamiltonian = oracle.hamiltonian(data['orbital_energies'],matrix)[0]
        _, vectors = np.linalg.eigh(hamiltonian)
        exact = vectors[:,0]/vectors[0,0]
        initial = exact[oracle.targets].copy()
        singles = (initial[:9]@oracle.generator_flat[:9]).reshape(20,20)
        initial[9:] -= (singles@singles@oracle.ref)[oracle.targets[9:]]/2
        result=oracle.solve(hamiltonian,initial)
        label=''.join(str(value) for value in pairing)
        output=f'{Path(filename).stem}_{label}.json'
        Path(output).write_text(json.dumps(artifact(matrix,result.amplitudes),indent=2))
        diagnostic=oracle.diagnostics(hamiltonian,result)
        print(output, diagnostic['occupation_violation'],diagnostic['ground_overlap'],diagnostic['hf_real_min'],diagnostic['energy_error'])
