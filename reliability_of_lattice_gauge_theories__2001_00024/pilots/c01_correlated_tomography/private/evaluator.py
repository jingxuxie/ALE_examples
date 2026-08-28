import argparse
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
from scoring import score


ROOT = Path(__file__).resolve().parents[1]
AUTHORING = ROOT.parent.parent / "authoring"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--participant", type=Path, default=ROOT / "participant")
    parser.add_argument("--split", choices=["screening", "challenge", "confirmation"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    sys.path.insert(0, str(AUTHORING))
    from isolated_eval import run_solver

    bundle = json.loads((ROOT / "private" / "challenge_pool" / f"{arguments.split}.json").read_text())
    started = time.monotonic()
    records = []
    for entry in bundle["cases"]:
        case = entry["case"]
        record = {"case_id": case["case_id"], "family": case["family"]}
        execution = run_solver(
            arguments.submission.resolve(), arguments.participant.resolve(), case,
            timeout=120, memory_gib=6,
        )
        record.update({
            "ok": bool(execution.get("ok")), "seconds": execution.get("seconds"),
            "max_rss_kib": execution.get("max_rss_kib"),
            "wall_seconds": execution.get("wall_seconds", execution.get("seconds")),
        })
        if execution.get("ok"):
            try:
                record.update(score(case, entry["reference"], execution["result"]))
            except (ValueError, KeyError, TypeError, OverflowError) as error:
                record.update({"ok": False, "error": f"Invalid result: {error}"})
        else:
            record["error"] = str(execution.get("error", "Solver failed"))[:2000]
            record["stderr"] = str(execution.get("stderr", ""))[-2000:]
        if not record["ok"]:
            record.update({"core": 0.0, "components": {"readout": 0.0, "certificate": 0.0}})
        records.append(record)
    families = sorted({record["family"] for record in records})
    family_scores = {
        family: sum(record["core"] for record in records if record["family"] == family)
        / sum(record["family"] == family for record in records)
        for family in families
    }
    component_scores = {
        component: sum(
            sum(record["components"][component] for record in records if record["family"] == family)
            / sum(record["family"] == family for record in records)
            for family in families
        ) / len(families)
        for component in ["readout", "certificate"]
    }
    report = {
        "schema_version": 1, "split": arguments.split,
        "mean_core": sum(family_scores.values()) / len(family_scores),
        "worst_family": min(family_scores.values()), "family_scores": family_scores,
        "component_scores": component_scores, "cases": records,
        "seconds": time.monotonic() - started,
        "reference_status": "conditional_numerical_optima_not_true_populations",
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, allow_nan=False))


if __name__ == "__main__":
    main()
