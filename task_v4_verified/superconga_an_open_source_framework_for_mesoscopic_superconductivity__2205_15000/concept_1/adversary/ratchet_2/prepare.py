from common import ROOT, CONCEPT, PREVIOUS, ASSETS, digest, now, read_json, relative, write_json

from collections import defaultdict, deque
import shutil
import sys

import numpy as np


def copy_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def main():
    if (ROOT / "corpus/manifest.json").exists():
        raise RuntimeError("corpus already frozen; refusing overwrite")
    (ROOT / "scratch").mkdir(exist_ok=True)
    for name in ("independent.py", "evaluate.py"):
        copy_file(CONCEPT / "evaluator" / name, ASSETS / "evaluator" / name)
    copy_file(CONCEPT.parent / "authoring/sandbox.py", ASSETS / "authoring/sandbox.py")
    copy_file(PREVIOUS / "cpu_monitor/run.py", ASSETS / "cpu_monitor/run.py")
    for source in sorted((CONCEPT / "participant").rglob("*")):
        if source.is_file() and not source.is_symlink() and "__pycache__" not in source.parts:
            copy_file(source, ASSETS / "participant" / source.relative_to(CONCEPT / "participant"))
    for name in ("analysis.json", "validation.json", "broad_index.json", "report.json"):
        copy_file(PREVIOUS / name, ROOT / "provenance/ratchet_1" / name)
    copy_file(CONCEPT / "evaluator/release_manifest.json", ROOT / "provenance/A2_release_manifest.json")
    copy_file(CONCEPT / "evaluator/hidden/target.json", ROOT / "provenance/A2_target.json")
    sys.path.insert(0, str(ASSETS / "evaluator"))
    from independent import checked_field, energy_gradient, lower_bound
    policy = read_json(ROOT / "policy.json")
    index = read_json(PREVIOUS / "broad_index.json")
    validation = read_json(PREVIOUS / "validation.json")
    if not validation["passed"] or len(index) > policy["maximum_physical_cases"]:
        raise ValueError("unvalidated or oversized source corpus")
    records = []
    for details in index:
        name = details["case_id"]
        original = PREVIOUS / "cases" / (name + ".json")
        metadata = PREVIOUS / "metadata" / (name + ".json")
        if digest(original) != details["case_sha256"]:
            raise ValueError("original physical input changed: " + name)
        case = read_json(original)
        original_path = ROOT / "corpus/original_cases" / original.name
        copy_file(original, original_path)
        copy_file(metadata, ROOT / "corpus/metadata" / metadata.name)
        initial_source = PREVIOUS / "runs/champion_cold" / name / "field.npz"
        initial = checked_field(initial_source, case, policy["result_max_bytes"])
        initial_energy, unused, initial_rms = energy_gradient(case, initial)
        if initial_rms > policy["stationarity_rms_max"]:
            raise ValueError("provided start is not stationary")
        candidates = []
        for path in sorted((PREVIOUS / "runs").glob("*/" + name + "/field.npz")):
            record_path = path.parent / "record.json"
            if not record_path.exists() or not read_json(record_path).get("valid", False):
                continue
            field = checked_field(path, case, policy["result_max_bytes"])
            energy, unused, rms = energy_gradient(case, field)
            if rms > policy["stationarity_rms_max"] or energy < lower_bound(case) - 1e-8:
                continue
            candidates.append({"source": str(path.relative_to(CONCEPT)), "sha256": digest(path), "record_source": str(record_path.relative_to(CONCEPT)), "record_sha256": digest(record_path), "energy": energy, "gradient_rms": rms})
        if not candidates:
            raise ValueError("no attained references: " + name)
        witness = min(candidates, key=lambda candidate: candidate["energy"])
        witness_path = ROOT / "corpus/witness_fields" / (name + ".npz")
        baseline_path = ROOT / "corpus/initial_fields" / (name + ".npz")
        copy_file(CONCEPT / witness["source"], witness_path)
        copy_file(initial_source, baseline_path)
        case["initial_real"] = initial.real.tolist()
        case["initial_imag"] = initial.imag.tolist()
        replay_path = ROOT / "corpus/replay_cases" / (name + ".json")
        write_json(replay_path, case)
        gap = initial_energy - witness["energy"]
        records.append({
            "case_id": name, "family": details["family"], "shape": details["shape"], "active_sites": details["active_sites"], "holes": details["actual_holes"],
            "original_case_path": relative(original_path), "case_path": relative(replay_path), "metadata_path": "corpus/metadata/" + name + ".json",
            "baseline_path": relative(baseline_path), "baseline_energy": initial_energy, "baseline_gradient_rms": initial_rms,
            "baseline_source": str(initial_source.relative_to(CONCEPT)), "baseline_source_sha256": digest(initial_source),
            "witness_path": relative(witness_path), "witness_energy": witness["energy"], "witness_gradient_rms": witness["gradient_rms"], "witness_provenance": witness,
            "reference_gap": gap, "selected_for_replay": gap >= policy["minimum_reference_gap"],
            "selection_reason": "preexisting meaningful stationary-start gap" if gap >= policy["minimum_reference_gap"] else "preserved coverage only: preexisting gap below 0.5; no manufactured separation",
            "all_preexisting_reference_candidates": candidates,
        })
    groups = defaultdict(list)
    for record in records:
        if record["selected_for_replay"]:
            groups[record["family"]].append(record)
    queues = {family: deque(sorted(members, key=lambda record: (-record["reference_gap"], record["case_id"]))) for family, members in groups.items()}
    ordering = []
    while any(queues.values()):
        for family in sorted(queues):
            if queues[family]:
                ordering.append(queues[family].popleft()["case_id"])
    immutable = [ROOT / "policy.json"]
    for directory in (ASSETS, ROOT / "corpus", ROOT / "provenance"):
        immutable.extend(path for path in directory.rglob("*") if path.is_file())
    manifest = {"schema_version": 1, "frozen_at": now(), "status": "prepared_without_v2_inspection", "source": "ratchet_1 physically validated broad24, preexisting fields only", "physical_case_count": len(records), "selected_replay_count": len(ordering), "replay_order": ordering, "selected_family_counts": {family: len(members) for family, members in groups.items()}, "excluded_case_ids": [record["case_id"] for record in records if not record["selected_for_replay"]], "cases": records, "sha256": {relative(path): digest(path) for path in sorted(immutable)}, "v2_artifacts_read": False, "fresh_sessions_launched": 0, "solver_replays_run": 0}
    write_json(ROOT / "corpus/manifest.json", manifest)
    write_json(ROOT / "status.json", {"status": "awaiting_main_notification", "prepared_at": now(), "v2_artifacts_read": False, "solver_replays_run": 0, "physical_cases_preserved": len(records), "selected_replay_cases": len(ordering), "manifest": "corpus/manifest.json", "manifest_sha256": digest(ROOT / "corpus/manifest.json"), "gate": policy["result_gate"], "fresh_sessions_launched": 0})
    print({key: manifest[key] for key in ("status", "physical_case_count", "selected_replay_count", "selected_family_counts", "replay_order")})


if __name__ == "__main__":
    main()
