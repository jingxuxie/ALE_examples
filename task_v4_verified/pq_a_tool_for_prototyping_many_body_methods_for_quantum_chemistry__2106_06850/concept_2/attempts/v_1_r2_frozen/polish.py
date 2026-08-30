import json
from pathlib import Path

import numpy as np
from scipy.optimize import root_scalar

from api import artifact, endpoint_failures, check_continuation
from optimize import Search


data = json.loads(Path('refined.json').read_text())
search = Search('high')
vector = np.array(data['pair_matrix'])[search.rows, search.cols]
initial = np.array(data['amplitudes'])
search.initial = initial.copy()
search.evaluate(vector)
result = search.result
positive, inverse = search.oracle.exponentials(result.amplitudes)
fixed_derivative = inverse @ search.basis @ positive
amplitude_derivative = np.linalg.solve(result.jacobian, -fixed_derivative[:, search.oracle.targets, search.oracle.reference].T).T
cluster_derivative = (amplitude_derivative @ search.oracle.generator_flat).reshape(120, 20, 20)
transformed_derivative = fixed_derivative + result.hbar @ cluster_derivative - cluster_derivative @ result.hbar
direction = transformed_derivative[:, -1, search.oracle.reference]
direction /= np.linalg.norm(direction)


def triple_residual(displacement):
    matrix = search.base + np.einsum('k,kij->ij', vector + displacement * direction, search.basis)
    solved = search.oracle.solve(matrix, initial, tolerance=2e-12, max_evaluations=250)
    assert solved.residual < 1e-10
    return solved.hbar[-1, search.oracle.reference]


solution = root_scalar(triple_residual, x0=0.0, x1=0.001, method='secant', xtol=1e-13)
assert solution.converged
pair_matrix = search.unpack(vector + solution.root * direction)
matrix = search.oracle.hamiltonian(search.epsilon, pair_matrix)[0]
solved = search.oracle.solve(matrix, initial, tolerance=2e-12, max_evaluations=250)
diagnostics = search.oracle.diagnostics(matrix, solved)
path = check_continuation(pair_matrix, solved.amplitudes, search.oracle)
assert not endpoint_failures(diagnostics)
assert path['passed'] and diagnostics['occupation_violation'] > 0.02
Path('exact_candidate.json').write_text(json.dumps(artifact(pair_matrix, solved.amplitudes), indent=2, allow_nan=False))
Path('exact_candidate.diagnostics.json').write_text(json.dumps(diagnostics, indent=2, allow_nan=False))
Path('exact_candidate.path.json').write_text(json.dumps(path, indent=2, allow_nan=False))
print('Displacement', solution.root)
print('Full residual', np.max(np.abs((matrix - solved.energy * np.eye(20)) @ solved.right)))
print('Energy error', diagnostics['energy_error'], 'Overlap', diagnostics['ground_overlap'])
print('Violation', diagnostics['occupation_violation'], 'Path', path['passed'])
