import os
import sys
import time

START = time.monotonic(), time.process_time()
sys.dont_write_bytecode = True
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'

import argparse
import copy
import json

import numpy as np

from numerics import Budget, Model, Topology, conjugate_relax, dot
from sectors import HarmonicSectors, anneal


def solve(model, budget, progress=False):
    baseline, gradient = model.energy_gradient(model.initial)
    best_energy, best = baseline, model.initial.copy()
    if np.all(model.alpha >= 0):
        return np.zeros(model.size, dtype=np.complex128), 0
    if not len(Topology(model).holes):
        energy, field, rms = conjugate_relax(model, best, budget, tolerance=1e-13)
        return (field if energy <= baseline and rms < 0.0015 else best), 0
    try:
        reference = HarmonicSectors(model, best)
        projector = np.linalg.solve(reference.hessian, reference.projected.T * reference.weights)
    except (RuntimeError, np.linalg.LinAlgError):
        return best, 0
    initial_phase = model.phase(best)
    best_sector = np.zeros(len(reference.centers))
    adaptive_field, adaptive_sector = best, best_sector
    adaptive_energy = baseline
    seen = {tuple(best_sector)}
    archive = {tuple(best_sector): 0.0}
    trials = 0
    for iteration in range(24):
        if budget.remaining() < 6.5:
            break
        ordered = sorted(archive.items(), key=lambda item: item[1])
        if iteration % 4 == 2:
            basis = copy.copy(reference)
            basis.build(adaptive_field)
            origin = adaptive_sector
            hessian, linear = basis.hessian, basis.linear
        else:
            basis = reference
            origin = np.zeros(len(reference.centers))
            if iteration > 0 and len(archive) >= 12:
                strength = 0.5 if iteration % 4 == 3 else 1.0
                hessian, linear = reference.corrected(archive, strength)
            else:
                hessian, linear = basis.hessian, basis.linear
        starts = [np.asarray(sector) - origin for sector, energy in ordered[:32]]
        expanded = iteration % 2 == 1
        energies, changes = anneal(
            hessian, linear, basis.lower, basis.centers, budget,
            replicas=256 if expanded else 512, sweeps=200 if expanded else 300,
            seed=4 + iteration * 7919, starts=starts, expanded=expanded)
        if progress:
            print('round', iteration, 'best', best_energy, 'elapsed', budget.elapsed(), flush=True)
        batch = 0
        for change in changes:
            if budget.remaining() < 3.0:
                break
            requested = tuple(origin + change)
            if requested in seen:
                continue
            seen.add(requested)
            candidate = basis.candidate(change)
            energy, field, rms = conjugate_relax(model, candidate, budget, tolerance=1e-10)
            trials += 1
            batch += 1
            if np.isfinite(energy) and rms < 0.0015:
                coordinates = projector @ (model.phase(field) - initial_phase)
                sector = np.rint(coordinates)
                if np.max(abs(coordinates - sector)) < 0.01:
                    key = tuple(sector)
                    seen.add(key)
                    archive[key] = min(archive.get(key, np.inf), energy - baseline)
                    if energy < adaptive_energy:
                        adaptive_energy, adaptive_field, adaptive_sector = energy, field, sector
                if energy < best_energy:
                    best_energy, best, best_sector = energy, field, sector
                    if progress:
                        print('improvement', trials, energy, rms, budget.elapsed(), flush=True)
            if batch >= 40:
                break
    if budget.remaining() > 0.8:
        energy, field, rms = conjugate_relax(model, best, budget, maxiter=4000,
                                            tolerance=1e-14, reserve=0.6)
        if np.isfinite(energy) and energy <= best_energy and rms < 0.0015:
            best = field
    return best, trials


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--progress', action='store_true')
    arguments = parser.parse_args()
    budget = Budget(55.0, START)
    with open(arguments.input) as stream:
        model = Model(json.load(stream))
    field, trials = solve(model, budget, arguments.progress)
    with open(arguments.output, 'wb') as stream:
        np.savez_compressed(stream, psi=model.full(field))
    energy, gradient = model.energy_gradient(field)
    rms = np.sqrt(dot(gradient, gradient) / (2 * model.size))
    print('energy=%.12g gradient_rms=%.6g trials=%d elapsed=%.3f' %
          (energy, rms, trials, budget.elapsed()))


if __name__ == '__main__':
    main()
