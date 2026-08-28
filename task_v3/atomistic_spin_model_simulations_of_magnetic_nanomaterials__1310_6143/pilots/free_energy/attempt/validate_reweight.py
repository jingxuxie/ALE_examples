import math
import os
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True

import numpy as np
from reweight import evaluate, fit_mbar, reweight, symmetric_potentials


def main():
    random = np.random.default_rng(771090)
    temperature = 0.8
    angles = np.arange(1, 16) * math.pi / 32
    requested = np.arange(9) * math.pi / 16
    mean = np.array([0, 0, 1.7, 0, -0.7, 0])
    variance = np.array([0, 0, 0.15, 0.3, 0.03, 0.09])
    records = []
    count = 4096
    for index, angle in enumerate(angles):
        basis = np.array([0, 0, np.cos(2 * angle), np.sin(2 * angle),
                          np.cos(4 * angle), np.sin(4 * angle)])
        coefficients = mean - variance * basis / temperature + random.normal(size=(count, 6)) * np.sqrt(variance)
        records.append(np.column_stack([np.full(count, index), np.arange(count) // 64, coefficients]))
    records = np.concatenate(records)
    result = reweight(records, angles, requested, temperature, 1)
    basis = np.stack([np.zeros_like(requested), np.zeros_like(requested),
                      np.cos(2 * requested), np.sin(2 * requested),
                      np.cos(4 * requested), np.sin(4 * requested)], axis=1)
    derivative = np.stack([np.zeros_like(requested), np.zeros_like(requested),
                           -2 * np.sin(2 * requested), 2 * np.cos(2 * requested),
                           -4 * np.sin(4 * requested), 4 * np.cos(4 * requested)], axis=1)
    exact_free = basis @ mean - (basis**2 @ variance) / (2 * temperature)
    exact_free -= exact_free[0]
    exact_torque = -derivative @ mean + (derivative * basis) @ variance / temperature
    print("Gaussian exact free energy:", exact_free)
    print("Gaussian reweighted free energy:", result["free_energy"])
    print("Gaussian exact torque:", exact_torque)
    print("Gaussian reweighted torque:", result["torque"])
    assert np.all(abs(np.asarray(result["free_energy"]) - exact_free) < 6 * np.asarray(result["free_energy_sem"]) + 0.004)
    assert np.all(abs(np.asarray(result["torque"]) - exact_torque) < 6 * np.asarray(result["torque_sem"]) + 0.008)
    potential, _ = symmetric_potentials(records[:, 2:], angles, temperature)
    fitted, denominator = fit_mbar(potential, records[:, 0].astype(int))
    offsets = np.linspace(-400, 400, len(angles))
    shifted, _ = fit_mbar(potential + offsets, records[:, 0].astype(int))
    assert np.max(np.abs(shifted - fitted - offsets + offsets[0])) < 1e-7
    center, step = 0.631, 1e-5
    query = np.array([0, center - step, center, center + step, -center, math.pi + center])
    potential, observable = symmetric_potentials(records[:, 2:], query, temperature)
    torque, free, _ = evaluate(potential, observable, denominator, temperature, 1)
    assert abs(torque[2] + (free[3] - free[1]) / (2 * step)) < 1e-7
    assert abs(free[4] - free[2]) < 1e-12
    assert abs(free[5] - free[2]) < 1e-12
    assert abs(torque[4] + torque[2]) < 1e-12
    print("Reweighting, symmetry, and torque/free-energy derivative checks passed.")


if __name__ == "__main__":
    main()
