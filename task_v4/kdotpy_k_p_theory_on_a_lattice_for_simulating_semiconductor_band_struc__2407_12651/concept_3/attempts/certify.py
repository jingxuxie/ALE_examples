import argparse
import json
import os
import sys
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from reference import spectral_certificate, topology_certificate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("witness", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh", type=int)
    arguments = parser.parse_args()
    witness = json.loads(arguments.witness.read_text())
    config = json.loads((ROOT / "participant/input/model.json").read_text())
    report = {"spectral": spectral_certificate(witness, config, arguments.mesh), "topology": topology_certificate(witness, config["topology_mesh"])}
    arguments.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: {name: value for name, value in result.items() if name != "scenarios"} for key, result in report.items()}, indent=2))


if __name__ == "__main__":
    main()
