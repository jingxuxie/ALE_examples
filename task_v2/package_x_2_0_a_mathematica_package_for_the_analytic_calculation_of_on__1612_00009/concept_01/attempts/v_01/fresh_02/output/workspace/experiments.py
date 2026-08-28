import argparse
import csv
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np

from plotting import plot_rows


CHANNELS = ("uv", "ir2", "ir1", "finite")


def flatten(payload, profile, config_hash):
    rows = []
    for case in payload["cases"]:
        trace = max([entry["residual"] for entry in case.get("observables", {}).values()] + [0.0])
        for identifier, result in case["integrals"].items():
            for order, coefficient in result["coefficients"].items():
                row = {"case_id": case["id"], "family": case["family"], "integral_id": identifier,
                       "order": order, "profile": profile, "config_hash": config_hash,
                       "seconds": result["seconds"], "work": result["work"],
                       "estimated_error": result["estimated_error"], "trace_residual": trace,
                       "strategy": result["strategy"]}
                for channel in CHANNELS:
                    row[channel + "_re"], row[channel + "_im"] = coefficient[channel]
                rows.append(row)
    return rows


def save_csv(path, rows):
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--requests", required=True)
    parser.add_argument("--profiles", nargs="+", default=["production", "fixed", "direct"])
    arguments = parser.parse_args()
    root = Path(arguments.submission).resolve()
    profiles = json.loads((root / "workspace/profiles.json").read_text())
    all_rows = []
    scaling = []
    predictions = {}
    (root / "runs").mkdir(exist_ok=True)
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    for profile in arguments.profiles:
        destination = root / "runs" / (profile + ".json")
        config_hash = hashlib.sha256(json.dumps(profiles[profile], sort_keys=True).encode()).hexdigest()
        started = time.perf_counter()
        subprocess.run(["bash", str(root / "run.sh"), "--requests", str(Path(arguments.requests).resolve()),
                        "--output", str(destination), "--profile", profile], check=True, env=environment)
        wall = time.perf_counter() - started
        predictions[profile] = json.loads(destination.read_text())
        rows = flatten(predictions[profile], profile, config_hash)
        all_rows.extend(rows)
        for case in predictions[profile]["cases"]:
            scaling.append({"case_id": case["id"], "family": case["family"], "profile": profile,
                            "config_hash": config_hash, "seconds": case["seconds"], "campaign_seconds": wall,
                            "work": sum(entry["work"] for entry in case["integrals"].values()),
                            "max_internal_error": max(entry["estimated_error"] for entry in case["integrals"].values()),
                            "trace_residual": max([entry["residual"] for entry in case.get("observables", {}).values()] + [0.0])})
    reference_profile = "direct" if "direct" in predictions else "production"
    reference_rows = {(row["case_id"], row["integral_id"], row["order"]): row
                      for row in all_rows if row["profile"] == reference_profile}
    comparison = []
    for row in all_rows:
        reference = reference_rows[(row["case_id"], row["integral_id"], row["order"])]
        columns = [channel + component for channel in CHANNELS for component in ("_re", "_im")]
        error = max(abs(row[column] - reference[column]) for column in columns)
        scale = max(max(abs(reference[column]) for column in columns), 1e-300)
        row["relative_to_direct"] = error / scale
        comparison.append({"case_id": row["case_id"], "integral_id": row["integral_id"], "order": row["order"],
                           "profile": row["profile"], "work": row["work"], "relative_to_direct": error / scale})
    for row in scaling:
        row["max_relative_to_direct"] = max(item["relative_to_direct"] for item in all_rows
                                             if item["case_id"] == row["case_id"] and item["profile"] == row["profile"])
    save_csv(root / "results.csv", [row for row in all_rows if row["profile"] == "production"])
    save_csv(root / "ablation.csv", all_rows)
    save_csv(root / "scaling.csv", scaling)
    plot_rows(comparison, root / "figures/primary_result.png", "work", "relative_to_direct")
    plot_rows(scaling, root / "figures/robustness_or_scaling.png", "work", "seconds")
    claims = {"schema": 1, "claims": [
        {"id": "production_uses_more_work", "table": "scaling.csv", "metric": "work",
         "left_profile": "production", "right_profile": "fixed", "relation": ">=", "case_ids": []}
    ]}
    if not (root / "claims.json").exists():
        (root / "claims.json").write_text(json.dumps(claims, indent=2))


if __name__ == "__main__":
    main()
