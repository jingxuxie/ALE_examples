import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import tempfile
import time


for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from kernel import WitnessError, parse_json, read_json, score_payload


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "authoring"))
from isolation import bubblewrap_command, clean_environment, run_bounded, validate_pair


MEMORY_BYTES = 4 * 1024 ** 3


def deadline_expired(signum, frame):
    raise TimeoutError("300-second evaluator wall limit exceeded")


def failure(message, process=None):
    report = {
        "mode": "C", "core_score": 0.0, "valid": False,
        "target_met": False, "success": False, "error": str(message)[:500],
        "cases": [],
    }
    if process is not None:
        report["process"] = process
    return report


def load_frozen_input(public=False):
    name = "demo.json" if public else "targets.json"
    contents = (ROOT / "participant/input" / name).read_bytes()
    manifest = read_json(ROOT / "evaluator/hidden/manifest.json")
    digest = hashlib.sha256(contents).hexdigest()
    expected = manifest["demo_sha256" if public else "targets_sha256"]
    if digest != expected:
        raise WitnessError("frozen public input hash mismatch")
    return parse_json(contents), contents, digest


def launch(submission, contents, seconds=290):
    attempts = ROOT / "attempts"
    attempts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".evaluation-", dir=attempts) as temporary:
        temporary = Path(temporary)
        work = temporary / "output"
        work.mkdir()
        submission, work = validate_pair(submission, work)
        if not (submission / "solution.py").is_file():
            raise WitnessError("submission must contain solution.py")
        public_input = temporary / "input.json"
        public_input.write_bytes(contents)
        command = bubblewrap_command(
            [(submission, "/submission", False), (public_input, "/input.json", False),
             (work, "/output", True)],
            "/submission",
            ["/usr/bin/taskset", "-c", str(min(os.sched_getaffinity(0))),
             "/usr/bin/prlimit", "--as=" + str(MEMORY_BYTES), "--cpu=290",
             "--fsize=1048576", "--nofile=128", "--", "/usr/bin/python3", "-B",
             "/submission/solution.py", "/input.json", "/output/witness.json"],
            network=False,
        )
        log = temporary / "process.log"
        process = run_bounded(command, clean_environment(), seconds, log_path=log)
        process["isolation"] = "shared fail-closed bubblewrap helper; no private mounts"
        process["memory_limit_bytes"] = MEMORY_BYTES
        if process["returncode"] != 0 or process["remaining_owned_descendants"]:
            with log.open("rb") as handle:
                handle.seek(max(0, log.stat().st_size - 4000))
                process["log_tail"] = handle.read(4000).decode("utf-8", errors="replace")
            return None, process
        try:
            payload = read_json(work / "witness.json")
        except (OSError, WitnessError) as error:
            process["output_error"] = str(error)[:300]
            return None, process
        return payload, process


def main():
    parser = argparse.ArgumentParser(description="Check compact full-unitary circuit witnesses")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--submission", type=Path)
    source.add_argument("--witness", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public", action="store_true", help="check the unscored two-qubit demo")
    arguments = parser.parse_args()
    started = time.monotonic()
    signal.signal(signal.SIGALRM, deadline_expired)
    signal.alarm(300)
    current_hard = resource.getrlimit(resource.RLIMIT_AS)[1]
    memory_cap = MEMORY_BYTES if current_hard == resource.RLIM_INFINITY else min(MEMORY_BYTES, current_hard)
    resource.setrlimit(resource.RLIMIT_AS, (memory_cap, memory_cap))
    digest = None
    try:
        specification, contents, digest = load_frozen_input(arguments.public)
        if arguments.witness is not None:
            payload = read_json(arguments.witness)
            process = {"execution": "static witness; no submission code executed"}
        else:
            seconds = max(1, min(290, 295 - (time.monotonic() - started)))
            payload, process = launch(arguments.submission, contents, seconds=seconds)
        if payload is None:
            report = failure("submission failed or did not produce a valid JSON output file", process)
        else:
            report = score_payload(specification, payload)
            report["process"] = process
    except (OSError, ValueError, TypeError, KeyError, TimeoutError, RecursionError) as error:
        report = failure(error)
    finally:
        signal.alarm(0)
    report.update(
        suite="demo" if arguments.public else "scored",
        input_sha256=digest,
        wall_seconds=round(time.monotonic() - started, 6),
        evaluation_limit_seconds=300,
        memory_limit_bytes=MEMORY_BYTES,
    )
    report["passed"] = report.get("target_met", False)
    report["worst_family_score"] = min((case.get("score", 0.0) for case in report["cases"]), default=0.0)
    report["runtime_seconds"] = report["wall_seconds"]
    report["resource_score"] = float(report["wall_seconds"] <= 300 and not report.get("process", {}).get("timed_out", False))
    report["reason"] = "all operator witnesses pass" if report["passed"] else report.get("error", "at least one operator witness misses the fixed threshold")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({name: report[name] for name in ("core_score", "valid", "target_met")}, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
