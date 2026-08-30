from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import aggregate, invalid_case, score_field
from independent import checked_field, energy_gradient, read_case


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    hidden = ROOT / "evaluator/hidden"
    if (hidden / "manifest.json").exists():
        raise RuntimeError("references are frozen; no overwriting")
    target = read_case(hidden / "target.json")
    specifications = read_case(hidden / "generation.json")
    references = []
    development = []
    hashes = {}
    kinds = ["expensive", "multistart", "qualified_portfolio", "qualified_multistart"]
    for details in specifications:
        name = details["case_id"]
        case_path = ROOT / ("participant/input/cases" if details["development"] else "evaluator/hidden/cases") / (name + ".json")
        case = read_case(case_path)
        baseline_path = ROOT / "attempts/baseline" / (name + ".npz")
        baseline_field = checked_field(baseline_path, case)
        baseline_energy, unused, baseline_rms = energy_gradient(case, baseline_field)
        best = (baseline_energy, baseline_path, baseline_field, baseline_rms)
        candidates = []
        for kind in kinds:
            path = ROOT / "attempts" / kind / (name + ".npz")
            if not path.exists():
                continue
            field = checked_field(path, case)
            energy, unused, rms = energy_gradient(case, field)
            candidates.append({"kind": kind, "energy": energy, "gradient_rms": rms})
            if rms <= target["stationarity_rms_max"] and energy < best[0]:
                best = (energy, path, field, rms)
        if details["development"]:
            development.append({"case_id": name, "baseline_energy": baseline_energy, "witness_energy": best[0], "gap": baseline_energy - best[0], "energy_at_65_percent_gap_closure": baseline_energy - 0.65 * (baseline_energy - best[0]), "baseline_gradient_rms": baseline_rms, "witness_gradient_rms": best[3], "witness_kind": "attained builder portfolio field; not a ground-state claim", "baseline_wall_seconds": read_case(baseline_path.with_suffix(".json"))["elapsed_seconds"]})
            continue
        if baseline_energy - best[0] < target["minimum_reference_gap"]:
            raise RuntimeError("insufficient verified gap for " + name)
        if baseline_rms > target["stationarity_rms_max"]:
            raise RuntimeError("unconverged baseline " + name)
        baseline_frozen = hidden / "baseline_fields" / (name + ".npz")
        witness_frozen = hidden / "witness_fields" / (name + ".npz")
        np.savez_compressed(baseline_frozen, psi=baseline_field)
        np.savez_compressed(witness_frozen, psi=best[2])
        record = {"case_id": name, "family": details["family"], "case_path": str(case_path.relative_to(ROOT)), "baseline_path": str(baseline_frozen.relative_to(ROOT)), "witness_path": str(witness_frozen.relative_to(ROOT)), "baseline_energy": baseline_energy, "witness_energy": best[0], "gap": baseline_energy - best[0], "baseline_gradient_rms": baseline_rms, "witness_gradient_rms": best[3], "witness_provenance": str(best[1].relative_to(ROOT)), "candidates": candidates}
        references.append(record)
        for path in (case_path, baseline_frozen, witness_frozen):
            hashes[str(path.relative_to(ROOT))] = sha256(path)
    for relative in ("evaluator/hidden/target.json", "participant/input/gl_model.py", "participant/baseline/solve.py"):
        hashes[relative] = sha256(ROOT / relative)
    manifest = {"schema_version": 1, "frozen_at": datetime.now(timezone.utc).isoformat(), "reference_kind": "attained upper bounds, unknown ground states", "no_fresh_model_sessions": True, "case_revision": "physical_lattice_v2", "cases": references, "immutable_sha256": hashes}
    (hidden / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "participant/input/development_targets.json").write_text(json.dumps({"schema_version": 1, "purpose": "public diagnostic targets, not hidden scoring references", "cases": development}, indent=2) + "\n")
    summaries = {}
    for kind in ["baseline"] + kinds:
        records = []
        for reference in references:
            name = reference["case_id"]
            path = ROOT / "attempts" / kind / (name + ".npz")
            timing = path.with_suffix(".json")
            if not path.exists() or not timing.exists():
                records.append(invalid_case(reference, "missing calibration field or timing"))
                continue
            case = read_case(ROOT / reference["case_path"])
            field = checked_field(path, case)
            timing_data = read_case(timing)
            elapsed = timing_data.get("wall_seconds", timing_data.get("elapsed_seconds"))
            record = score_field(reference, case, field, elapsed, target)
            if kind.startswith("qualified") and not timing_data["valid"]:
                record = invalid_case(reference, timing_data["reason"], elapsed)
            records.append(record)
        report = aggregate(records, target)
        report["timing_kind"] = "actual supplied sandbox, 60s contract" if kind.startswith("qualified") else "builder subprocess, not resource qualification"
        (ROOT / "attempts" / (kind + "_report.json")).write_text(json.dumps(report, indent=2) + "\n")
        summaries[kind] = {key: value for key, value in report.items() if key != "cases"}
    witness_records = []
    for reference in references:
        case = read_case(ROOT / reference["case_path"])
        field = checked_field(ROOT / reference["witness_path"], case)
        witness_records.append(score_field(reference, case, field, 0, target))
    witness_report = aggregate(witness_records, target)
    witness_report["passed"] = None
    witness_report["runtime_score"] = None
    witness_report["reason"] = "Stored-field energy feasibility only. Not a solver run, not 60-second achievability."
    for record in witness_report["cases"]:
        record.pop("wall_seconds", None)
        record.pop("runtime_score", None)
    (ROOT / "attempts/witness_feasibility.json").write_text(json.dumps(witness_report, indent=2) + "\n")
    (hidden / "calibration_summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
