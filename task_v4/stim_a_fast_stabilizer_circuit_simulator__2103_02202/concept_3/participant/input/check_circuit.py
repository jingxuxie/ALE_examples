import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from checker import MAX_BYTES, Invalid, check, load, rejection


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("circuit")
    arguments = parser.parse_args()
    try:
        path = Path(arguments.circuit)
        if path.name != "circuit.json" or path.is_symlink() or not path.is_file():
            raise Invalid("Expected regular nonsymlink circuit.json")
        with path.open("rb") as source:
            artifact = load(source.read(MAX_BYTES + 1))
        instance = {name: json.loads((ROOT / (name + ".json")).read_text()) for name in ("target", "constraints")}
        result = check(artifact, instance)
    except (ValueError, OSError, UnicodeError, RecursionError, TypeError, KeyError) as error:
        result = rejection(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
