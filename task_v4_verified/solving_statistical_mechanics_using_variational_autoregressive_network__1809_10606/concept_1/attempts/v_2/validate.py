import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

from test_solver import metrics, validate


def generated_instance(family, count, beta, seed, field_scale=0.05):
    rng = np.random.default_rng(seed)
    if family == "sk":
        couplings = np.tril(rng.normal(size=(count, count)) * beta / np.sqrt(count), -1)
        couplings += couplings.T
    elif family == "memory":
        patterns = rng.choice([-1, 1], size=(count, 3 + seed % 3))
        couplings = beta * (patterns @ patterns.T) / count
        noise = rng.normal(size=(count, count)) * 0.04
        couplings += (noise + noise.T) / np.sqrt(2)
        np.fill_diagonal(couplings, 0)
    elif family == "lattice":
        couplings = np.zeros((count, count))
        if count in (18, 20):
            width, height = (5, 4) if count == 20 else (6, 3)
            for row in range(height):
                for column in range(width):
                    site = row * width + column
                    neighbors = (row * width + (column + 1) % width, ((row + 1) % height) * width + column)
                    for other in neighbors:
                        couplings[site, other] = couplings[other, site] = beta * rng.choice([-1, 1])
        else:
            for site in range(count):
                for other in ((site + 1) % count, (site + 4) % count):
                    couplings[site, other] = couplings[other, site] = beta * rng.choice([-1, 1])
    else:
        raise ValueError(family)
    fields = rng.normal(size=count) * field_scale
    return {"n": count, "couplings": couplings.tolist(), "fields": fields.tolist()}


def stress_cases():
    for family, moderate, cold in (("sk", 2, 6), ("memory", 2, 6), ("lattice", 0.8, 2.5)):
        for count, beta, seed, field in ((18, cold, 17, 0), (19, moderate, 314, 0.05),
                                         (20, moderate, 0, 0.05), (20, cold, 23, 0.2)):
            name = f"{family}_n{count}_beta{beta}_seed{seed}"
            yield name, generated_instance(family, count, beta, seed, field)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--stress", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("validation_results.json"))
    args = parser.parse_args()
    cases = []
    if args.input_dir:
        cases.extend((path.stem, json.loads(path.read_text())) for path in sorted(args.input_dir.glob("*.json")))
    if args.stress:
        cases.extend(stress_cases())
    if not cases:
        parser.error("provide --input-dir and/or --stress")
    root = Path(__file__).resolve().parent
    records = []
    with tempfile.TemporaryDirectory(prefix="validation_", dir=root) as temporary:
        temporary = Path(temporary)
        for name, instance in cases:
            source = temporary / (name + "_instance.json")
            destination = temporary / (name + "_model.json")
            source.write_text(json.dumps(instance))
            started = time.monotonic()
            process = subprocess.run([sys.executable, str(root / "solve.py"), str(source), str(destination)],
                                     capture_output=True, text=True, timeout=118, cwd=root)
            runtime = time.monotonic() - started
            if process.returncode:
                raise RuntimeError(process.stderr)
            model = json.loads(destination.read_text())
            validate(model, instance["n"])
            result = metrics(instance, model)
            record = {"name": name, "n": instance["n"], "runtime_seconds": runtime,
                      "artifact_bytes": destination.stat().st_size,
                      "peak_child_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss, **result}
            records.append(record)
            print(json.dumps(record), flush=True)
            args.output.write_text(json.dumps(records, indent=2))
            if result["kl"] > 0.12 or result["ess"] < 0.25:
                raise AssertionError(f"quality check failed: {record}")


if __name__ == "__main__":
    main()
