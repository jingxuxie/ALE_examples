import argparse
import json
from pathlib import Path


def make_witness():
    bonds = [1] * 32
    bonds[0] = -1
    bonds[20] = -1
    return {
        "schema_version": 1,
        "bonds": bonds,
        "beta": 1.0,
        "order": list(range(16)),
        "weights": [[0.0] * 16 for position in range(16)],
        "pattern": [1] * 16,
        "radius": 2,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    destination = arguments.output / "witness.json"
    destination.write_text(json.dumps(make_witness(), indent=2, allow_nan=False) + "\n")
    print(destination)


if __name__ == "__main__":
    main()
