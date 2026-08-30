"""Generate public development cases without reading private manifests."""

import argparse
import hashlib
import json
from pathlib import Path


PUBLIC_ROOT_SEED = "cascade-correlated-echo-v2-public-development-2026-08-28"


def generate(contract, root_seed=PUBLIC_ROOT_SEED, episodes_per_cell=4):
    cases = []
    for replicate in range(episodes_per_cell):
        for family in contract["families"]:
            for denominator in contract["contamination_denominators"]:
                material = f"{root_seed}:{family}:{denominator}:{replicate}".encode()
                cases.append({"family": family, "contamination_denominator": denominator, "seed": int.from_bytes(hashlib.sha256(material).digest(), "big")})
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root-seed", default=PUBLIC_ROOT_SEED)
    parser.add_argument("--episodes-per-cell", type=int, default=4)
    arguments = parser.parse_args()
    contract = json.loads(arguments.contract.read_text())
    arguments.output.write_text(json.dumps(generate(contract, arguments.root_seed, arguments.episodes_per_cell), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
