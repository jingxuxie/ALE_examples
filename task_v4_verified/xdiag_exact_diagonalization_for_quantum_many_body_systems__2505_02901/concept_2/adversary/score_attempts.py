import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import evaluate
import numpy as np


def arrays_in_json(value, location="root"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from arrays_in_json(item, location + "." + key)
    elif isinstance(value, list):
        try:
            array = np.asarray(value, dtype=float)
        except (ValueError, TypeError, OverflowError):
            array = None
        if array is not None and array.shape in ((24, 3), (72,), (3, 24)) and np.all(np.isfinite(array)):
            candidate = array.T if array.shape == (3, 24) else array.reshape(24, 3)
            yield location, candidate
        elif array is not None and array.ndim == 3 and array.shape[1:] == (24, 3):
            for index, candidate in enumerate(array):
                if np.all(np.isfinite(candidate)):
                    yield location + f"[{index}]", candidate
        else:
            for index, item in enumerate(value):
                if isinstance(item, (list, dict)):
                    yield from arrays_in_json(item, location + f"[{index}]")


def candidates(directory):
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 32 * 1024 * 1024:
            continue
        try:
            if path.suffix == ".json":
                payload = json.loads(path.read_text())
                for location, array in arrays_in_json(payload):
                    yield str(path.relative_to(directory)) + ":" + location, array
            elif path.suffix in (".npy", ".npz"):
                loaded = np.load(path, allow_pickle=False)
                if path.suffix == ".npy":
                    entries = [("array", loaded)]
                else:
                    entries = [(name, loaded[name]) for name in loaded.files]
                for name, array in entries:
                    if np.iscomplexobj(array):
                        if np.any(array.imag != 0):
                            continue
                        array = array.real
                    if array.shape == (72,):
                        array = array.reshape(24, 3)
                    if array.shape == (3, 24):
                        array = array.T
                    if array.shape == (24, 3) and np.all(np.isfinite(array)):
                        yield str(path.relative_to(directory)) + ":" + name, array
                    elif array.ndim == 3 and array.shape[1:] == (24, 3):
                        for index, candidate in enumerate(array):
                            if np.all(np.isfinite(candidate)):
                                yield str(path.relative_to(directory)) + f":{name}[{index}]", candidate
                if path.suffix == ".npz":
                    loaded.close()
        except (ValueError, OSError, TypeError, OverflowError, RecursionError):
            continue


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    directory = arguments.attempt.resolve()
    archive = arguments.output.parent / (arguments.output.stem + "_artifacts")
    archive.mkdir(parents=True, exist_ok=True)
    seen = set()
    records = []
    for origin, amplitudes in candidates(directory):
        amplitudes = np.asarray(amplitudes, dtype=np.float64)
        digest = hashlib.sha256(np.asarray(amplitudes, dtype=np.float64).tobytes()).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        path = archive / (digest + ".json")
        path.write_text(json.dumps({"schema_version": 1, "amplitudes": amplitudes.tolist()}, allow_nan=False) + "\n")
        report = evaluate(path)
        report.update(original_artifact=origin, amplitude_sha256=digest, canonical_artifact=str(path))
        records.append(report)
    def rank(record):
        joint = min(record["core_score"] / 0.999995, record["worst_family_score"] / 0.99999, record["minimum_column_fidelity"] / 0.99999)
        return (record["passed"], record["valid"], joint, record["core_score"])
    records.sort(key=rank, reverse=True)
    final_report = evaluate(directory)
    output = {"any_valid_witness": any(record["passed"] for record in records), "unique_artifacts_checked": len(records), "final_submission": final_report, "best_produced_artifact": records[0] if records else None, "artifacts": records, "note": "Every discovered numeric 24x3 pulse is checked independently, including auxiliary checkpoints. Only serialization is canonicalized; no amplitude is optimized or projected. This prevents packaging mistakes from masquerading as scientific hardness."}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"any_valid_witness": output["any_valid_witness"], "unique_artifacts_checked": len(records), "best_core_score": records[0]["core_score"] if records else 0, "best_worst_family_score": records[0]["worst_family_score"] if records else 0, "final_passed": final_report["passed"]}))


if __name__ == "__main__":
    main()
