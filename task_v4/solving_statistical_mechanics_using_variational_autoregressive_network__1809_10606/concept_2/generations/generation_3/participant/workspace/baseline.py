import argparse
import json
from pathlib import Path


def make_witness():
    template = Path(__file__).resolve().parents[1] / "baseline" / "witness.json"
    return json.loads(template.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    witness = make_witness()
    arguments.output.mkdir(parents=True, exist_ok=True)
    destination = arguments.output / "witness.json"
    destination.write_text(json.dumps(witness, indent=2, allow_nan=False) + "\n")
    print(destination)


if __name__ == "__main__":
    main()
