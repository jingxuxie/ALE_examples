import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

ROOT = Path(__file__).resolve().parent
OBSERVABLES = ["torque", "magnetization", "energy", "constraint_drift", "norm_error",
               "lower_perpendicular", "upper_perpendicular", "surface_parallel",
               "surface_perpendicular", "acceptance"]
PHYSICAL_COLUMNS = [0, 1, 2, 5, 6, 7, 8]


def block_summary(records, column):
    values = records[:, column]
    mean = float(np.average(values, weights=records[:, 3]))
    errors = []
    for grouping in [1, 2, 4, 8]:
        grouped = values.reshape(-1, grouping).mean(axis=1)
        errors.append(float(grouped.std(ddof=1) / math.sqrt(len(grouped))))
    return mean, max(errors)


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    reference = json.loads((ROOT / "reference/scout.json").read_text())
    report = {"protocol": json.loads((ROOT / "scout_protocol.json").read_text()), "cases": {}}
    for entry in manifest:
        case_id = entry["id"]
        assert hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
        source = reference[case_id]
        worst = max(((record["rhat"][column], record["angle"], OBSERVABLES[column])
                     for record in source["angles"] for column in PHYSICAL_COLUMNS))
        record = {"n_spins": entry["n_spins"], "source_max_rhat": worst[0],
                  "source_worst_angle": worst[1], "source_worst_observable": worst[2],
                  "reference_certified": False, "full_score": None,
                  "reference_limit": "Four-start 10k-burn/10k-production scouts are not converged golden references."}
        folder = ROOT / "scouts" / case_id
        if not (folder / "execution.json").exists():
            record["decision"] = "REJECT_REFERENCE" if source["max_rhat"] > 1.5 else "PENDING"
            report["cases"][case_id] = record
            continue
        execution = json.loads((folder / "execution.json").read_text())
        assert execution["returncode"] == 0 and not execution["timeout"]
        prediction = json.loads((folder / "output.json").read_text())
        blocks = np.loadtxt(folder / "output.blocks.txt")
        comparisons = []
        for index, angle in enumerate(prediction["sample_angles"]):
            source_angle = min(source["angles"], key=lambda item: abs(item["angle"] - angle))
            assert abs(source_angle["angle"] - angle) < 1e-12
            rows = blocks[blocks[:, 0] == index]
            comparison = {"angle": angle}
            for name, raw_column, source_column in [("torque", 4, 0), ("magnetization", 5, 1)]:
                mean, sem = block_summary(rows, raw_column)
                reference_mean = source_angle["mean"][source_column]
                reference_sem = source_angle["sem"][source_column]
                combined = math.hypot(sem, reference_sem)
                comparison[name] = {"submitted_mean": mean, "submitted_sem": sem,
                                    "reference_mean": reference_mean, "reference_sem": reference_sem,
                                    "difference": mean - reference_mean,
                                    "combined_sem_units": (mean - reference_mean) / combined}
            comparisons.append(comparison)
        acceptance = []
        pattern = (r"angle (\S+) torque (\S+) m (\S+) sweeps (\d+) warmup (\d+) "
                   r"acceptance (\S+) (\S+) (\S+)")
        for match in re.finditer(pattern, execution["stderr"]):
            fields = match.groups()
            acceptance.append({"angle": float(fields[0]), "sweeps": int(fields[3]),
                               "warmup": int(fields[4]), "heatbath": float(fields[5]),
                               "overrelaxation": float(fields[6]), "cluster": float(fields[7])})
        max_torque = max(abs(item["torque"]["combined_sem_units"]) for item in comparisons)
        record.update(comparisons=comparisons, acceptance=acceptance,
                      max_torque_combined_sem_units=max_torque, elapsed_seconds=execution["elapsed"],
                      max_magnetization_combined_sem_units=max(abs(item["magnetization"]["combined_sem_units"])
                                                             for item in comparisons),
                      reduced_grid_target_ess=prediction.get("reweighting_effective_samples"),
                      ess_limit="Three-window target ESS is not evidence of failure of the default fifteen-window solver.",
                      decision="NO_SIGNIFICANT_SCOUT_DISCREPANCY" if max_torque < 3 else "REQUIRES_LONG_REFERENCE")
        report["cases"][case_id] = record
    (ROOT / "scout_analysis.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({name: {key: row[key] for key in ["decision", "source_max_rhat", "max_torque_combined_sem_units"]
                             if key in row} for name, row in report["cases"].items()}, indent=2))


if __name__ == "__main__":
    main()
