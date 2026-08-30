import argparse
import json
from pathlib import Path


def sample():
    return {
        "schema_version": 1,
        "virtual_hopping": [[0.0 for column in range(7)] for row in range(7)],
        "virtual_density": [[0.0 for column in range(7)] for row in range(7)],
    }


def main():
    parser = argparse.ArgumentParser(description="Write a deterministic admissible starting Hamiltonian, not a witness.")
    parser.add_argument("--output", type=Path, default=Path("output/witness.json"))
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(sample(), indent=2, allow_nan=False) + "\n")
    print(str(arguments.output))


if __name__ == "__main__":
    main()
