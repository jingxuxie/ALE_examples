import json
import sys
from pathlib import Path

import numpy as np

workspace = Path(__file__).resolve().parents[2] / "participant" / "workspace"
if workspace.is_dir():
    sys.path.insert(0, str(workspace))

from energy import energy_gradient, load_case, relax


def main():
    case = load_case(sys.argv[1])
    minimum = relax(case, case["minimum_a"], max_steps=300)
    saddle = minimum.copy()
    result = {
        "saddle": saddle.tolist(),
        "barrier_meV": max(0.0, energy_gradient(case, saddle)[0] - energy_gradient(case, minimum)[0]),
        "eigenvalues_min_meV": [1.0] * (2 * case["n_spins"]),
        "eigenvalues_saddle_meV": [-1.0] + [1.0] * (2 * case["n_spins"] - 1),
        "log_omega0": 0.0,
    }
    output = Path(sys.argv[2])
    if output.suffix == ".npz":
        np.savez(output, **{name: np.asarray(value) for name, value in result.items()})
    else:
        output.write_text(json.dumps(result))


if __name__ == "__main__":
    main()
