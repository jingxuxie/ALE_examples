"""Budgeted orchestration of unchanged archived algorithms inside bubblewrap."""

import argparse
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, "/runtime/champion")
sys.path.insert(0, "/runtime/workspace")

from fermion import (
    Excitation, circuit_state, load_cases, read_json, squared_overlap, validate_submission,
)
from assemble import from_reverse
from baseline import solve_case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--profile", choices=("broad", "deep"), required=True)
    arguments = parser.parse_args()
    started = time.perf_counter()
    deadline = started + arguments.seconds - 1.0
    case = load_cases()[0]
    assert not Path("/srv").exists() and not Path("/home").exists()
    assert not Path("/root").exists() and not Path("/runtime/private").exists()
    namespace = {"certificate_free_allowlist": True, "visible_roots": sorted(path.name for path in Path("/").iterdir()),
                 "input_case_id": case.case_id, "archived_solutions_visible": False}
    Path("namespace.json").write_text(json.dumps(namespace, indent=2) + "\n")
    for name in ("beam3", "model.so"):
        Path(name).symlink_to("/runtime/champion/" + name)
    runpy.run_path("/runtime/champion/export_data.py")
    initial = solve_case(case, 60)
    Path("initial.json").write_text(json.dumps(initial, allow_nan=False) + "\n")
    best_fidelity, best_circuit, best_source = -1.0, None, None
    phases, candidates = [], []

    def consider(circuit, source):
        nonlocal best_fidelity, best_circuit, best_source
        try:
            payload = {"schema_version": 1, "circuits": [circuit]}
            parsed = validate_submission(payload, (case,))
            fidelity = squared_overlap(case.target, circuit_state(case, parsed[case.case_id]))
        except (KeyError, ValueError, TypeError, OverflowError):
            return
        candidates.append({"source": source, "fidelity": fidelity, "gate_count": len(circuit["gates"])})
        if fidelity > best_fidelity:
            best_fidelity, best_circuit, best_source = fidelity, circuit, source
            Path("result.json").write_text(json.dumps(payload, allow_nan=False) + "\n")

    def harvest():
        for name in ("initial.json", "refined104.json", "resume.json"):
            if not Path(name).is_file():
                continue
            try:
                payload = read_json(name)
                if "circuits" in payload:
                    payload = payload["circuits"][0]
                consider(payload, name)
            except (OSError, ValueError, TypeError, KeyError, IndexError):
                pass
        for suffix in (".reverse.json", ".best.json"):
            path = Path(case.case_id + suffix)
            if not path.is_file():
                continue
            try:
                gates = from_reverse(case, read_json(path))
                consider({"case_id": case.case_id, "gates": [
                    {"annihilate": list(label.annihilate), "create": list(label.create), "theta": float(theta)}
                    for label, theta in gates]}, path.name)
            except (OSError, ValueError, TypeError, KeyError, IndexError):
                pass

    def execute(name, command, allocation):
        available = min(allocation, deadline - time.perf_counter())
        if available <= 0.2:
            phases.append({"method": name, "skipped": "budget exhausted"})
            return
        phase_started = time.perf_counter()
        timed_out = False
        with Path(name + ".log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                returncode = process.wait(timeout=available)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
        harvest()
        phases.append({"method": name, "command": command, "allocated_seconds": available,
                       "runtime_seconds": time.perf_counter() - phase_started, "timed_out": timed_out,
                       "returncode": returncode, "best_fidelity_after": best_fidelity})

    harvest()
    if arguments.profile == "broad":
        beam_seconds, continuous_seconds, bridge_seconds = 30.0, 20.0, 10.0
        width, branches, bridge_limit = "256", "40", "5"
    else:
        beam_seconds, continuous_seconds, bridge_seconds = 140.0, 100.0, 60.0
        width, branches, bridge_limit = "1000", "80", "20"
    execute("beam", ["./beam3", case.case_id, width, branches, "0.1", "4"], beam_seconds)
    if best_fidelity < 0.999999999:
        Path("continuous_seed.json").write_text(json.dumps(best_circuit, allow_nan=False) + "\n")
        execute("continuous_refinement", [sys.executable, "/runtime/champion/refine.py", "--seed", "continuous_seed.json",
                                           "--iterations", "100", "--random", "1"], continuous_seconds)
    if best_fidelity < 0.999999999:
        seed_path = next((Path(case.case_id + suffix) for suffix in (".reverse.json", ".best.json") if Path(case.case_id + suffix).is_file()), None)
        if seed_path is not None:
            seed = read_json(seed_path)
            Path("seed104.json").write_text(json.dumps(seed, allow_nan=False) + "\n")
            maximum = min(12, len(seed["reverse"]), case.max_gates - 3)
            depths = [depth for depth in (10, 9, 11, 8, 12, 7, 6, 5, 4, 3, 2, 1, 0) if depth <= maximum]
            execute("bridge", [sys.executable, "/runtime/champion/bridges.py", "--depths", ",".join(map(str, depths)),
                               "--limit", bridge_limit], bridge_seconds)
        else:
            phases.append({"method": "bridge", "skipped": "beam produced no fresh reverse-prefix seed"})
    harvest()
    report = {"case_id": case.case_id, "profile": arguments.profile, "budget_seconds": arguments.seconds,
              "runtime_seconds": time.perf_counter() - started, "best_fidelity": best_fidelity,
              "pass": best_fidelity >= 0.999999999, "best_source": best_source,
              "phases": phases, "candidates": candidates, "namespace": namespace,
              "seed_policy": "fresh public greedy seed and fresh beam output; deep may resume its own broad result"}
    Path("report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"case_id": case.case_id, "profile": arguments.profile, "fidelity": best_fidelity,
                      "pass": report["pass"], "runtime_seconds": report["runtime_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
