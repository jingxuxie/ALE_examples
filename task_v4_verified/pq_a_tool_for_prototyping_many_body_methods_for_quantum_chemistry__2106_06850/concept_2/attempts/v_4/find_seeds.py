import os
import json
import time
import numpy as np
from pathlib import Path
from oracle import DeterminantCC
from api import artifact

oracle = DeterminantCC()
epsilon = np.array([-1.2, -.9, -.5, .5, .9, 1.2])
axes = []
for row in range(15):
    for column in range(row, 15):
        first = sorted(orbital % 3 for orbital in oracle.pairs[row])
        second = sorted(orbital % 3 for orbital in oracle.pairs[column])
        if first == second:
            direction = np.zeros((15, 15))
            direction[row, column] = direction[column, row] = 1. if row == column else 1 / np.sqrt(2)
            axes.append(direction)
axes = np.array(axes)
hbase = oracle.hamiltonian(epsilon, np.zeros((15, 15)))[0]
haxes = np.array([oracle.hamiltonian(np.zeros(6), direction)[0] for direction in axes])
hfbase = np.array(oracle.hf_stability(hbase))
hfaxes = np.array([oracle.hf_stability(derivative) for derivative in haxes])
rng = np.random.default_rng(7745)
started = time.monotonic()
best = []
count = 0
for trial in range(20000):
    values = rng.normal(size=len(axes)) * rng.uniform(.2, .9)
    matrix = np.einsum('k,kij->ij', values, axes)
    if np.max(abs(matrix)) > 1.48 or np.linalg.norm(matrix) > 6.8:
        continue
    real_hf, imag_hf = hfbase + np.einsum('k,kbij->bij', values, hfaxes)
    curvature = min(np.linalg.eigvalsh(real_hf)[0], np.linalg.eigvalsh(imag_hf)[0])
    if curvature < -.05:
        continue
    hamiltonian = hbase + np.einsum('k,kij->ij', values, haxes)
    result = oracle.solve(hamiltonian)
    if not result.converged or np.linalg.norm(result.amplitudes) > 1.3:
        continue
    diagnostic = oracle.diagnostics(hamiltonian, result)
    if diagnostic['ground_overlap'] < .975 or diagnostic['reference_weight'] < .38 or diagnostic['jacobian_condition'] > 150:
        continue
    count += 1
    minimum = diagnostic['occupations'][0]
    merit = minimum + .03 * diagnostic['energy_error'] + .01 * diagnostic['rdm_dad']
    if minimum < -.00001 and (len(best) < 40 or merit < best[-1][0]):
        filename = f'seed_{trial}.json'
        Path(filename).write_text(json.dumps(artifact(matrix, result.amplitudes)))
        best.append((merit, filename, diagnostic))
        best.sort(key=lambda item: item[0])
        best = best[:40]
        Path('seeds.json').write_text(json.dumps(best, indent=2))
        print(trial, count, 'minocc', minimum, 'error', diagnostic['energy_error'], 'dad', diagnostic['rdm_dad'], 'overlap', diagnostic['ground_overlap'], 'seconds', time.monotonic()-started, flush=True)
    if trial % 1000 == 0:
        print('progress', trial, count, 'best', best[0][:2] if best else None, flush=True)
print('finished', count, time.monotonic()-started, flush=True)
