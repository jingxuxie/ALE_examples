import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from spectral import discrepancies, load_problem, validate_design
from checker import independent_response


def evaluate(submission):
    started = time.monotonic()
    result = {"verification_mode": "C", "core_score": 0.0, "worst_family_score": 0.0,
              "runtime_score": 0.0, "passed": False, "valid": False}
    try:
        seal = json.loads((ROOT / "evaluator" / "hidden" / "freeze.json").read_text())
        for relative, expected in seal["sha256"].items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
                raise RuntimeError("frozen evaluator input changed: " + relative)
        artifact = Path(submission) / "design.json"
        if artifact.is_symlink() or artifact.stat().st_size > 65536:
            raise ValueError("artifact is a symlink or exceeds 64 KiB")
        design = json.loads(artifact.read_text())
        config, target = load_problem(ROOT / "participant" / "input")
        pattern = validate_design(config, design["pattern"])
        observed = independent_response(config, pattern)
        if observed.shape != target.shape or not np.isfinite(observed).all():
            raise ValueError("nonfinite or malformed computed spectrum")
        result.update(discrepancies(config, observed, target))
        elapsed = time.monotonic() - started
        result["runtime_seconds"] = elapsed
        result["runtime_score"] = max(0.0, 1.0 - elapsed / 120.0)
        result["valid"] = True
        result["passed"] = bool(result["core_score"] >= 0.96 and result["worst_family_score"] >= 0.94 and elapsed <= 120.0)
        result["reason"] = "all fabrication and spectral conditions met" if result["passed"] else "valid pattern; spectral fidelity below fixed target"
    except Exception as error:
        result["reason"] = type(error).__name__ + ": " + str(error)
        result["runtime_seconds"] = time.monotonic() - started
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--report")
    arguments = parser.parse_args()
    result = evaluate(arguments.submission)
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        Path(arguments.report).write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
