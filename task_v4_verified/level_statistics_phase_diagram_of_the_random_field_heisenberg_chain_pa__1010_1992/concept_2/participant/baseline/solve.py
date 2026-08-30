import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    spec = json.loads((Path(__file__).resolve().parents[1] / "input/spec.json").read_text())
    generator = np.random.default_rng(42)
    layouts = []
    for bank in spec["banks"]:
        fields = np.array(bank["fields"])
        layouts.append({"id": bank["id"], "high": np.argsort(fields).tolist(),
                        "low": generator.permutation(len(fields)).tolist()})
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps({"layouts": layouts}, indent=2) + "\n")


if __name__ == "__main__":
    main()
