import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

from physics import observables

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "concept_1/participant/workspace"))
import generators


def label(case):
    result = observables(case["fields"])
    return {**case, "f": result["f"], "r": result["r"], "min_gap": result["min_gap"]}


def main():
    destination = ROOT / "concept_1/adversary"
    generator = np.random.default_rng(721035891744)
    generators.LENGTHS = (10, 12, 14)
    cases = []
    for length, count in ((10, 180), (12, 180), (14, 80)):
        for family in generators.FAMILIES:
            for sample in range(count):
                cases.append({"id": "stress_" + str(len(cases)), "L": length, "family": family,
                              "fields": generators.sample_fields(generator, length, family)})
    started = time.monotonic()
    archive_path = destination / "broad_prediction_bank.jsonl"
    with archive_path.open("w") as archive:
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
            for finished, result in enumerate(executor.map(label, cases, chunksize=2)):
                archive.write(json.dumps(result) + "\n")
                archive.flush()
                if finished % 80 == 0:
                    print(json.dumps({"done": finished + 1, "total": len(cases), "length": result["L"],
                                      "seconds": time.monotonic() - started}), flush=True)
    report = {"records": len(cases), "lengths": [10, 12, 14], "families": list(generators.FAMILIES),
              "seed": 721035891744, "seconds": time.monotonic() - started,
              "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
              "purpose": "Private broad champion stress; in-domain draws plus scientifically identical L14 extension. Not part of initial scoring.",
              "primary_targets_unchanged": True, "private_to_generation": True}
    (destination / "broad_prediction_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
