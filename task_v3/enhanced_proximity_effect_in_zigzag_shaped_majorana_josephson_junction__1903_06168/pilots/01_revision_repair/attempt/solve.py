#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import sys

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent / 'participant' / 'workspace'
sys.path.insert(0, str(WORKSPACE))

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.sparse.linalg import ArpackNoConvergence, eigsh

from compat import load_source
from geometry import assemble, barrier_response


def excitation_gap(system, params, grid_points):
    def matrix_at(momentum):
        return system.hamiltonian_submatrix(
            params=dict(params, k_x=float(momentum)), sparse=True
        ).tocsc()

    matrix_zero = matrix_at(0)
    matrix_pi = matrix_at(np.pi)
    constant = (matrix_zero + matrix_pi) * 0.5
    cosine = (matrix_zero - matrix_pi) * 0.5
    sine = matrix_at(np.pi / 2) - constant
    for matrix in (constant, cosine, sine):
        matrix.eliminate_zeros()
    indices = np.arange(constant.shape[0], dtype=float)
    initial = np.cos(0.47 * indices) + 1j * np.sin(0.61 * indices)
    cache = {}

    def energy(momentum):
        momentum = float(momentum)
        if momentum not in cache:
            matrix = constant + np.cos(momentum) * cosine + np.sin(momentum) * sine
            try:
                energies = eigsh(
                    matrix, k=4, sigma=0, which='LM', v0=initial,
                    tol=1e-10, maxiter=2000, return_eigenvectors=False
                )
            except (ArpackNoConvergence, RuntimeError):
                energies = eigsh(
                    matrix, k=8, sigma=1e-9, which='LM', v0=initial,
                    tol=1e-11, ncv=40, maxiter=10000,
                    return_eigenvectors=False
                )
            cache[momentum] = float(np.min(np.abs(energies)))
        return cache[momentum]

    momenta = np.linspace(0.0, np.pi, grid_points)
    energies = np.array([energy(momentum) for momentum in momenta])
    best = float(np.min(energies))
    for index in range(grid_points):
        if index > 0 and energies[index] > energies[index - 1]:
            continue
        if index + 1 < grid_points and energies[index] > energies[index + 1]:
            continue
        lower = momenta[max(0, index - 1)]
        upper = momenta[min(grid_points - 1, index + 1)]
        optimum = minimize_scalar(
            energy, bounds=(lower, upper), method='bounded',
            options={'xatol': 1e-8, 'maxiter': 80}
        )
        best = min(best, float(optimum.fun))
    return best


def solve(request, output_parent):
    if request['version'] != 1:
        raise ValueError('Unsupported request version')
    source = load_source(ROOT / 'repaired_zigzag.py', output_parent)
    system = assemble(source, request['geometry'])
    params = dict(source.constants, **request['model'], k_x=0)
    if request['kind'] == 'barrier':
        response = barrier_response(system, params, request['probes'])
        return {'version': 1, 'response': response}
    if request['kind'] == 'gap':
        if not request['geometry']['infinite']:
            raise ValueError('Gap requests require a periodic geometry')
        gap = excitation_gap(system, params, request['grid_points'])
        return {'version': 1, 'gap': gap}
    raise ValueError('Unknown request kind')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    arguments = parser.parse_args()
    request = json.loads(arguments.input.read_text())
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    result = solve(request, arguments.output.parent)
    arguments.output.write_text(json.dumps(result, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
