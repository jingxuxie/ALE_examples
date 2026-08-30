import importlib.util
import json
from pathlib import Path
import sys
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
import model


parameters = [-1., 1., 1., 1., 1., -.3, -.1, .1, .3] + [0.] * 4 + [.16] * 8 + [.2, 1.1, -1.4, 2.2]
blocks = model.coefficients(parameters)
generator = np.random.default_rng(782939)
errors = []
hermitian_error = 0.
for trial in range(12):
    position = generator.uniform(-np.pi, np.pi, 2)
    def hamiltonian(momentum):
        return (blocks[0] + np.cos(momentum[0]) * blocks[1] + np.sin(momentum[0]) * blocks[2]
                + np.cos(momentum[1]) * blocks[3] + np.sin(momentum[1]) * blocks[4])
    matrix = hamiltonian(position)
    hermitian_error = max(hermitian_error, float(np.linalg.norm(matrix - matrix.conj().T)))
    for axis in (0, 1):
        displacement = np.zeros(2)
        displacement[axis] = 1e-5
        numerical = (hamiltonian(position + displacement) - hamiltonian(position - displacement)) / 2e-5
        analytical = -np.sin(position[axis]) * blocks[1 + 2 * axis] + np.cos(position[axis]) * blocks[2 + 2 * axis]
        errors.append(float(np.linalg.norm(numerical - analytical)))
analytic_parameters = np.array(parameters)
analytic_parameters[13:21] = 0.
analytic = model.diagnose(analytic_parameters, 81)
expected_chern = 1.
assert hermitian_error < 1e-13
assert max(errors) < 1e-8
assert abs(analytic['full'] - expected_chern) < 1e-8
assert abs(analytic['chern'] - expected_chern) < 1e-8
assert np.max(np.abs(analytic['windows'])) < 1e-12
matrix, derivative_x, derivative_y = model.sample(parameters, 17)
values, vectors = np.linalg.eigh(matrix)
independent_terms = []
for band in range(1, 6):
    target, partner = vectors[..., :, 0], vectors[..., :, band]
    first = np.einsum('...a,...ab,...b->...', target.conj(), derivative_x, partner)
    second = np.einsum('...a,...ab,...b->...', partner.conj(), derivative_y, target)
    independent_terms.append(float((-2 * np.imag(first * second) / (values[..., band] - values[..., 0]) ** 2).mean() * 2 * np.pi))
reported = model.diagnose(parameters, 17)
assert np.max(np.abs(np.array(independent_terms) - reported['contributions'])) < 1e-12
spec = importlib.util.spec_from_file_location('checker', ROOT / 'evaluator' / 'evaluate.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
controls = {}
for name, payload in [('nan', {'parameters': [float('nan')] * 25}),
                      ('bad_shape', {'parameters': [1.]}),
                      ('booleans', {'parameters': [True] * 25}),
                      ('bounds', {'parameters': [200.] * 25}),
                      ('decoupled', {'parameters': analytic_parameters.tolist()})]:
    filename = ROOT / 'adversary' / (name + '.json')
    filename.write_text(json.dumps(payload))
    try:
        outcome = checker.evaluate(filename)
        rejected = not outcome['passed']
    except ValueError:
        rejected = True
    controls[name] = rejected
assert all(controls.values())
result = {'valid': True, 'max_derivative_error': max(errors), 'hermitian_error': hermitian_error,
          'analytic_decoupled_chern': analytic['chern'], 'analytic_full_response': analytic['full'],
          'analytic_truncated_response': analytic['windows'], 'negative_controls': controls,
          'independent_transition_sum_error': float(np.max(np.abs(np.array(independent_terms) - reported['contributions'])))}
(ROOT / 'adversary' / 'validation.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
