import ctypes
from pathlib import Path
import numpy as np

rng = np.random.default_rng(736551)
pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
library = ctypes.CDLL(str(Path('kernel.so').resolve()))
library.predict.argtypes = [pointer, pointer, ctypes.c_int]
library.predict_p.argtypes = [pointer, pointer, pointer, ctypes.c_int]
all_invariants = []
all_momenta = []
all_family = []
for family in range(5):
    count = 50000
    energies = rng.gamma(2, 1, size=(count, 5)).astype(np.longdouble)
    directions = rng.normal(size=(count, 5, 3)).astype(np.longdouble)
    directions /= np.linalg.norm(directions, axis=2, keepdims=True)
    if family == 1:
        energies[:, 3] *= 10 ** rng.uniform(-4.5, -1, size=count)
    if family in (2, 3, 4):
        pairs = [(2, 3)]
        if family == 3:
            pairs += [(0, 4)]
        if family == 4:
            pairs += [(2, 4)]
        for source, target in pairs:
            width = 10 ** rng.uniform(-2.5, -.35, size=(count, 1))
            directions[:, target] = directions[:, source] + width * directions[:, target]
            directions[:, target] /= np.linalg.norm(directions[:, target], axis=1, keepdims=True)
    momenta = directions * energies[:, :, None]
    invariants = np.stack([2 * energies[:, left] * energies[:, right] * (1 - np.sum(directions[:, left] * directions[:, right], axis=1)) for left in range(5) for right in range(left+1, 5)], axis=1)
    mass = np.sqrt(invariants.sum(axis=1))
    invariants /= mass[:, None] ** 2
    total_energy = energies.sum(axis=1)
    total_momentum = momenta.sum(axis=1)
    velocity = total_momentum / total_energy[:, None]
    gamma = total_energy / mass
    projection = np.sum(momenta * velocity[:, None, :], axis=2)
    coefficient = gamma[:, None] ** 2 / (gamma[:, None]+1) * projection - gamma[:, None] * energies
    momenta += coefficient[:, :, None] * velocity[:, None, :]
    energies = gamma[:, None] * (energies - projection)
    points = np.concatenate([momenta, energies[:, :, None]], axis=2) / mass[:, None, None]
    mask = np.min(invariants, axis=1) > 1e-10
    invariants = np.ascontiguousarray(invariants[mask], dtype=np.float64)
    points = np.ascontiguousarray(points[mask], dtype=np.float64)
    output = np.empty(len(invariants))
    reference = np.empty(len(invariants))
    library.predict(invariants, output, len(output))
    library.predict_p(invariants, points, reference, len(output))
    error = output-reference
    print(family, len(error), 'rmse', np.mean(error**2)**.5, 'max', np.max(np.abs(error)), 'q99', np.quantile(abs(error), .99), flush=True)
    all_invariants.append(invariants)
    all_momenta.append(points)
    all_family.append(np.full(len(invariants), family))
np.savez('_stress.npz', s=np.concatenate(all_invariants), p=np.concatenate(all_momenta), family=np.concatenate(all_family))
