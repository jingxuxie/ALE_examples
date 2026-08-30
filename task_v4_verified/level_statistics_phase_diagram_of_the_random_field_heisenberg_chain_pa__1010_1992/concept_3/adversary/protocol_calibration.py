import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sys

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))

import numpy as np
from exact import assess


def make_protocol(namespace="ale-c3-v1", members=8):
    families = []
    for name, scale, amplitude in (("jitter_004", 1.0, 0.04), ("jitter_012", 1.0, 0.12),
                                   ("scale_096", 0.96, 0.08), ("scale_104", 1.04, 0.08)):
        offsets = []
        for member in range(members):
            values = []
            for site in range(12):
                message = f"{namespace}|{name}|{member}|{site}".encode("ascii")
                number = int.from_bytes(hashlib.sha256(message).digest()[:8], "big")
                values.append(2.0 * number / (2 ** 64 - 1) - 1.0)
            offset = amplitude * (np.asarray(values) - np.mean(values))
            offsets.append(offset.tolist())
        families.append({"name": name, "scale": scale, "amplitude_before_centering": amplitude, "offsets": offsets})
    return {"schema_version": 1, "task_id": "pal_huse_spectral_center_falsification_v1",
            "length": 12, "dimension": 924, "rank_slice": [308, 616],
            "window_levels": 128, "energy_density_targets": [0.49, 0.50, 0.51],
            "targets": {"core": 0.060, "worst_family": 0.050, "base": 0.055,
                        "member_floor": 0.025, "members_required": 6},
            "witness_byte_limit": 16384, "evaluator_seconds": 180, "workers": 1, "blas_threads": 1,
            "field_constraints": {"base_bound": 8.0, "base_rms_min": 0.65,
                                  "base_pair_separation_min": 0.001, "base_symmetry_distance_min": 0.12,
                                  "derived_bound": 8.5, "derived_rms_min": 0.55,
                                  "derived_pair_separation_min": 1e-7, "derived_symmetry_distance_min": 0.05,
                                  "mean_absolute_tolerance": 1e-9, "gap_floor": 1e-10},
            "offset_namespace": namespace, "families": families}


def evaluate_candidate(candidate):
    witness = {"schema_version": 1, "fields": candidate["fields"], "orientation": -1}
    try:
        report = assess(witness, make_protocol())
        return {"index": candidate["index"], "witness": witness, "report": report}
    except ValueError as error:
        return {"index": candidate["index"], "error": str(error)}


def main():
    if (ROOT / "freeze.json").exists():
        raise RuntimeError("the protocol is frozen; recalibration must not overwrite it")
    protocol = make_protocol()
    destination = ROOT / "participant" / "input"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    records = [json.loads(line) for line in (ROOT / "adversary" / "refine_robust.jsonl").read_text().splitlines()]
    def strength(record):
        values = record["robust"]["triple_128"]
        return min(-value for value in values["families"] + [np.mean(values["scale"])])
    selected = sorted(records, key=strength, reverse=True)[:32]
    checked = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        with (ROOT / "adversary" / "final_protocol_candidates.jsonl").open("w") as output:
            for result in executor.map(evaluate_candidate, selected):
                checked.append(result)
                output.write(json.dumps(result) + "\n")
                output.flush()
                if "report" in result:
                    report = result["report"]
                    print(json.dumps({"index": result["index"], "core": report["core"],
                                      "worst_family": report["worst_family"], "pass": report["pass"],
                                      "coverage": [family["above_member_floor"] for family in report["families"]]}), flush=True)
                else:
                    print(json.dumps(result), flush=True)
    usable = [result for result in checked if "report" in result]
    best = max(usable, key=lambda result: (result["report"]["pass"], result["report"]["worst_family"], result["report"]["core"]))
    champions = ROOT / "adversary" / "champions"
    champions.mkdir(exist_ok=True)
    (champions / "witness.json").write_text(json.dumps(best["witness"], indent=2) + "\n")
    (champions / "selection.json").write_text(json.dumps(best, indent=2) + "\n")
    holdout = make_protocol("ale-c3-out-of-sample-20260828", members=32)
    holdout_report = assess(best["witness"], holdout)
    (champions / "holdout.json").write_text(json.dumps(holdout_report, indent=2) + "\n")
    print(json.dumps({"selected": best["index"], "pass": best["report"]["pass"],
                      "core": best["report"]["core"], "worst_family": best["report"]["worst_family"],
                      "holdout_core": holdout_report["core"], "holdout_worst_family": holdout_report["worst_family"]}), flush=True)


if __name__ == "__main__":
    main()
