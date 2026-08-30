import argparse
import json
import os
from pathlib import Path
import stat
import sys


MAX_BYTES = 16384


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON value")


def read_witness(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("witness must be a regular, nonsymlink file")
        if metadata.st_size > MAX_BYTES:
            raise ValueError("witness exceeds byte limit")
        content = source.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError("witness exceeds byte limit")
    return json.loads(
        content.decode("utf-8"), object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )


def check(model, artifact):
    if type(artifact) is not dict or set(artifact) != {"faults"}:
        raise ValueError("expected exactly the faults key")
    faults = artifact["faults"]
    if type(faults) is not list or len(faults) > model["num_faults"]:
        raise ValueError("faults must be a list of at most 512 IDs")
    if any(type(fault) is not int for fault in faults):
        raise ValueError("fault IDs must be integers, not booleans")
    if any(not 0 <= fault < model["num_faults"] for fault in faults):
        raise ValueError("fault ID outside [0,511]")
    if len(set(faults)) != len(faults):
        raise ValueError("duplicate fault IDs")
    syndrome = 0
    logical = 0
    for fault in faults:
        syndrome ^= int(model["columns"][fault], 16)
        logical ^= model["observable"][fault]
    weight = len(faults)
    within_bound = 1 <= weight <= model["weight_bound"]
    valid = within_bound and syndrome == 0 and logical == 1
    score = 0.0
    if weight:
        score = (
            0.10 + 0.15 * min(1, model["weight_bound"] / weight)
            + 0.45 * (1 - syndrome.bit_count() / model["num_detectors"])
            + 0.10 * logical
        )
    if valid:
        score = 1.0
    reason = "counterexample"
    if not weight:
        reason = "empty_witness"
    elif not within_bound:
        reason = "over_weight_bound"
    elif syndrome:
        reason = "nonzero_syndrome"
    elif not logical:
        reason = "even_logical_parity"
    return {
        "schema_valid": True, "valid": valid, "score": round(score, 12),
        "weight": weight, "within_bound": within_bound,
        "detector_weight": syndrome.bit_count(), "logical_parity": logical,
        "syndrome_hex": f"{syndrome:048x}", "reason": reason,
    }


def failure(reason):
    return {"schema_valid": False, "valid": False, "score": 0.0, "reason": reason}


def main():
    parser = argparse.ArgumentParser(description="Check a static fault witness; no search.")
    parser.add_argument("witness", type=Path)
    arguments = parser.parse_args()
    try:
        model = json.loads(Path(__file__).with_name("model.json").read_text())
    except (OSError, ValueError) as error:
        print(json.dumps(failure(f"input_error: {error}")))
        return 2
    try:
        result = check(model, read_witness(arguments.witness))
    except (OSError, ValueError, RecursionError) as error:
        result = failure(f"invalid_artifact: {error}")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
