import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import differential_evolution

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from physics import SIGMA_X, SIGMA_Z, apply_transfer, stationary


def tensor_for(angles):
    theta, phi = angles
    return np.array([[[np.cos(theta), 0.0], [0.0, np.cos(phi)]], [[0.0, np.sin(theta)], [np.sin(phi), 0.0]]])


def energy(angles):
    tensor = tensor_for(angles)
    density, _, _, _ = stationary(tensor)
    identity = np.eye(2)
    order = apply_transfer(tensor, apply_transfer(tensor, identity, SIGMA_X), SIGMA_X)
    transverse = apply_transfer(tensor, identity, SIGMA_Z)
    return float(-np.trace(density @ (order + transverse)).real)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    destination = Path(arguments.output)
    destination.mkdir(parents=True, exist_ok=True)
    result = differential_evolution(energy, [(0.002, 1.56), (0.002, 1.56)], seed=13025582, maxiter=100, popsize=12, tol=1e-10, polish=True)
    np.savez(destination / "state.npz", A=tensor_for(result.x))
    print({"energy": float(result.fun), "angles": result.x.tolist()})


if __name__ == "__main__":
    main()
