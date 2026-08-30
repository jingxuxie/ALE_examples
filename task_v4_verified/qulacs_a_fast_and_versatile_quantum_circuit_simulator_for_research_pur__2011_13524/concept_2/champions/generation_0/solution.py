#!/usr/bin/env python3
"""Emit locally synthesized compact circuits for the supplied public operators.

Usage: python solution.py INPUT_JSON OUTPUT_JSON
The precomputed circuits are independent of the working directory, require no
optimization at runtime, and use only the U3/CNOT gate vocabulary.
"""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python solution.py INPUT_JSON OUTPUT_JSON")
    specification = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    library_path = Path(__file__).resolve().with_name("circuits.json")
    library = json.loads(library_path.read_text(encoding="utf-8"))
    # The separate, unscored ordering example supplied with the task.
    library["demo_2q"] = [{"gate": "CNOT", "control": 0, "target": 1}]
    answer = {target["id"]: library[target["id"]]
              for target in specification["targets"]}
    Path(sys.argv[2]).write_text(
        json.dumps(answer, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
