import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 16384


def failure(reason):
    return {"schema_valid": False, "valid": False, "passed": False, "score": 0.0,
            "core_score": 0.0, "runtime_resource_score": 0.0, "reason": reason}


def unique_object(pairs):
    parsed = {}
    for name, value in pairs:
        if name in parsed:
            raise ValueError("duplicate JSON key")
        parsed[name] = value
    return parsed


def reject_constant(value):
    raise ValueError("nonfinite JSON value")


def read_artifact(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("witness must be a regular, nonsymlink file")
        if metadata.st_size > MAX_BYTES:
            raise ValueError("witness exceeds byte limit")
        data = source.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("witness exceeds byte limit")
    return json.loads(
        data.decode("utf-8"), object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )


def load_trusted_model():
    manifest = json.loads((ROOT / "evaluator/hidden/generation_manifest.json").read_text())
    model_bytes = (ROOT / "evaluator/hidden/reference_model.json").read_bytes()
    if hashlib.sha256(model_bytes).hexdigest() != manifest["model_sha256"]:
        raise ValueError("trusted model hash mismatch")
    public_files = json.loads((ROOT / "evaluator/hidden/public_hashes.json").read_text())
    for relative, expected in public_files.items():
        path = ROOT / relative
        if path.is_symlink() or not path.is_file() or path.stat().st_size != expected["bytes"]:
            raise ValueError(f"public input integrity failure: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
            raise ValueError(f"public input integrity failure: {relative}")
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "participant" / "input").rglob("*")
        if path.is_file() or path.is_symlink()
    }
    expected_input = {name for name in public_files if name.startswith("participant/input/")}
    if actual != expected_input:
        raise ValueError("public input inventory mismatch")
    model = json.loads(model_bytes)
    if (model["num_faults"], model["num_detectors"], model["weight_bound"]) != (512, 192, 20):
        raise ValueError("trusted dimensions mismatch")
    return model


def evaluate_data(model, artifact):
    if type(artifact) is not dict or set(artifact.keys()) != {"faults"}:
        raise ValueError("expected exactly the faults key")
    support = artifact["faults"]
    if type(support) is not list or len(support) > 512:
        raise ValueError("faults must be a list of at most 512 IDs")
    if any(type(location) is not int for location in support):
        raise ValueError("fault IDs must be integers, not booleans")
    if any(location < 0 or location >= 512 for location in support):
        raise ValueError("fault ID outside [0,511]")
    if len(set(support)) != len(support):
        raise ValueError("duplicate fault IDs")
    fault_mask = sum(1 << location for location in support)
    residual = 0
    for detector in range(192):
        row = sum(
            ((int(column, 16) >> detector) & 1) << location
            for location, column in enumerate(model["columns"])
        )
        residual |= ((row & fault_mask).bit_count() & 1) << detector
    observable_mask = sum(bit << location for location, bit in enumerate(model["observable"]))
    logical = (observable_mask & fault_mask).bit_count() & 1
    weight = len(support)
    within_bound = 1 <= weight <= 20
    valid = within_bound and residual == 0 and logical == 1
    score = 0.0 if weight == 0 else (
        0.10 + 0.15 * min(1, 20 / weight)
        + 0.45 * (1 - residual.bit_count() / 192) + 0.10 * logical
    )
    if valid:
        score = 1.0
    if weight == 0:
        reason = "empty_witness"
    elif not within_bound:
        reason = "over_weight_bound"
    elif residual:
        reason = "nonzero_syndrome"
    elif logical == 0:
        reason = "even_logical_parity"
    else:
        reason = "counterexample"
    return {
        "schema_valid": True, "valid": valid, "score": round(score, 12),
        "weight": weight, "within_bound": within_bound,
        "detector_weight": residual.bit_count(), "logical_parity": logical,
        "syndrome_hex": f"{residual:048x}", "reason": reason,
    }


def evaluate_path(path):
    started = time.monotonic()
    try:
        model = load_trusted_model()
    except (OSError, ValueError, KeyError) as error:
        return failure(f"input_error: {error}")
    try:
        result = evaluate_data(model, read_artifact(path))
        specification = importlib.util.spec_from_file_location("trusted_pruning", ROOT / "evaluator/hidden/overconfident_search.py")
        method = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(method)
        claim = method.search(model)
        result["claim_reproduced"] = claim["claimed_certified"] and claim["faults"] == [] and claim["claimed_distance_lower_bound"] == 21
        if not result["claim_reproduced"]:
            return failure("input_error: supplied failure is not reproduced")
        result.update(passed=result["valid"], core_score=result["score"], runtime_resource_score=1.0,
                      runtime_seconds=time.monotonic() - started, baseline_extensions=claim["total_extensions"])
        return result
    except (OSError, ValueError, RecursionError) as error:
        return failure(f"invalid_artifact: {error}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate static witness JSON without executing participant code.")
    parser.add_argument("--witness", type=Path, default=ROOT / "participant/workspace/witness.json")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = evaluate_path(arguments.witness)
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.write_text(serialized)
    print(serialized, end="")
    if result["reason"].startswith("input_error:"):
        return 2
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
