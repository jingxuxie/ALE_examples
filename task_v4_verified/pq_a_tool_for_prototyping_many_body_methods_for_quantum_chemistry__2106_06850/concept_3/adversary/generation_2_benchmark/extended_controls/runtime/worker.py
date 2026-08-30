"""Fresh-input extended control portfolio; archived algorithm bodies are unchanged."""

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

from assemble import from_reverse
from baseline import solve_case
from fermion import circuit_state, load_cases, read_json, squared_overlap, validate_submission


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--profile")
    arguments = parser.parse_args()
    started = time.perf_counter()
    deadline = started + arguments.seconds - 1.0
    case = load_cases()[0]
    assert not Path("/home").exists() and not Path("/srv").exists() and not Path("/root").exists()
    namespace = {"certificate_free_allowlist": True, "archived_solutions_or_checkpoints_visible": False,
                 "visible_roots": sorted(path.name for path in Path("/").iterdir())}
    Path("namespace.json").write_text(json.dumps(namespace, indent=2) + "\n")
    for name in ("beam", "beam2", "beam3", "model.so"):
        Path(name).symlink_to("/runtime/champion/" + name)
    runpy.run_path("/runtime/champion/export_data.py")
    initial = solve_case(case, 60)
    Path("initial.json").write_text(json.dumps(initial, allow_nan=False) + "\n")
    phases, candidates = [], []
    best_fidelity, best_source = -1.0, None

    def consider(circuit, source):
        nonlocal best_fidelity, best_source
        try:
            payload = {"schema_version": 1, "circuits": [circuit]}
            parsed = validate_submission(payload, (case,))
            fidelity = squared_overlap(case.target, circuit_state(case, parsed[case.case_id]))
        except (ValueError, TypeError, KeyError, IndexError):
            return
        candidates.append({"source": source, "fidelity": fidelity, "gate_count": len(circuit["gates"])})
        if fidelity > best_fidelity:
            best_fidelity, best_source = fidelity, source
            Path("result.json").write_text(json.dumps(payload, allow_nan=False) + "\n")

    def harvest():
        for name in ("initial.json", "refined104.json"):
            if Path(name).is_file():
                try:
                    consider(read_json(name), name)
                except (OSError, ValueError, TypeError):
                    pass
        for suffix in (".reverse.json", ".best.json"):
            path = Path(case.case_id + suffix)
            if path.is_file():
                try:
                    gates = from_reverse(case, read_json(path))
                    consider({"case_id": case.case_id, "gates": [
                        {"annihilate": list(label.annihilate), "create": list(label.create), "theta": float(theta)}
                        for label, theta in gates]}, path.name)
                except (OSError, ValueError, TypeError, KeyError, IndexError):
                    pass

    def save_progress():
        report = {"case_id": case.case_id, "profile": "extended_original_champion_portfolio",
                  "worker_budget_seconds": arguments.seconds, "runtime_seconds": time.perf_counter() - started,
                  "pass": best_fidelity >= 0.999999999, "best_fidelity": best_fidelity, "best_source": best_source,
                  "phases": phases, "candidates": candidates, "namespace": namespace,
                  "seed_policy": "all greedy/beam/bridge/refinement inputs are generated fresh in this run"}
        Path("report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")

    def execute(name, command, allocation):
        available = min(allocation, deadline - time.perf_counter())
        if available < 0.2 or best_fidelity >= 0.999999999:
            return
        phase_started = time.perf_counter()
        with Path(name + ".log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            timed_out = False
            try:
                returncode = process.wait(timeout=available)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
        harvest()
        phases.append({"method": name, "command": command, "allocated_seconds": available,
                       "runtime_seconds": time.perf_counter() - phase_started, "returncode": returncode,
                       "timed_out": timed_out, "best_fidelity_after": best_fidelity})
        save_progress()

    def bridge(name, allocation):
        if best_fidelity >= 0.999999999:
            return
        seed_path = Path(case.case_id + ".best.json")
        if not seed_path.is_file():
            phases.append({"method": name, "skipped": "no fresh beam checkpoint"})
            return
        seed = read_json(seed_path)
        Path("seed104.json").write_text(json.dumps(seed, allow_nan=False) + "\n")
        maximum = min(len(seed["reverse"]), case.max_gates - 3)
        depths = [depth for depth in (10, 9, 11, 8, 12, 7, 6) if depth <= maximum]
        execute(name, [sys.executable, "/runtime/champion/bridges.py", "--depths", ",".join(map(str, depths)), "--limit", "100"], allocation)

    harvest()
    save_progress()
    execute("beam_original_2000", ["./beam", case.case_id, "2000", "60", "0.1"], 90.0)
    bridge("bridge_original_seed", 120.0)
    if best_fidelity < 0.999999999:
        seed_path = case.case_id + ".best.json" if Path(case.case_id + ".best.json").is_file() else "initial.json"
        execute("continuous_fresh_beam_prune", [sys.executable, "/runtime/champion/refine.py", "--seed", seed_path,
                                               "--iterations", "100", "--random", "1"], 120.0)
    execute("beam2_wide", ["./beam2", case.case_id, "10000", "80", "0.1", "1"], 150.0)
    bridge("bridge_wide_seed", max(0.0, deadline - time.perf_counter()))
    harvest()
    save_progress()
    print(json.dumps({"case_id": case.case_id, "fidelity": best_fidelity, "pass": best_fidelity >= 0.999999999,
                      "runtime_seconds": time.perf_counter() - started}), flush=True)


if __name__ == "__main__":
    main()
