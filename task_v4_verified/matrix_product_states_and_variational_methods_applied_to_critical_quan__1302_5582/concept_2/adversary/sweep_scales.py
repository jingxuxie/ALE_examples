import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluator" / "hidden"))
from trusted_physics import SIGMA_X, SIGMA_Z, apply_transfer, load_tensor, metrics, stationary


def exact_sequence(maximum):
    current = 0.0
    prefix = 0.0
    values = []
    for distance in range(1, maximum + 1):
        current += np.log(2.0 / np.pi) - prefix
        values.append(np.exp(current))
        prefix += np.log1p(-1.0 / (4.0 * distance**2))
    return np.asarray(values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--maximum", type=int, default=2048)
    arguments = parser.parse_args()
    tensor = load_tensor(arguments.state)
    original = metrics(tensor)
    density, _, _, _ = stationary(tensor)
    identity = np.eye(tensor.shape[1], dtype=complex)
    sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    operators = {"xx": SIGMA_X, "yy": sigma_y, "zz_connected": SIGMA_Z}
    exact_xx = exact_sequence(arguments.maximum)
    distances = np.arange(1, arguments.maximum + 1)
    targets = {"xx": exact_xx, "yy": -exact_xx / (4 * distances**2 - 1), "zz_connected": 4 / (np.pi**2 * (4 * distances**2 - 1))}
    transverse = original["transverse_magnetization"]
    profiles = {}
    windows = [bound for bound in (16, 32, 64, 128, 256, 512, 1024, 2048) if bound <= arguments.maximum]
    for name, operator in operators.items():
        environment = apply_transfer(tensor, identity, operator)
        values = []
        for distance in distances:
            value = float(np.trace(density @ apply_transfer(tensor, environment, operator)).real)
            if name == "zz_connected":
                value -= transverse**2
            values.append(value)
            environment = apply_transfer(tensor, environment)
        errors = np.abs(np.asarray(values) / targets[name] - 1)
        profiles[name] = {
            "window_max_relative_errors": {str(bound): float(max(errors[:bound])) for bound in windows},
            "first_distance_above_10pct": int(np.argmax(errors > 0.1) + 1) if np.any(errors > 0.1) else None,
            "first_distance_above_50pct": int(np.argmax(errors > 0.5) + 1) if np.any(errors > 0.5) else None,
            "values": values,
        }
    result = {
        "state": str(Path(arguments.state).resolve()),
        "maximum_distance": arguments.maximum,
        "original_energy_excess": original["energy_excess"],
        "correlation_length": original["correlation_length"],
        "profiles": profiles,
        "search_type": "exact infinite-chain operator and length-scale sweep; no changed Hamiltonian or mislabeled data",
        "ratchet_rule": "Use only a solved champion's measured failure to define a disclosed new contract. This sweep alone does not change the original target.",
    }
    Path(arguments.output).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"energy_excess": result["original_energy_excess"], "correlation_length": result["correlation_length"], "profiles": {name: {key: value for key, value in profile.items() if key != "values"} for name, profile in profiles.items()}}, indent=2))


if __name__ == "__main__":
    main()
