import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import time


PRIVATE = Path(__file__).resolve().parent
ROOT = PRIVATE.parents[2]
CONCEPT = ROOT / "concept_1"
PHASES = ["early_python", "before_rlimit", "after_rlimit", "before_seccomp_load", "before_runpy"]


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Nonregular artifact: " + str(path))
        result = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1048576), b""):
            result.update(chunk)
    return result.hexdigest()


def tree(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlink is not allowed: " + str(path))
        if path.is_file():
            result[str(path.relative_to(directory))] = digest(path)
        elif not path.is_dir():
            raise ValueError("Nonregular artifact: " + str(path))
    return result


def verify_originals(manifest):
    changed = [name for name, expected in manifest["original_files_sha256"].items()
               if not (ROOT / name).is_file() or digest(ROOT / name) != expected]
    if tree(CONCEPT / "attempts/v_3") != manifest["submission_sha256"]:
        changed.append("concept_1/attempts/v_3 full manifest")
    if tree(CONCEPT / "participant") != manifest["participant_sha256"]:
        changed.append("concept_1/participant full manifest")
    return changed


def within(value, directory):
    return value == str(directory) or value.startswith(str(directory) + "/")


def process_snapshot(outer_pids, staging_directories):
    result = {"sampled_utc": stamp(), "scope": "escalated_host_proc", "visible_processes": 0,
              "same_uid_processes": 0, "inaccessible_or_vanished_entries": 0,
              "time_limit_hit": False, "outer_pids_present": {str(pid): (Path("/proc") / str(pid)).exists() for pid in outer_pids}, "candidates": []}
    roots = [PRIVATE] + [Path(directory) for directory in staging_directories]
    deadline = time.monotonic() + 20
    for process_dir in Path("/proc").iterdir():
        if not process_dir.name.isdigit():
            continue
        result["visible_processes"] += 1
        if time.monotonic() > deadline:
            result["time_limit_hit"] = True
            break
        try:
            if process_dir.stat().st_uid != os.getuid():
                continue
            result["same_uid_processes"] += 1
            fields = (process_dir / "stat").read_text().rsplit(")", 1)[1].split()
            group_match = int(fields[2]) in outer_pids or int(fields[3]) in outer_pids
            try:
                cwd = os.readlink(process_dir / "cwd")
                cwd_match = any(within(cwd, directory) for directory in roots)
            except (FileNotFoundError, PermissionError):
                cwd_match = False
            references = []
            for descriptor in (process_dir / "fd").iterdir():
                try:
                    destination = os.readlink(descriptor).removesuffix(" (deleted)")
                    if any(within(destination, directory) for directory in roots):
                        info = (process_dir / "fdinfo" / descriptor.name).read_text()
                        flags = int(re.search(r"^flags:\s*(\d+)", info, re.M).group(1), 8)
                        references.append({"fd": int(descriptor.name), "path": destination, "writable": bool(flags & os.O_ACCMODE)})
                except (FileNotFoundError, PermissionError, ProcessLookupError):
                    continue
            if group_match or cwd_match or references:
                result["candidates"].append({"pid": int(process_dir.name), "state": fields[0], "pgrp": int(fields[2]), "session": int(fields[3]), "launch_group_match": group_match, "diagnostic_cwd": cwd_match, "references": references})
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            result["inaccessible_or_vanished_entries"] += 1
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute:
        raise SystemExit("Explicit --execute is required; no solver was launched")
    manifest = json.loads((PRIVATE / "launch_manifest.json").read_text())
    request = json.loads((PRIVATE / "request.json").read_text())
    assert digest(PRIVATE / "request.json") == manifest["request_sha256"]
    assert manifest["maximum_runs"] == 3
    assert request["case_id"] == "g1_ea6c7b33ae689d1cfeeec166ffd0a4a0"
    assert request["budget_seconds"] == 6 and request["wall_seconds"] == 30
    assert not verify_originals(manifest)
    for name, expected in manifest["private_code_sha256"].items():
        assert digest(PRIVATE / name) == expected, name
    runs_root = PRIVATE / "runs"
    runs_root.mkdir(exist_ok=False)
    write_json(PRIVATE / "execution.json", {"state": "running", "started_utc": stamp(), "maximum_runs": 3, "automatic_retries": 0})
    specification = importlib.util.spec_from_file_location("private_infra5_runner", PRIVATE / "runtime/sandbox_runner.py")
    runner = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(runner)
    original_run_local = runner.run_local
    rows = []
    outer_pids = []
    staging_directories = []
    stop_reason = None
    for ordinal in range(1, 4):
        if verify_originals(manifest):
            stop_reason = "Original immutable hashes changed; no further diagnostic runs"
            break
        location = runs_root / ("trial_" + str(ordinal))
        location.mkdir(exist_ok=False)
        write_json(location / "reservation.json", {"ordinal": ordinal, "reserved_utc": stamp(), "case_id": request["case_id"], "budget_seconds": 6, "wall_seconds": 30})

        def checked_run_local(submission, participant, scratch, features, public_source):
            staged_submission = tree(submission)
            staged_public = tree(public_source)
            worker_path = public_source.parent / "worker.py"
            staged_worker = digest(worker_path)
            record = {"staged_utc": stamp(), "submission_sha256": staged_submission,
                      "public_sha256": staged_public, "worker_sha256": staged_worker,
                      "submission_matches_original": staged_submission == manifest["submission_sha256"],
                      "public_matches_original": staged_public == manifest["participant_sha256"],
                      "worker_matches_instrumented_copy": staged_worker == manifest["private_code_sha256"]["runtime/worker.py"],
                      "source_directory": str(public_source.parent), "feature_request_matches": features == request,
                      "submission_and_public_mounts": "read-only; unchanged original bwrap allowlist",
                      "protected_phase_channel": "pre-user pipe closed in child before runpy; parent holds phase records"}
            write_json(location / "staging_manifest.json", record)
            assert all(record[name] for name in ("submission_matches_original", "public_matches_original", "worker_matches_instrumented_copy", "feature_request_matches"))
            staging_directories.append(str(public_source.parent))
            return original_run_local(submission, participant, scratch, features, public_source)

        runner.run_local = checked_run_local
        begun = stamp()
        process_result = None
        failure = None
        try:
            process_result = runner.run_submission(CONCEPT / "attempts/v_3", CONCEPT / "participant", location, dict(request))
        except Exception as error:
            failure = {"type": type(error).__name__, "message": str(error)}
        write_json(location / "process.json", {"started_utc": begun, "finished_utc": stamp(), "result": process_result, "exception": failure, "official_grade": False})
        resource_path = location / "resource.json"
        accounting_error = None
        try:
            accounting = json.loads(resource_path.read_text()) if resource_path.is_file() else None
            if accounting is not None and not isinstance(accounting, dict):
                raise ValueError("Accounting must be a JSON object")
        except (ValueError, OSError) as error:
            accounting = None
            accounting_error = str(error)
        phases = accounting.get("phases", []) if isinstance(accounting, dict) else []
        phase_map = {phase["phase"]: phase for phase in phases}
        complete = isinstance(accounting, dict) and accounting.get("phase_channel_complete") is True and [phase.get("phase") for phase in phases] == PHASES
        cpu_accounted = isinstance(process_result, dict) and process_result.get("cpu_accounted") is True
        version_matches = isinstance(accounting, dict) and accounting.get("diagnostic_version") == "infra5-private-phase-v1"
        finite_phase_data = complete and all(isinstance(phase.get(name), (int, float)) and math.isfinite(phase[name]) and phase[name] >= 0 for phase in phases for name in ("cpu_user_seconds", "cpu_system_seconds", "cpu_process_seconds", "monotonic_seconds", "wall_since_spawn_seconds"))
        phase_limits_match = complete and all(phase["rlimit_cpu"] == ([10, 11] if phase["phase"] in ("early_python", "before_rlimit") else [8, 9]) for phase in phases)
        checksum_ok = isinstance(accounting, dict) and all(isinstance(accounting.get(name), (int, float)) and math.isfinite(accounting[name]) for name in ("cpu_seconds", "wait4_ru_utime", "wait4_ru_stime")) and abs(accounting["cpu_seconds"] - accounting["wait4_ru_utime"] - accounting["wait4_ru_stime"]) < 1e-9
        row = {"ordinal": ordinal, "case_id": request["case_id"], "started_utc": begun, "finished_utc": stamp(),
               "exception": failure, "cpu_accounted": cpu_accounted, "phase_channel_complete": complete,
               "phase_limits_match": phase_limits_match, "wait4_sum_matches": checksum_ok,
               "instrumentation_recorded": cpu_accounted and complete and phase_limits_match and checksum_ok and version_matches and finite_phase_data,
               "accounting_parse_error": accounting_error, "instrumentation_version_matches": version_matches,
               "phase_values_finite": finite_phase_data,
               "cpu_seconds": accounting.get("cpu_seconds") if accounting else None,
               "wait4_ru_utime": accounting.get("wait4_ru_utime") if accounting else None,
               "wait4_ru_stime": accounting.get("wait4_ru_stime") if accounting else None,
               "worker_wall_seconds": accounting.get("worker_wall_seconds") if accounting else None,
               "worker_timed_out": accounting.get("worker_timed_out") if accounting else None,
               "worker_exitcode": accounting.get("worker_exitcode") if accounting else None,
               "wait4_status": accounting.get("wait4_status") if accounting else None,
               "parent_cpu_before": accounting.get("parent_cpu_before") if accounting else None,
               "parent_cpu_after_reap": accounting.get("parent_cpu_after_reap") if accounting else None,
               "parent_cpu_interval": accounting.get("parent_cpu_interval") if accounting else None,
               "phases": phases,
               "process_valid_under_unchanged_predicate": process_result.get("process_valid") if process_result else False,
               "original_hash_changes": verify_originals(manifest)}
        if complete:
            before_user = phase_map["before_runpy"]
            before_filter = phase_map["before_seccomp_load"]
            row["child_cpu_before_runpy"] = before_user["cpu_user_seconds"] + before_user["cpu_system_seconds"]
            row["seccomp_load_to_runpy_cpu_delta"] = row["child_cpu_before_runpy"] - before_filter["cpu_user_seconds"] - before_filter["cpu_system_seconds"]
            row["seccomp_load_to_runpy_system_delta"] = before_user["cpu_system_seconds"] - before_filter["cpu_system_seconds"]
            row["wait4_total_minus_preuser_self_cpu"] = accounting["cpu_seconds"] - row["child_cpu_before_runpy"]
        outer_path = location / "outer_process.json"
        if outer_path.is_file():
            outer_pids.append(json.loads(outer_path.read_text())["pid"])
        write_json(location / "summary.json", row)
        write_json(location / "artifact_manifest.json", tree(location))
        rows.append(row)
        write_json(PRIVATE / "checkpoint.json", {"completed_diagnostic_runs": len(rows), "maximum_runs": 3, "runs": rows})
        print(json.dumps({key: row[key] for key in ("ordinal", "cpu_seconds", "wait4_ru_utime", "wait4_ru_stime", "worker_wall_seconds", "worker_exitcode", "worker_timed_out", "instrumentation_recorded")}), flush=True)
        if row["original_hash_changes"]:
            stop_reason = "Original immutable hashes changed; diagnostic stopped"
            break
    first_artifacts = tree(runs_root)
    first_processes = process_snapshot(outer_pids, staging_directories)
    time.sleep(12)
    second_artifacts = tree(runs_root)
    second_processes = process_snapshot(outer_pids, staging_directories)
    changed_originals = verify_originals(manifest)
    report = {"version": 1, "diagnostic_only": True, "official_regrade": False, "created_utc": stamp(),
              "case_id": request["case_id"], "completed_diagnostic_runs": len(rows), "maximum_runs": 3,
              "automatic_retries": 0, "stop_reason": stop_reason, "runs": rows,
              "all_claimed_instrumentation_recorded": len(rows) == 3 and all(row["instrumentation_recorded"] for row in rows),
              "observed_cpu_above_child_hard9": [row["ordinal"] for row in rows if row["cpu_accounted"] and row["cpu_seconds"] > 9],
              "observed_cpu_above_inherited_hard11": [row["ordinal"] for row in rows if row["cpu_accounted"] and row["cpu_seconds"] > 11],
              "original_hash_changes": changed_originals, "originals_unchanged": not changed_originals,
              "artifact_hashes_stable_over_12_seconds": first_artifacts == second_artifacts,
              "process_snapshots": [first_processes, second_processes],
              "temporary_staging_removed": {directory: not Path(directory).exists() for directory in staging_directories},
              "interpretation": "Bounded diagnostic evidence only. If the original anomaly does not reproduce, attribution remains inconclusive; neither harness correctness nor a solver defect follows.",
              "measurement_perturbation": "Instrumented bootstrap and pre-user pipe add small work and may change timing/spawn behavior. Original ephemeral local-/tmp staging is retained and removed by the copied runner; retained artifacts are exclusively in this private directory.",
              "scoring_or_physical_measurements_performed": False}
    write_json(PRIVATE / "results.json", report)
    write_json(PRIVATE / "execution.json", {"state": "complete", "completed_utc": stamp(), "completed_diagnostic_runs": len(rows), "maximum_runs": 3, "no_more_runs_authorized": True})
    write_json(PRIVATE / "artifact_manifest.json", tree(PRIVATE))
    print(json.dumps({"state": "complete", "runs": len(rows), "instrumentation_recorded": report["all_claimed_instrumentation_recorded"], "originals_unchanged": report["originals_unchanged"], "cpu_above_hard9": report["observed_cpu_above_child_hard9"], "output_stable": report["artifact_hashes_stable_over_12_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
