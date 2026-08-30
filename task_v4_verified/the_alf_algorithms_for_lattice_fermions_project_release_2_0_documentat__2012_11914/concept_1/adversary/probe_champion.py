import argparse
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
from scipy.linalg import expm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--beta", required=True, type=float)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    output = Path(arguments.output)
    output.mkdir(parents=True, exist_ok=True)
    module_spec = importlib.util.spec_from_file_location("frozen_champion", arguments.source)
    champion = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(champion)
    champion.MODEL["beta"] = arguments.beta
    champion.DELTA = arguments.beta / champion.MODEL["time_slices"]
    champion.COUPLING = np.arccosh(np.exp(champion.DELTA * champion.MODEL["interaction"] / 2))
    champion.KINETIC = expm(-champion.DELTA * champion.kinetic_matrix())
    champion.OUTPUT = output
    started = time.monotonic()
    champion.main()
    (output / "result.json").write_text(json.dumps({"beta": arguments.beta, "seconds": time.monotonic() - started, "witness_written": (output / "witness.json").exists()}, indent=2) + "\n")


if __name__ == "__main__":
    main()
