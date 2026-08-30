import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

PARTICIPANT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PARTICIPANT / "workspace"))

import numpy as np
from exact import assess, family_fields, proxy_statistics, spectrum, validate_fields


def screen(fields):
    statistics = proxy_statistics(spectrum(fields))
    return {"schema_version": 1, "fields": fields,
            "orientation": 1 if statistics["difference"] >= 0 else -1}, abs(statistics["difference"])


def check(candidate):
    witness, protocol = candidate
    return witness, assess(witness, protocol)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("witness.json"))
    parser.add_argument("--seed", type=int, default=21992)
    parser.add_argument("--candidates", type=int, default=128)
    parser.add_argument("--finalists", type=int, default=8)
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=8)
    arguments = parser.parse_args()
    if not 1 <= arguments.finalists <= arguments.candidates <= 100000:
        parser.error("require 1 <= finalists <= candidates <= 100000")
    protocol = json.loads((PARTICIPANT / "input" / "protocol.json").read_text())
    random = np.random.default_rng(arguments.seed)
    started = time.monotonic()
    candidates = []
    while len(candidates) < arguments.candidates:
        width = random.uniform(1.0, 5.0)
        fields = random.uniform(-width, width, 12)
        fields -= fields.mean()
        try:
            validate_fields(fields)
            for family, member, profile in family_fields(fields, protocol):
                validate_fields(profile, derived=True)
        except ValueError:
            continue
        candidates.append(fields.tolist())
    with concurrent.futures.ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        screened = sorted(executor.map(screen, candidates), key=lambda item: item[1], reverse=True)
        finalists = [(witness, protocol) for witness, discrepancy in screened[:arguments.finalists]]
        results = list(executor.map(check, finalists))
    witness, report = max(results, key=lambda item: (item[1]["pass"], item[1]["core"], item[1]["worst_family"]))
    arguments.output.write_text(json.dumps(witness, indent=2, allow_nan=False) + "\n")
    summary = {"seed": arguments.seed, "candidates": arguments.candidates, "finalists": arguments.finalists,
               "workers": arguments.workers, "blas_threads": 1, "seconds": time.monotonic() - started,
               "diagonalizations": arguments.candidates + 129 * arguments.finalists,
               "case_set": "public_calibration",
               "core": report["core"], "worst_family": report["worst_family"],
               "valid": report["valid"], "pass": report["pass"], "reason": report["reason"]}
    arguments.output.with_suffix(".search.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
