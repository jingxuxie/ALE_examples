import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from baseline import solve as baseline_solve
from channel import risk


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    model = json.loads(Path(arguments.input).read_text())
    answer = baseline_solve(model)
    best_risk = max(risk(model, answer))
    Path(arguments.output).write_text(json.dumps(answer) + "\n")
    with tempfile.TemporaryDirectory(prefix="decoder_portfolio_") as temporary:
        candidate_path = Path(temporary) / "candidate.json"
        command = [sys.executable, str(Path(__file__).parent / "optimizer/solve.py"),
                   "--input", arguments.input, "--output", str(candidate_path), "--seconds", "38.0"]
        try:
            subprocess.run(command, check=False, timeout=41)
        except subprocess.TimeoutExpired:
            pass
        if candidate_path.is_file():
            try:
                candidate = json.loads(candidate_path.read_text())
                if max(risk(model, candidate)) < best_risk:
                    answer = candidate
            except (ValueError, KeyError, IndexError, TypeError):
                pass
    Path(arguments.output).write_text(json.dumps(answer) + "\n")


if __name__ == "__main__":
    main()
