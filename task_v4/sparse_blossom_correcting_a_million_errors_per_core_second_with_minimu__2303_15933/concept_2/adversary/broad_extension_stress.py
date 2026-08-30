import sys

sys.dont_write_bytecode = True

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import time

import numpy as np

import extension_stress as extension


def directions(artifact):
    rates = np.asarray(artifact["probabilities"])
    projection = extension.projection_matrix()
    orientation = np.asarray([1] * 24 + [-1] * 15)
    rows = [[1, *tail] for tail in itertools.product((-1, 1), repeat=3) if min(tail) < 1]
    columns = [[1, *tail] for tail in itertools.product((-1, 1), repeat=4) if min(tail) < 1]
    raw_fields = [("orientation", "horizontal_vertical", orientation)]
    for family, modes in (("oriented_rows", rows), ("oriented_columns", columns)):
        for signs in modes:
            field = [signs[detector % 4 if family == "oriented_rows" else detector // 4] for detector in range(20)]
            raw_fields.append((family, "".join("+" if value > 0 else "-" for value in signs), orientation * (projection @ field)))
    for row_signs, column_signs in itertools.product(rows, columns):
        field = [row_signs[detector % 4] * column_signs[detector // 4] for detector in range(20)]
        name = "".join("+" if value > 0 else "-" for value in row_signs) + "/" + "".join("+" if value > 0 else "-" for value in column_signs)
        raw_fields.append(("row_column_products", name, projection @ field))
        raw_fields.append(("oriented_products", name, orientation * (projection @ field)))
    for left in range(5):
        for right in range(left, 5):
            for top in range(4):
                for bottom in range(top, 4):
                    if left == 0 and right == 4 and top == 0 and bottom == 3:
                        continue
                    field = [int(left <= detector // 4 <= right and top <= detector % 4 <= bottom) for detector in range(20)]
                    raw_fields.append(("all_rectangles", f"{left},{right}/{top},{bottom}", projection @ field))
    output = []
    for family, name, raw in raw_fields:
        centered = raw - np.dot(rates, raw) / math.fsum(rates)
        if np.max(np.abs(centered)) < 1e-14:
            continue
        levels = centered / np.max(np.abs(centered))
        output.append({"family": family, "name": name, "levels": levels})
    return output


def run(witness, output):
    started = time.monotonic()
    frozen = extension.frozen_hashes()
    checker = extension.load("broad_frontier", extension.GENERATION / "participant/workspace/check.py")
    oracle = extension.load("broad_oracle", extension.GENERATION / "evaluator/hidden/oracle.py")
    artifact = oracle.read_artifact(witness)
    rates = np.asarray(artifact["probabilities"])
    physical = int(checker.frontier(rates, artifact["syndrome"])[1][1] < checker.frontier(rates, artifact["syndrome"])[1][0])
    records = []
    for direction in directions(artifact):
        for background, amplitude in itertools.product((0.95, 1.05), (-0.05, 0.0, 0.05)):
            calibrated = background * rates * (1 + amplitude * direction["levels"])
            joint, costs = checker.frontier(calibrated, artifact["syndrome"])
            metrics = {"gap": float(costs[1 - physical] - costs[physical]), "posterior": float(joint[1 - physical] / sum(joint)), "mass": float(sum(joint))}
            failures = [metric for metric in extension.TARGETS if metrics[metric] < extension.TARGETS[metric]]
            records.append({"family": direction["family"], "name": direction["name"], "background": background, "amplitude": amplitude,
                            "levels": direction["levels"].tolist(), "metrics": metrics, "failures": failures,
                            "joint_probabilities": list(map(float, joint)), "class_costs": list(map(float, costs))})
    summaries = {}
    independent = []
    for family in sorted(set(record["family"] for record in records)):
        subset = [record for record in records if record["family"] == family]
        summaries[family] = {"points": len(subset), "actual_failure_clusters": dict(Counter("+".join(record["failures"]) or "none" for record in subset)),
                             "minimum_metrics": {metric: min(record["metrics"][metric] for record in subset) for metric in extension.TARGETS}}
        for metric in extension.TARGETS:
            worst = min(subset, key=lambda record: record["metrics"][metric])
            calibrated = worst["background"] * rates * (1 + worst["amplitude"] * np.asarray(worst["levels"]))
            native = oracle.native_many([calibrated], oracle.edge_masks(), 20, sum(1 << detector for detector in artifact["syndrome"]))[0]
            np.testing.assert_allclose(native[:2], worst["joint_probabilities"], rtol=3e-12, atol=0)
            np.testing.assert_allclose(native[2:], worst["class_costs"], rtol=3e-12, atol=1e-12)
            independent.append({"family": family, "metric": metric, "name": worst["name"], "background": worst["background"], "amplitude": worst["amplitude"],
                                "metrics": worst["metrics"], "independent_generic_passed": True})
    assert extension.frozen_hashes() == frozen
    report = {"state": "private_unfrozen_structural_probe", "artifact_sha256": hashlib.sha256(Path(witness).read_bytes()).hexdigest(),
              "targets_unchanged": extension.TARGETS, "tested_points": len(records), "summaries": summaries, "independent_checks": independent,
              "continuous_certificate_claimed": False, "frozen_assets_unchanged": frozen, "records": records, "elapsed_seconds": time.monotonic() - started}
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("witness")
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    destination = Path(arguments.output).resolve()
    if not destination.is_relative_to(extension.PRIVATE.resolve()):
        parser.error("outputs must stay in concept_2/adversary")
    run(arguments.witness, destination)
