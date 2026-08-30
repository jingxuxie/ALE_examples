import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                 "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
sys.path.insert(0, str(ROOT / "evaluator"))

import numpy as np

from generators import FAMILIES, LENGTHS, sample_cases
from physics import observables


def simulate(case):
    result = observables(case["fields"])
    return dict(case, f=result["f"], min_gap=result["min_gap"])


def canonical(fields):
    fields = np.asarray(fields)
    centered = fields - np.mean(fields)
    return min(tuple(np.round(np.roll(orientation, shift), 11))
               for orientation in (centered, -centered, centered[::-1], -centered[::-1])
               for shift in range(len(fields)))


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n"
                            for record in records))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    destinations = {"train": ROOT / "participant/input/train.jsonl",
                    "validation": ROOT / "participant/input/validation.jsonl",
                    "test": ROOT / "evaluator/hidden/test.jsonl"}
    if any(path.exists() for path in destinations.values()):
        raise RuntimeError("Frozen datasets exist; refusing to overwrite")
    configurations = (("train", 200, np.random.default_rng(1010199201)),
                      ("validation", 40, np.random.default_rng(1010199202)),
                      ("test", 40, np.random.default_rng()))
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "workers": args.workers,
                "public_seeds": {"train": 1010199201, "validation": 1010199202},
                "test_generation": "Independent OS-entropy draws from identical public generators; no retained secret seed",
                "simulation": "float64 scipy.linalg.eigh evr, zero-Sz, periodic J=1, central third eigenvectors",
                "splits": {}}
    seen = set()
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for name, per_cell, rng in configurations:
            cases = sample_cases(per_cell, rng)
            for index, case in enumerate(cases):
                case["id"] = f"{name}_{index:05d}"
                signature = canonical(case["fields"])
                if signature in seen:
                    raise AssertionError("Duplicate, shifted, spin-flipped or dihedrally equivalent sample")
                seen.add(signature)
            records = []
            for index, result in enumerate(executor.map(simulate, cases, chunksize=4)):
                if not 0 <= result["f"] <= 1 or not np.isfinite(result["f"]):
                    raise AssertionError("Invalid simulated target")
                records.append(result)
                if (index + 1) % 100 == 0:
                    print(f"{name}: {index + 1}/{len(cases)} at {time.monotonic() - started:.1f}s", flush=True)
            labels = [{key: value for key, value in result.items() if key != "min_gap"}
                      for result in records]
            write_jsonl(destinations[name], labels)
            if name == "validation":
                inputs = [{key: case[key] for key in ("id", "L", "fields")} for case in labels]
                path = ROOT / "participant/input/validation_cases.json"
                path.write_text(json.dumps({"cases": inputs}, allow_nan=False) + "\n")
            statistics = {}
            for family in FAMILIES:
                for length in LENGTHS:
                    selected = [case["f"] for case in records
                                if case["family"] == family and case["L"] == length]
                    statistics[f"{family}/L{length}"] = {
                        "count": len(selected), "f_min": min(selected), "f_max": max(selected),
                        "f_mean": float(np.mean(selected)), "f_std": float(np.std(selected))}
            manifest["splits"][name] = {
                "records": len(records), "sha256": sha256(destinations[name]), "strata": statistics,
                "minimum_central_spectral_gap": min(case["min_gap"] for case in records),
                "minimum_field_separation": min(float(np.min(np.diff(np.sort(case["fields"])))) for case in records)}
    manifest["seconds"] = time.monotonic() - started
    manifest["cross_split_symmetry_duplicates"] = 0
    manifest["physics_sha256"] = sha256(ROOT / "evaluator/physics.py")
    manifest["generator_sha256"] = sha256(ROOT / "participant/workspace/generators.py")
    (ROOT / "evaluator/hidden/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    public = {key: value for key, value in manifest.items() if key != "splits"}
    public["splits"] = {key: value for key, value in manifest["splits"].items() if key != "test"}
    (ROOT / "participant/input/data_checks.json").write_text(json.dumps(public, indent=2) + "\n")
    print(json.dumps({"seconds": manifest["seconds"], "records": len(seen)}), flush=True)


if __name__ == "__main__":
    main()
