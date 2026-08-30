import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

from protocol import run_policy, summarize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    models = json.loads((root / "input/practice_models.json").read_text())
    tables = np.load(root / "input/practice.npz", allow_pickle=False)["energies"]
    environment = dict(os.environ, PYTHONPATH=str(root / "workspace"), OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    records, elapsed = run_policy([sys.executable, str(arguments.submission.resolve() / "solution.py")],
                                  models, tables, environment=environment)
    report = summarize(records, elapsed)
    if arguments.output:
        arguments.output.write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
