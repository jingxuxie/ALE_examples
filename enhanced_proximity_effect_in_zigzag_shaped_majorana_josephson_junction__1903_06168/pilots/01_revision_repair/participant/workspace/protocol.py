import argparse
import json
from pathlib import Path
import sys

from compat import load_source
from hamiltonian import solve_request


def main(snapshot):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    arguments = parser.parse_args()
    sys.dont_write_bytecode = True
    request = json.loads(arguments.input.read_text())
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    source = load_source(Path(snapshot), arguments.output.parent)
    result = solve_request(source, request)
    arguments.output.write_text(json.dumps(result, allow_nan=False) + '\n')
