import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
import json
import time
from pathlib import Path
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu, eigsh
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'participant' / 'workspace'))
from physics import ForwardModel, feasibility, geometry_arrays, nominal_scenario


def geometry(request, amplitude=200, width=140, harmonics=1, kind='triangle', offset=0, modulation=0):
    grid = request['grid']
    nx, ny, spacing = grid['nx'], grid['ny'], grid['spacing_nm']
    period = nx * spacing
    columns = np.arange(nx)
    phase = (columns * harmonics / nx) % 1
    if kind == 'triangle':
        center = amplitude * (1 - 4 * np.minimum(phase, 1 - phase))
        slope = 4 * amplitude * harmonics / period
        halfwidth = width / 2 * np.sqrt(1 + slope ** 2)
    else:
        center = amplitude * np.cos(2 * np.pi * phase)
        slope = -2 * np.pi * amplitude * harmonics / period * np.sin(2 * np.pi * phase)
        halfwidth = width / 2 * np.sqrt(1 + slope ** 2)
    halfwidth = halfwidth + modulation * np.cos(4 * np.pi * phase)
    positions = (np.arange(ny) - (ny - 1) / 2) * spacing
    return {'sc_top': positions[:, None] >= center[None, :] + offset + halfwidth,
            'sc_bottom': positions[:, None] <= center[None, :] + offset - halfwidth}


def projection(nx, ny, momentum):
    rows, columns, values = [], [], []
    visited = set()
    count = 0
    for column in range(nx):
        reflected = (-column) % nx
        sign = -1 if momentum != 0 and column != 0 else 1
        for row in range(ny):
            for component in range(4):
                index = (column * ny + row) * 4 + component
                partner = (reflected * ny + row) * 4 + ((component + 2) % 4)
                if index in visited:
                    continue
                visited.update((index, partner))
                rows.extend((index, partner))
                columns.extend((count, count))
                values.extend((1 / np.sqrt(2), sign / np.sqrt(2)))
                count += 1
    return sparse.csc_matrix((values, (rows, columns)), shape=(4 * nx * ny, count))


def permutation_sign(permutation):
    visited = np.zeros(len(permutation), dtype=bool)
    cycles = 0
    for start in range(len(permutation)):
        if visited[start]:
            continue
        cycles += 1
        current = start
        while not visited[current]:
            visited[current] = True
            current = permutation[current]
    return -1 if (len(permutation) - cycles) % 2 else 1


def fast_topology(model, check=False):
    signs = []
    for momentum in (0, np.pi):
        basis = projection(model.nx, model.ny, momentum)
        matrix = model.hamiltonian(momentum)
        projected = (basis.T @ matrix @ basis).tocsc()
        if check:
            error = matrix @ basis - basis @ projected
            print('projection residual', abs(error).max(), flush=True)
        factor = splu(projected)
        diagonal = factor.U.diagonal()
        phase = np.prod(diagonal / np.abs(diagonal)) * permutation_sign(factor.perm_r) * permutation_sign(factor.perm_c)
        signs.append(phase)
    if check:
        print('det signs', signs, flush=True)
    return int(np.sign((signs[0] * signs[1]).real))


def main():
    with open(Path(__file__).resolve().parent.parent / 'participant' / 'input' / 'example.json') as handle:
        request = json.load(handle)
    scenario = nominal_scenario(request)
    masks = geometry_arrays(request, request['baseline_geometry'])
    model = ForwardModel(request, masks, scenario)
    started = time.monotonic()
    print('baseline feasibility', feasibility(request, masks), flush=True)
    print('fast topology', fast_topology(model, check=True), 'seconds', time.monotonic()-started, flush=True)
    started = time.monotonic()
    print('exact topology', model.topological_invariant(), 'seconds', time.monotonic()-started, flush=True)
    started = time.monotonic()
    print('gap', model.spectral_gap(np.linspace(0,np.pi,9)), 'seconds',time.monotonic()-started,flush=True)
    for amplitude, width in [(200,140),(300,140),(200,200),(300,200),(400,120),(300,100),(100,120)]:
        masks = geometry(request, amplitude, width)
        print('candidate', amplitude, width, feasibility(request, masks), flush=True)
        model = ForwardModel(request, masks, scenario)
        started = time.monotonic()
        print('topology', fast_topology(model), 'gap', model.spectral_gap(np.linspace(0,np.pi,9)), 'seconds',time.monotonic()-started,flush=True)


if __name__ == '__main__':
    main()
