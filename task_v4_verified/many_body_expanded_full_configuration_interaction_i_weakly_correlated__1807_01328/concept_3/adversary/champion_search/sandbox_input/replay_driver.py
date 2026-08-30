"""I/O-only adapter for the unchanged reviewed champion, inside bubblewrap."""

import hashlib
import importlib.util
import json
import resource
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import scipy


INPUT = Path("/input")
OUTPUT = Path("/output")


def main():
    started = time.perf_counter()
    isolation_checks = {path: Path(path).exists() for path in
                        ("/home", "/srv/home", "/input/private", "/private", "/workspace")}
    if any(isolation_checks.values()):
        raise RuntimeError("Unexpected private/host filesystem visibility")
    hashes = json.loads((INPUT / "source_hashes.json").read_text())
    for filename, expected in hashes.items():
        if hashlib.sha256((INPUT / filename).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Source snapshot checksum mismatch")
    specification = importlib.util.spec_from_file_location("reviewed_champion", INPUT / "reconstruct.py")
    champion = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = champion
    specification.loader.exec_module(champion)
    generator = champion.load_generator(INPUT)
    with np.load(INPUT / "challenge_features.npz", allow_pickle=False) as archive:
        data = dict(archive)
    forbidden = {"tail", "hopping", "correlation", "residual", "reference_weight", "seed", "cohort"}
    if forbidden.intersection(data):
        raise RuntimeError("Non-feature data present in predictor input")
    predictions = np.full(len(data["ids"]), np.nan)
    recovered_hopping = np.full((len(predictions), 12, 12), np.nan)
    records = []
    feature_keys = [key for key in data if key != "ids"]
    for row in range(len(predictions)):
        case_started = time.perf_counter()
        record = {"id": str(data["ids"][row]), "row": row, "status": "error"}
        try:
            features = {key: data[key][row] for key in feature_keys}
            prediction, diagnostics, inferred = champion.reconstruct(features, generator)
            if not np.isfinite(prediction):
                raise ValueError("Champion returned a nonfinite prediction")
            predictions[row] = prediction
            recovered_hopping[row] = 0.0
            size = len(inferred.onsite)
            recovered_hopping[row, :size, :size] = inferred.hopping
            record.update({"status": "ok", "diagnostics": diagnostics})
        except Exception as error:
            record.update({"error_type": type(error).__name__, "error": str(error),
                           "traceback": traceback.format_exc()})
        record["runtime_seconds"] = time.perf_counter() - case_started
        records.append(record)
        if (row + 1) % 32 == 0 or row + 1 == len(predictions):
            print("champion replay", row + 1, "/", len(predictions), flush=True)
    np.savez_compressed(OUTPUT / "predictions.npz", ids=data["ids"], tail=predictions)
    np.savez_compressed(OUTPUT / "inferred_hopping.npz", ids=data["ids"], hopping=recovered_hopping)
    report = {"source_hashes": hashes, "runtime_seconds": time.perf_counter() - started,
              "numerical_runtime_seconds": sum(record["runtime_seconds"] for record in records),
              "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
              "python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__,
              "isolation_checks_path_visible": isolation_checks,
              "default_champion_assets_visible": champion.DEFAULT_ASSETS.exists(),
              "input_keys": sorted(data), "rows": len(predictions),
              "failures": sum(record["status"] != "ok" for record in records), "records": records,
              "algorithm_modified": False, "adapter_role": "read feature rows; call unchanged reconstruct; collect outputs"}
    (OUTPUT / "diagnostics.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("rows", "failures", "runtime_seconds", "peak_rss_mib")}), flush=True)


if __name__ == "__main__":
    main()
