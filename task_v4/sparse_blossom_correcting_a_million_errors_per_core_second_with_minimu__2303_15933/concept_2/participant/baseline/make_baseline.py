import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(Path(__file__).resolve().parent / "weak.json"))
    arguments = parser.parse_args()
    data = {"version": 1,
            "probabilities": [0.03 + 0.08 * ((17 * edge + 11) % 39) / 38 for edge in range(39)],
            "syndrome": [1, 6, 11, 16]}
    Path(arguments.output).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
