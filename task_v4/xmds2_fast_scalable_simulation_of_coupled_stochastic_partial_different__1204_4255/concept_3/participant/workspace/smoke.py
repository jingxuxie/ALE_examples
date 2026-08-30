import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from field_control import evolve, failure, fidelities, read_json, references, resource_score, summarize, validate_artifact


def main():
    parser = argparse.ArgumentParser(description="Public coarse diagnostic; never a certified passing result")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--output")
    parser.add_argument("--cache-dir", help="Optional writable reference cache; default is no disk cache")
    parser.add_argument("--nx", type=int, default=64)
    parser.add_argument("--ny", type=int, default=32)
    parser.add_argument("--dt", type=float, default=0.04)
    arguments = parser.parse_args()
    started = time.perf_counter()
    root = Path(__file__).resolve().parents[1]
    try:
        protocol = read_json(root / "input/protocol.json")
        cases = read_json(root / "input/public_cases.json")
        artifact = read_json(arguments.artifact)
        splines, control_diagnostics = validate_artifact(artifact, protocol)
        shape = (arguments.nx, arguments.ny)
        initial, target, residual = references(cases, shape, arguments.cache_dir)
        state, audit = evolve(splines, cases, shape, arguments.dt, initial)
        scores = fidelities(state, target, shape)
        result = summarize(scores, cases, protocol)
        result["artifact_canonical_sha256"] = hashlib.sha256(json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        result["meets_public_thresholds_without_audit"] = result.pop("passed")
        result.update({"valid": True, "passed": False, "reason": "public_coarse_diagnostic_only; official passing requires private refined evaluation", "resource_score": resource_score(splines, protocol), "runtime_score": min(1.0, 180.0 / max(time.perf_counter() - started, 1e-9)), "runtime_seconds": time.perf_counter() - started, "grid": list(shape), "dt": arguments.dt, "reference_residual": residual, "cases": [{"id": case["id"], "fidelity": float(score)} for case, score in zip(cases, scores)], "control_diagnostics": control_diagnostics, "numerical_diagnostics": {key: float(np.max(value)) for key, value in audit.items()}})
    except Exception as error:
        result = failure(type(error).__name__ + ": " + str(error), time.perf_counter() - started)
    text = json.dumps(result, indent=2, allow_nan=False)
    if arguments.output:
        Path(arguments.output).write_text(text + "\n")
    print(text)
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
