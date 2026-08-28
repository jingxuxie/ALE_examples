import argparse
import json
from pathlib import Path

from transport import np, read_case, solve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=["smatrix", "greens"], default="smatrix")
    arguments = parser.parse_args()
    result, diagnostics = solve(read_case(arguments.input), arguments.backend)
    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **result)
    print(json.dumps(diagnostics))


if __name__ == "__main__":
    main()
