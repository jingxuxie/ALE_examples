import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from spectral import load_problem, validate_design


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    config, target = load_problem(arguments.input)
    random = np.random.default_rng(71)
    while True:
        pattern = np.zeros(len(config["candidates"]), dtype=int)
        pattern[random.choice(len(pattern), config["normal_site_count"], replace=False)] = 1
        try:
            validate_design(config, pattern)
            break
        except ValueError:
            continue
    output = Path(arguments.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "design.json").write_text(json.dumps({"pattern": pattern.tolist()}) + "\n")


if __name__ == "__main__":
    main()
