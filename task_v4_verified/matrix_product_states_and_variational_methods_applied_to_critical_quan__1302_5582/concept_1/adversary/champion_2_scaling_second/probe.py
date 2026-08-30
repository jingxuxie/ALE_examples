import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

from scipy.special import ellipk


WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
sys.path.insert(0, str(WORK / "runtime"))
from sandbox_runner import run_submission
from trusted_contractor import load_mps, measure


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def prepare():
    sources = {
        "v4": (ROOT / "champions/generation_2/submission",
               ("solve.py", "fast.py", "optimizer.py", "contractor.py")),
        "v3": (ROOT / "attempts/v_3",
               ("solve.py", "optimizer.py", "contractor.py", "native.py",
                "local_solver.c", "local_solver.so")),
    }
    manifest = {}
    for label, (directory, filenames) in sources.items():
        destination = WORK / "source" / label
        destination.mkdir(parents=True, exist_ok=True)
        manifest[label] = {}
        for filename in filenames:
            source = directory / filename
            target = destination / filename
            if target.exists():
                assert digest(target) == digest(source)
            else:
                shutil.copy2(source, target)
            manifest[label][filename] = digest(target)
    manifest["runtime"] = {
        name: digest(WORK / "runtime" / name)
        for name in ("sandbox_runner.py", "worker.py", "trusted_contractor.py")
    }
    manifest["probe.py"] = digest(Path(__file__))
    path = WORK / "SOURCE_HASHES.json"
    if path.exists():
        assert json.loads(path.read_text()) == manifest
    else:
        write_json(path, manifest)
    return manifest


def requests():
    result = []
    for length_index, length in enumerate((512,)):
        quartic = 0.02
        renormalized = quartic / 65.0
        mass = renormalized - quartic * float(ellipk(4.0 / (renormalized + 4.0))) / (
            2.0 * math.pi * math.sqrt(renormalized + 4.0))
        for sector_index, sector in enumerate(("even", "odd")):
            result.append({
                "version": 1,
                "case_id": f"uv{length}_l020_{sector}",
                "seed": 841017 + length_index * 19 + sector_index,
                "n_sites": length,
                "local_dim": 14,
                "bond_cap": 24,
                "sector": sector,
                "omega": [0.65] * length,
                "mass2": [mass] * length,
                "lambda4": [quartic] * length,
                "field": [0.0] * length,
                "coupling": [1.0] * (length - 1),
            })
    return result


def summarize(rows):
    records = []
    for request in requests():
        matches = [row for row in rows if row["case_id"] == request["case_id"]]
        baseline = next((row for row in matches if row["label"] == "v4_40"), None)
        valid = [row for row in matches if row.get("physical_valid")]
        best = min(valid, key=lambda row: row["measurement"]["energy"]) if valid else None
        gap = None
        if baseline and baseline.get("physical_valid") and baseline["process"]["process_valid"] and best:
            gap = baseline["measurement"]["energy"] - best["measurement"]["energy"]
        records.append({
            "case_id": request["case_id"],
            "runs": matches,
            "screen": 1e-7 * request["n_sites"],
            "v4_energy_gap": gap,
            "above_screen": gap is not None and gap > 1e-7 * request["n_sites"],
            "attainable_reference": best["label"] if best else None,
            "reference_is_exact_ground_energy": False,
            "outside_current_public_domain": True,
        })
    write_json(WORK / "SUMMARY.json", {
        "cases": records,
        "completed_stage_count": len(rows),
        "observed_child_cpu_seconds": sum(row["process"]["cpu_seconds"] for row in rows),
        "new_task_generation_built": False,
        "public_domain_changed": False,
        "mass_selection_is_a_heuristic_not_a_finite_critical_point": True,
        "official_evaluator_invoked": False,
        "runtime_boundary": "private infra5 copy; only file/NPZ caps raised to 64 MiB; teacher budgets are private",
    })


def main():
    manifest = prepare()
    rows = []
    for base_request in requests():
        write_json(WORK / "requests" / (base_request["case_id"] + ".json"), base_request)
        teacher_cpu = 300.0 if base_request["n_sites"] == 256 else 600.0
        for label, source, cpu, wall in (("v4_40", "v4", 40.0, 120.0),
                                         ("v3_extended", "v3", teacher_cpu, teacher_cpu * 3.0)):
            directory = WORK / "runs" / base_request["case_id"] / label
            report_path = directory / "result.json"
            request = dict(base_request, budget_seconds=cpu, wall_seconds=wall)
            if report_path.exists():
                row = json.loads(report_path.read_text())
                assert row["request"] == request and row["source_hashes"] == manifest[source]
            else:
                assert not directory.exists(), f"Incomplete diagnostic is not automatically retried: {directory}"
                directory.mkdir(parents=True)
                write_json(directory / "request.json", request)
                process = run_submission(WORK / "source" / source, ROOT / "participant",
                                         directory / "scratch", request)
                row = {
                    "case_id": base_request["case_id"], "label": label,
                    "request": request, "source_hashes": manifest[source],
                    "recorded_utc": datetime.now(timezone.utc).isoformat(),
                    "process": {key: value for key, value in process.items() if key != "state_path"},
                    "physical_valid": False,
                }
                state = Path(process.get("state_path", directory / "missing.npz"))
                if state.is_file():
                    try:
                        row["measurement"] = measure(load_mps(state, base_request), base_request)
                        row["state"] = str(state.relative_to(WORK))
                        row["state_sha256"] = digest(state)
                        row["physical_valid"] = True
                    except Exception as error:
                        row["measurement_error"] = type(error).__name__ + ": " + str(error)
                write_json(report_path, row)
            rows.append(row)
            summarize(rows)
            print(json.dumps({"case_id": row["case_id"], "label": label,
                              "process_valid": row["process"]["process_valid"],
                              "cpu": row["process"]["cpu_seconds"],
                              "physical_valid": row["physical_valid"],
                              "energy": row.get("measurement", {}).get("energy")}), flush=True)
    assert prepare() == manifest


if __name__ == "__main__":
    main()
