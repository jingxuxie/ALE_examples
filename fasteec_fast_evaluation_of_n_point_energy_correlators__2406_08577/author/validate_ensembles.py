import json
import math
from pathlib import Path

import numpy as np


root = Path(__file__).resolve().parent.parent
checks = []
cache = {}


def moments(path):
    key = str(path.resolve())
    if key not in cache:
        data = np.loadtxt(path, ndmin=2)
        boundaries = np.flatnonzero(np.r_[True, data[1:, 0] != data[:-1, 0], True])
        starts = boundaries[:-1]
        totals = np.add.reduceat(data[:, 1], starts)
        fractions = data[:, 1] / np.repeat(totals, np.diff(boundaries))
        powered = {power: np.add.reduceat(fractions**power, starts) for power in [1.0, 1.5, 2.0]}
        fourth = []
        if len(starts) < 10000:
            for begin, end in zip(boundaries[:-1], boundaries[1:]):
                coefficients = [1.0, 0.0, 0.0, 0.0, 0.0]
                for value in fractions[begin:end]:
                    for degree in range(4, 0, -1):
                        coefficients[degree] += value * coefficients[degree - 1]
                fourth.append(24 * coefficients[4])
        cache[key] = powered, float(np.mean(fourth)) if fourth else None
    return cache[key]


for kind in ["weighted", "fractional", "resolved", "ewoc"]:
    private = root / "pilots" / kind / "private"
    manifest = json.loads((private / "challenge_pool" / "manifest.json").read_text())
    for case in manifest["cases"]:
        directory = private / "challenge_pool" / case["id"]
        job = json.loads((directory / "job.json").read_text())
        reference_file = private / "reference" / (case["id"] + ".json")
        if not reference_file.exists():
            raise RuntimeError("Missing reference " + str(reference_file))
        reference = json.loads(reference_file.read_text())
        if len(reference["histograms"]) != len(job["queries"]):
            raise RuntimeError("Reference/query count mismatch")
        for query, histogram in zip(job["queries"], reference["histograms"]):
            measured = math.fsum(histogram)
            target = None
            identity = None
            if kind == "weighted":
                powered, fourth = moments(directory / job["events_file"])
                target = float(np.mean(powered[query["kappa"]] ** query["order"]))
                identity = "weighted_total_moment"
            elif kind == "fractional":
                target, identity = 1.0, "pt_scheme_signed_total"
            elif kind == "resolved" and all(query.get(name, 1) == 1 for name in ["nu1", "nu2", "nu3"]):
                if query["order"] == 3:
                    target, identity = 1.0, "inclusive_three_point_total"
                else:
                    powered, target = moments(directory / job["events_file"])
                    identity = "contact_free_four_point_elementary_symmetric_total"
            elif kind == "ewoc" and query["geometry"] == "ee" and query["kappa"] == 1:
                target, identity = 1.0, "ee_energy_conservation"
            if target is not None:
                error = abs(measured - target) / max(abs(target), 1e-12)
                checks.append({"kind": kind, "case": case["id"], "identity": identity, "expected": target, "observed": measured, "relative_error": error, "passed": error < 1e-8})
            if kind in ["weighted", "resolved", "ewoc"]:
                checks.append({"kind": kind, "case": case["id"], "identity": "nonnegative_measure", "passed": min(histogram) >= -1e-13})
result = {"passed": all(check["passed"] for check in checks), "checks": len(checks), "max_relative_identity_error": max(check.get("relative_error", 0) for check in checks), "details": checks}
(root / "author" / "ensemble_validation.json").write_text(json.dumps(result, indent=2))
print(json.dumps({key: value for key, value in result.items() if key != "details"}, indent=2))
if not result["passed"]:
    raise RuntimeError("Independent ensemble identities failed")
