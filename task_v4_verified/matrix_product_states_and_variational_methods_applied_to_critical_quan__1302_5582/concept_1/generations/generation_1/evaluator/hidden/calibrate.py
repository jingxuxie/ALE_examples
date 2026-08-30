"""Generation-time calibration only. Targets/cases are never fitted here."""

import os

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "participant/baseline"))

from contractor import load_mps, measure, save_mps
from mps import make_mpo, product_state, project_parity, sweep
from sandbox_runner import run_submission
from hidden.suite import cases
from hidden.teacher import install

install()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def calibrate(resume=False):
    folder = Path(__file__).resolve().parent
    scoring = json.loads((ROOT / "participant/input/scoring.json").read_text())
    destination = folder / "calibration.json"
    frozen = ["participant/input/scoring.json", "evaluator/hidden/cases.json",
              "evaluator/hidden/suite.py", "participant/baseline/solve.py",
              "participant/baseline/mps.py", "participant/baseline/contractor.py",
              "evaluator/trusted_contractor.py", "evaluator/evaluate.py", "evaluator/sandbox_runner.py", "evaluator/worker.py", "evaluator/hidden/calibrate.py", "evaluator/hidden/teacher.py"]
    hashes = {relative: digest(ROOT / relative) for relative in frozen}
    if destination.exists() and not resume:
        raise RuntimeError("calibration exists; use --resume, never silently overwrite")
    report = json.loads(destination.read_text()) if resume and destination.exists() else {
        "version": 1, "kind": "attainable variational references, not exact lower bounds",
        "full_passing_algorithm_known": False, "frozen_hashes": hashes,
        "target_frozen_before_launch": scoring["target"], "cases": {}}
    if report["frozen_hashes"] != hashes:
        raise RuntimeError("frozen source changed since calibration began")
    (folder / "freeze_manifest.json").write_text(json.dumps(hashes, indent=2) + "\n")
    state_folder = folder / "states"
    state_folder.mkdir(exist_ok=True)
    for family, base in cases():
        identity = base["case_id"]
        if identity in report["cases"]:
            continue
        record = {"family": family, "request": base, "baseline": {}, "teacher_runs": []}
        for stage, budget in scoring["stages"].items():
            request = dict(base, budget_seconds=budget["cpu_seconds"], wall_seconds=budget["wall_seconds"])
            scratch = folder / "baseline_runs" / (identity + "-" + stage)
            outcome = run_submission(ROOT / "participant/baseline", ROOT / "participant", scratch, request)
            if not outcome["process_valid"]:
                raise RuntimeError("baseline invalid: " + identity + " " + str(outcome))
            measurement = measure(load_mps(outcome["state_path"], request), request)
            retained = state_folder / (identity + "_baseline_" + stage + ".npz")
            shutil.copyfile(outcome["state_path"], retained)
            record["baseline"][stage] = dict(measurement, cpu_seconds=outcome["cpu_seconds"],
                                              wall_seconds=outcome["wall_seconds"],
                                              state=str(retained.relative_to(ROOT)), sha256=digest(retained))
        best_energy = float("inf")
        best_tensors = None
        bias = {"any": 0.0, "even": 2.0, "odd": -2.0}[base["sector"]]
        starting_tilts = (None, 0.0, 0.45) if base["sector"] != "any" else (None, 0.35, -0.35)
        for starting_tilt in starting_tilts:
            beginning = time.process_time()
            search_seconds = 70.0 if starting_tilt is None else 35.0
            if starting_tilt is None:
                seed_record = min(record["baseline"].values(), key=lambda entry: entry["energy"])
                tensors = load_mps(ROOT / seed_record["state"], base)
            elif base["sector"] != "any" and starting_tilt == 0:
                tensors = product_state(base, odd_site=base["n_sites"] // 2 if base["sector"] == "odd" else None)
            else:
                tensors = project_parity(product_state(base, tilt=starting_tilt), base["sector"])
            mpo = make_mpo(base, parity_bias=bias)
            trajectory = []
            for sweep_index in range(10 if starting_tilt is None else 6):
                tensors = sweep(tensors, mpo, base["bond_cap"], tolerance=2e-9, maxiter=80,
                                deadline=beginning + search_seconds)
                try:
                    measurement = measure(tensors, base)
                    trajectory.append(dict(measurement, sweep=sweep_index + 1,
                                           cpu_seconds=time.process_time() - beginning))
                    if measurement["energy"] < best_energy:
                        best_energy = measurement["energy"]
                        best_tensors = [tensor.copy() for tensor in tensors]
                except ValueError as error:
                    trajectory.append({"sweep": sweep_index + 1, "invalid": str(error)})
                if time.process_time() - beginning >= search_seconds:
                    break
            record["teacher_runs"].append({"tilt": starting_tilt, "cap": base["bond_cap"],
                                            "parity_bias": bias, "eigsh_tolerance": 2e-9,
                                            "maxiter": 80, "trajectory": trajectory,
                                            "cpu_seconds": time.process_time() - beginning})
        if best_tensors is None:
            raise RuntimeError("no valid teacher state for " + identity)
        if min(item["energy"] for item in record["baseline"].values()) - best_energy <= 1e-7 * base["n_sites"]:
            record["best_teacher_energy"] = best_energy
            (folder / (identity + "_insufficient_calibration.json")).write_text(json.dumps(record, indent=2) + "\n")
            raise RuntimeError("teacher did not establish meaningful improvement for " + identity)
        retained = state_folder / (identity + "_reference.npz")
        save_mps(retained, best_tensors)
        record["reference"] = dict(measure(load_mps(retained, base), base),
                                   state=str(retained.relative_to(ROOT)), sha256=digest(retained))
        report["cases"][identity] = record
        destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        print(identity, family, "baseline", record["baseline"]["long"]["energy"],
              "reference", best_energy, flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    calibrate(arguments.resume)
