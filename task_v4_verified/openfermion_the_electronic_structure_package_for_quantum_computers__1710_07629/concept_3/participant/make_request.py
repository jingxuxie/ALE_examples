"""Strip public labels and prepare a development inference request."""

import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output_dir", type=Path)
    arguments = parser.parse_args()
    destination = arguments.output_dir.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with np.load(arguments.dataset, allow_pickle=False) as archive:
        inputs = {key: archive[key] for key in ("hopping", "interaction", "potential", "n_sites", "family")}
    np.savez_compressed(destination / "inputs.npz", **inputs)
    (destination / "request.json").write_text(json.dumps({"schema_version": 1,
        "inputs": str(destination / "inputs.npz"), "n_instances": len(inputs["family"]),
        "target_order": ["charge_gap", "spin_gap"]}) + "\n")


if __name__ == "__main__":
    main()
