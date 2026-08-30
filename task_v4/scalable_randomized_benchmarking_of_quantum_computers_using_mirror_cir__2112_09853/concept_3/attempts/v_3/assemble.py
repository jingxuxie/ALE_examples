import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ["SRC"])
from reference_core import circuit_weights, summarize, validate_submission

WORDS = ["I", "H", "S", "HS", "SH", "HSH"]


def read_circuit(path, family):
    values = iter(map(int, Path(path).read_text().split()))
    width, depth = next(values), next(values)
    layers = []
    for round_index in range(depth):
        local = [WORDS[next(values)] for site in range(width)]
        gates = next(values)
        cx = [[next(values), next(values)] for gate in range(gates)]
        layers.append({"local": local, "cx": cx})
    return {"family": family, "layers": layers}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs=3)
    parser.add_argument("--output", default="artifact.json")
    args = parser.parse_args()
    spec = json.loads(Path(os.environ["SRC"], "input/spec.json").read_text())
    circuits = [read_circuit(path, family["id"]) for path, family in zip(args.paths, spec["families"])]
    artifact = {"schema_version": 1, "circuits": circuits}
    validate_submission(artifact, spec)
    Path(args.output).write_text(json.dumps(artifact, indent=2) + "\n")
    for circuit, family in zip(circuits, spec["families"]):
        metrics = summarize(family["n"], circuit_weights(family["n"], circuit["layers"]))
        print(family["id"], [(direction, kind, values["minimum"], values["mean"]) for direction, strata in metrics.items() for kind, values in strata.items()])
