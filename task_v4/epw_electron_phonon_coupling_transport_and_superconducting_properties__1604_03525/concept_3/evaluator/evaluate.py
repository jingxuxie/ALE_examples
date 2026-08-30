import argparse
import json
import os
from pathlib import Path
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from hidden.engine import InvalidWitness, load_witness, validate_pair


def evaluate(submission):
    started = time.monotonic()
    try:
        matrices, resources = load_witness(submission)
        result = validate_pair(matrices)
        result["resources"] = resources
    except (InvalidWitness, ValueError, OSError, UnicodeError, OverflowError, RecursionError) as error:
        result = {"valid": False, "passed": False, "status": "invalid_witness", "score": 0.0,
                  "core_score": 0.0, "worst_family_score": 0.0, "reason": str(error)[:500]}
    result.update({"authoritative": True, "model_id": "epw_matched_dirichlet_v1",
                   "elapsed_seconds": time.monotonic() - started,
                   "runtime_resource_score": None,
                   "runtime_note": "Only a bounded static artifact is graded; design-time usage is not inferred."})
    return result


def main():
    parser = argparse.ArgumentParser(description="Validate numeric JSON only; never execute submission code")
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    result = evaluate(arguments.submission)
    serialized = json.dumps(result, indent=2, allow_nan=False) + "\n"
    destination = Path(arguments.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(serialized)
    print(serialized, end="")


if __name__ == "__main__":
    main()
