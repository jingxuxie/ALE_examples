import argparse
import json
import struct
import sys
from pathlib import Path

PARTICIPANT = Path(__file__).resolve().parents[2] / "participant"
sys.path.insert(0, str(PARTICIPANT / "workspace"))
from design_common import generate_supports, load_case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--seed", type=int, default=17031)
    parser.add_argument("--count", type=int, default=256)
    arguments = parser.parse_args()
    family = json.loads((PARTICIPANT / "input/family.json").read_text())
    with open(arguments.output, "wb") as stream:
        def integer(value):
            stream.write(struct.pack("<I", value))

        integer(3)
        for index, identifier in enumerate(family["cases"]):
            case = load_case(PARTICIPANT / "input" / (identifier + ".json.gz"))
            integer(len(case["columns"]))
            bits = max(value.bit_length() for triple in case["columns"] for value in triple)
            words = (bits + 63) // 64
            integer(words)
            for cell, triple in zip(case["slot_cells"], case["columns"]):
                integer(cell)
                for value in triple:
                    stream.write(value.to_bytes(words * 8, "little"))
            records = generate_supports(case, arguments.seed + 37 * index, arguments.count, family["densities"])
            integer(len(records))
            for record in records:
                integer(("iid", "stripe", "burst").index(record["family"]))
                integer(len(record["support"]))
                for slot in record["support"]:
                    integer(slot)


if __name__ == "__main__":
    main()
