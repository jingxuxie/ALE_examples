import json
import math
import os
from pathlib import Path
import subprocess
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True

import numpy as np
from numpy.polynomial.legendre import leggauss
from solve import summarize, write_model


def exact_pair(case, theta):
    nodes, weights = leggauss(160)
    longitudinal = np.sqrt((nodes + 1) / 2)
    azimuth = np.arange(512) * (2 * math.pi / 512)
    transverse = np.sqrt(1 - longitudinal**2)
    spin_x = transverse[:, None] * np.cos(azimuth)
    spin_y = transverse[:, None] * np.sin(azimuth)
    spin_z = np.broadcast_to(longitudinal[:, None], spin_x.shape)
    first = np.stack([spin_x, spin_y, spin_z], axis=-1)
    second = np.stack([-spin_x, -spin_y, spin_z], axis=-1)
    rotation = np.array([[math.cos(theta), 0, math.sin(theta)],
                         [0, 1, 0], [-math.sin(theta), 0, math.cos(theta)]])
    first = first @ rotation.T
    second = second @ rotation.T
    exchange, axial = case["bonds"][0][2:]
    energy = -exchange * (first * second).sum(axis=-1) - axial * first[..., 2] * second[..., 2]
    torque = -axial * (first[..., 0] * second[..., 2] + first[..., 2] * second[..., 0])
    for spin, tensor in zip([first, second], case["onsite"]):
        quadratic = np.array([[tensor[0], tensor[3], tensor[4]],
                              [tensor[3], tensor[1], tensor[5]],
                              [tensor[4], tensor[5], tensor[2]]])
        energy -= np.einsum("...i,ij,...j->...", spin, quadratic, spin) + tensor[6] * (spin**4).sum(axis=-1)
        field = 2 * spin @ quadratic + 4 * tensor[6] * spin**3
        torque += np.cross(spin, field)[..., 1]
    probability = weights[:, None] * np.exp(-energy / case["temperature"])
    probability /= probability.sum()
    return float((probability * torque).sum() / 2), float((probability * longitudinal[:, None]).sum())


def main():
    root = Path(__file__).resolve().parent
    case = {"n_spins": 2, "bonds": [[0, 1, 0.7, 0.2]], "temperature": 0.8, "seed": 719311,
            "onsite": [[0.17, -0.13, 0.29, 0, 0, 0, 0.18],
                       [-0.22, 0.05, 0.15, 0, 0, 0, 0.09]]}
    angles = [0.23, 0.67, 1.16]
    write_model(case, angles, root / "pair_test.model")
    expected = np.array([exact_pair(case, angle) for angle in angles])
    print("Exact pair torque and magnetization:", expected, flush=True)
    for kernel in ["projected", "pairs", "cluster"]:
        path = root / f"pair_test_{kernel}.txt"
        subprocess.run([str(root / "sampler"), str(root / "pair_test.model"), str(path), "9", kernel], check=True)
        data = np.loadtxt(path)
        _, torque, error = summarize(data)
        measured_magnetization = np.array([data[data[:, 0] == index, 5].mean() for index in range(len(angles))])
        print(kernel, "torque", torque, "sem", error, "m", measured_magnetization, flush=True)
        assert np.all(abs(torque - expected[:, 0]) < 6 * error + 2e-5)
        assert np.max(abs(measured_magnetization - expected[:, 1])) < 0.002
    case["bonds"] = [[0, 1, 0.0, 0.0]]
    case["onsite"] = [[0.0] * 7] * 2
    write_model(case, [0.0], root / "pair_isotropic.model")
    subprocess.run([str(root / "sampler"), str(root / "pair_isotropic.model"),
                    str(root / "pair_isotropic.txt"), "2"], check=True)
    data = np.loadtxt(root / "pair_isotropic.txt")
    assert np.all(data[:, 4] == 0)
    assert abs(np.mean(data[:, 5]) - 2 / 3) < 0.003
    print("All exact-ensemble checks passed.")


if __name__ == "__main__":
    main()
