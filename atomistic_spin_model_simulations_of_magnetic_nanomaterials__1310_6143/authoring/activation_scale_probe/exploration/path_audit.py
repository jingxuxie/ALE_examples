import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parents[2] / "pilots/activation/attempt/solve.py"
COPY = ROOT / "old_solver.py"
EXPECTED_HASH = "252500c16f8aa286173b42139f0cc1686627788dcde93ad46f081b89771e4656"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != EXPECTED_HASH:
    raise RuntimeError("immutable solver changed")
if not COPY.exists():
    shutil.copyfile(SOURCE, COPY)
if hashlib.sha256(COPY.read_bytes()).hexdigest() != EXPECTED_HASH:
    raise RuntimeError("private snapshot changed")
specification = importlib.util.spec_from_file_location("old_solver", COPY)
old = importlib.util.module_from_spec(specification)
specification.loader.exec_module(old)


class ReachedEigenFollowing(Exception):
    pass


def audit(directory):
    case = json.loads((directory / "case.json").read_text())
    with np.load(directory / "reference.npz", allow_pickle=False) as archive:
        reference_barrier = float(archive["barrier_meV"])
    model = old.SpinModel(case)
    planar = old.PlanarModel(model, model.plane())
    start_energy = float(planar.energy_gradient(planar.start)[0])
    records = []
    original_follow = old.follow_saddle
    for direction in [0, 1, -1]:
        for images in ([45] if direction == 0 else [45, 65, 97, 129, 257]):
            path = old.initial_path(planar, direction, images=images)
            energy = planar.energy_gradient(path)[0] - start_energy
            trace = []
            def stop_before_eigen(model, initial, maxiter=160):
                trace.append({"energy_above_start_meV": float(model.energy_gradient(initial)[0]) - start_energy, "maxiter": maxiter})
                raise ReachedEigenFollowing()
            old.follow_saddle = stop_before_eigen
            started = time.perf_counter()
            try:
                candidates, final_path = old.string_search(planar, path.copy(), time.monotonic() + 90)
                final_energy = planar.energy_gradient(final_path)[0] - start_energy
                status = "returned_no_candidate_before_any_eigensolve" if not candidates else "unexpected_candidate"
                final_peak = int(np.argmax(final_energy))
                final_interior_max = float(np.max(final_energy[1:-1]))
            except ReachedEigenFollowing:
                status = "reached_eigenvector_following"
                final_peak = None
                final_interior_max = None
            finally:
                old.follow_saddle = original_follow
            record = {"direction": direction, "images": images, "initial_peak_index": int(np.argmax(energy)),
                      "initial_max_interior_above_A_meV": float(np.max(energy[1:-1])), "initial_first_image_above_A_meV": float(energy[1]),
                      "native_reference_barrier_meV": reference_barrier, "status": status, "final_peak_index": final_peak,
                      "final_max_interior_above_A_meV": final_interior_max, "follow_entry_trace": trace, "seconds": time.perf_counter() - started,
                      "eigenvalue_or_eigenvector_computations": 0}
            records.append(record)
            print(case["case_id"], direction, images, status, record["initial_max_interior_above_A_meV"], flush=True)
            if images != 45 and status == "reached_eigenvector_following":
                break
    result = {"case_id": case["case_id"], "n_spins": case["n_spins"], "immutable_source_sha256": EXPECTED_HASH,
              "method": "Unchanged initial_path and string_search; an observer stops immediately before the first follow_saddle call. Endpoint exits are real returns, not forced stops.",
              "records": records}
    destination = ROOT / "path_audits" / (case["case_id"] + ".json")
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directories", nargs="+", type=Path)
    for directory in parser.parse_args().directories:
        audit(directory.resolve())
