import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import optimizer_copy as opt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--safe", required=True)
    parser.add_argument("--fast", required=True)
    parser.add_argument("--tag", default="mix")
    arguments = parser.parse_args()
    safe = opt.load(arguments.safe)
    fast = opt.load(arguments.fast)
    provenance = {"role": "privileged_postdeadline_generation_only", "generation": 2, "sources": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in (arguments.safe, arguments.fast)}, "weights_fast": [0.25, 0.4, 0.55]}
    for weight in provenance["weights_fast"]:
        vector = (1 - weight) * safe + weight * fast
        opt.fc.validate_artifact(opt.artifact(vector), opt.PROTOCOL)
        opt.write(HERE / (arguments.tag + "_%02d.json" % round(100 * weight)), vector)
    (HERE / (arguments.tag + ".provenance.json")).write_text(json.dumps(provenance, indent=2) + "\n")


if __name__ == "__main__":
    main()
