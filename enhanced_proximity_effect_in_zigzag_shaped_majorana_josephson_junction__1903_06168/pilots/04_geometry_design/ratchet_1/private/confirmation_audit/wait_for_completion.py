"""Observe only the queued confirmation's launch and score report files."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time


HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "runs" / "confirmation"
SUCCESS = {"complete", "completed", "finished", "success", "succeeded", "done"}
FAILURE = {"failed", "failure", "error", "timeout", "timed_out", "cancelled", "canceled", "killed"}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    if not path.resolve().is_relative_to(HERE):
        raise ValueError("All watcher writes must remain in confirmation_audit")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def observe(name):
    path = RUN / name
    metadata = {"path": str(path), "exists": path.is_file(), "readable_json": False}
    if not metadata["exists"]:
        return None, metadata
    try:
        payload = path.read_bytes()
        document = json.loads(payload)
        metadata.update(
            readable_json=True, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
            modified_unix=path.stat().st_mtime,
            top_level_keys=list(document) if isinstance(document, dict) else None,
        )
        if isinstance(document, dict):
            for key in ("complete", "status", "state", "returncode", "return_code", "exit_code"):
                value = document.get(key)
                if isinstance(value, (str, int, float, bool)) or value is None:
                    metadata[key] = value
        return document, metadata
    except (OSError, ValueError) as error:
        metadata["read_error"] = repr(error)
        return None, metadata


def classification(document):
    if not isinstance(document, dict):
        return "unknown"
    status = str(document.get("status", document.get("state", ""))).lower()
    if status in FAILURE:
        return "terminal_failure"
    if document.get("complete") is True or status in SUCCESS:
        return "terminal_success_marker"
    if document.get("complete") is False or status in {"running", "pending", "queued", "in_progress", "starting"}:
        return "in_progress"
    for key in ("returncode", "return_code", "exit_code"):
        if isinstance(document.get(key), int) and document[key] != 0:
            return "terminal_failure"
    return "unknown"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-seconds", type=float, default=7200)
    parser.add_argument("--poll-seconds", type=float, default=30)
    arguments = parser.parse_args()
    if not 0 < arguments.wait_seconds <= 7200 or arguments.poll_seconds < 1:
        parser.error("Use a wait interval up to two hours and a positive polling interval")
    allowed = os.sched_getaffinity(0)
    if 69 in allowed:
        os.sched_setaffinity(0, {69})
    started = time.monotonic()
    deadline = started + arguments.wait_seconds
    save(HERE / "wait_session.json", {
        "started_utc": stamp(), "started_local": datetime.now().astimezone().isoformat(),
        "wait_cap_seconds": arguments.wait_seconds, "poll_seconds": arguments.poll_seconds,
        "observed_paths_only": [str(RUN / "launch.json"), str(RUN / "score.json")],
        "no_agents_solvers_graders_launched": True, "attempt_and_transcript_not_accessed_by_watcher": True,
        "affinity": sorted(os.sched_getaffinity(0)),
    })
    previous_signature = None
    last_heartbeat = -300.0
    while True:
        launch, launch_metadata = observe("launch.json")
        score, score_metadata = observe("score.json")
        launch_state = classification(launch)
        score_state = classification(score)
        elapsed = time.monotonic() - started
        state = "waiting_for_launch" if launch is None else "waiting_for_score"
        ready = False
        if launch is not None and score is not None and launch_state != "in_progress":
            if score_state in ("terminal_success_marker", "terminal_failure"):
                state, ready = "reports_ready_for_independent_verification", True
            elif score_state == "unknown":
                state, ready = "reports_present_need_schema_inspection", True
        record = {
            "observed_utc": stamp(), "elapsed_wait_seconds": elapsed,
            "state": state, "launch": launch_metadata, "score": score_metadata,
            "launch_classification": launch_state, "score_classification": score_state,
            "attempt_inspection_gate_open": launch_metadata["exists"],
            "ready_for_report_inspection": ready,
            "no_numeric_computation_or_attempt_access": True,
            "missing_or_failed_score_is_not_zero": True,
        }
        save(HERE / "wait_status.json", record)
        signature = (state, launch_metadata.get("sha256"), score_metadata.get("sha256"))
        if signature != previous_signature or elapsed - last_heartbeat >= 300:
            with open(HERE / "wait_events.jsonl", "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
            print(json.dumps({"time": record["observed_utc"], "elapsed_wait_seconds": round(elapsed, 1), "state": state, "launch": launch_state, "score": score_state}), flush=True)
            previous_signature = signature
            last_heartbeat = elapsed
        if ready:
            save(HERE / "observed_launch.json", launch)
            save(HERE / "observed_score.json", score)
            break
        if time.monotonic() >= deadline:
            record.update(state="wait_interval_expired_without_complete_reports", ready_for_report_inspection=False)
            save(HERE / "wait_status.json", record)
            print(json.dumps({"state": record["state"], "score_is_unknown_not_zero": True}), flush=True)
            break
        time.sleep(min(arguments.poll_seconds, max(0, deadline - time.monotonic())))


if __name__ == "__main__":
    main()
