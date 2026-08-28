import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from transport import np, read_case, solve

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
arguments = parser.parse_args()
result, diagnostics = solve(read_case(arguments.input), backend="greens")
np.savez_compressed(arguments.output, **result)
print(json.dumps(diagnostics))
