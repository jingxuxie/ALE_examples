import argparse
import json
import time
from pathlib import Path

import numpy as np

from harness import ROOT, diagnostics, load_mps, measure, sha256, write_json
import optimizer
from refine import infer_charges, refine
import teacher_engine
from trusted_contractor import save_mps


def balanced_split(vector, shape, cap, direction, left_charges, right_charges):
    matrix = vector.reshape(shape[0] * shape[1], shape[2] * shape[3])
    row_charge = (left_charges[:, None] ^ (np.arange(shape[1])[None, :] % 2)).ravel()
    column_charge = ((np.arange(shape[2])[:, None] % 2) ^ right_charges[None, :]).ravel()
    left_vectors = np.zeros((matrix.shape[0], cap))
    right_vectors = np.zeros((cap, matrix.shape[1]))
    values = np.zeros(cap)
    new_charge = np.repeat([0, 1], cap // 2)
    for charge in (0, 1):
        rows = np.flatnonzero(row_charge == charge)
        columns = np.flatnonzero(column_charge == charge)
        block_left, block_values, block_right = np.linalg.svd(matrix[np.ix_(rows, columns)], full_matrices=False)
        count = cap // 2
        assert len(block_values) >= count
        selected = np.arange(charge * count, (charge + 1) * count)
        left_vectors[np.ix_(rows, selected)] = block_left[:, :count]
        right_vectors[np.ix_(selected, columns)] = block_right[:count]
        values[selected] = block_values[:count]
    values /= np.linalg.norm(values)
    if direction == "right":
        return (left_vectors.reshape(shape[0], shape[1], cap),
                (values[:, None] * right_vectors).reshape(cap, shape[2], shape[3]), new_charge)
    return ((left_vectors * values).reshape(shape[0], shape[1], cap),
            right_vectors.reshape(cap, shape[2], shape[3]), new_charge)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--cuts", nargs="+", type=int, default=[3, 4])
    parser.add_argument("--budget", type=float, default=60)
    args = parser.parse_args()
    request_path = Path(args.request)
    request = json.loads(request_path.read_text())
    seed_path = Path(args.seed)
    tensors = load_mps(seed_path, request)
    charges = infer_charges(tensors, request)
    started = time.process_time()
    wall_started = time.monotonic()
    trajectory = []
    original_split = teacher_engine.split_pair
    for cut in args.cuts:
        tensors, charges = teacher_engine.right_canonical(tensors, charges)
        mpo = teacher_engine.make_mpo(request)
        rights = [None] * (len(tensors) + 1)
        rights[-1] = np.ones((1, 1, 1))
        for site in range(len(tensors) - 1, -1, -1):
            rights[site] = teacher_engine.right_step(rights[site + 1], tensors[site], mpo[site])
        left_environment = np.ones((1, 1, 1))
        for site in range(cut - 1):
            left, dimension, right = tensors[site].shape
            row_charge = (charges[site][:, None] ^ (np.arange(dimension)[None, :] % 2)).ravel()
            rotation, values, following, new_charge = optimizer.factor(
                tensors[site].reshape(left * dimension, right), row_charge, charges[site + 1], right)
            tensors[site] = rotation.reshape(left, dimension, len(values))
            tensors[site + 1] = np.tensordot(values[:, None] * following, tensors[site + 1], axes=(1, 0))
            charges[site + 1] = new_charge
            left_environment = teacher_engine.left_step(left_environment, tensors[site], mpo[site])
        site = cut - 1
        teacher_engine.split_pair = balanced_split
        try:
            tensors[site], tensors[site + 1], charges[cut] = teacher_engine.optimize_pair(
                tensors[site], tensors[site + 1], left_environment, rights[site + 2],
                mpo[site], mpo[site + 1], request["bond_cap"], "right", charges[site],
                charges[site + 2], 2e-11, started + args.budget)
        finally:
            teacher_engine.split_pair = original_split
        trajectory.append({"phase": "force_balanced_cut_" + str(cut),
                           **measure(tensors, request), "cpu_seconds": time.process_time() - started})
    directory = Path(args.output).parent
    directory.mkdir(parents=True, exist_ok=True)
    save_mps(directory / "reallocated_seed.npz", tensors)

    def checkpoint(state, local_trajectory):
        save_mps(directory / "state.npz", state)
        print(json.dumps({"phase": local_trajectory[-1]["phase"], **measure(state, request)}), flush=True)

    tensors, polished = refine(tensors, request, max(1.0, args.budget - time.process_time() + started), 0, checkpoint)
    save_mps(directory / "state.npz", tensors)
    checked = measure(load_mps(directory / "state.npz", request), request)
    result = {"case_id": request["case_id"], "solver": "reallocation_teacher", "budget_seconds": args.budget,
              "returncode": 0, "physical_validity": True, "measurement": checked,
              "cpu_seconds": time.process_time() - started,
              "wall_seconds": time.monotonic() - wall_started,
              "timing_mode": "in-process reallocation and refinement, imports excluded",
              "resource_observation_valid": False, "ground_energy_certified": False,
              "state_sha256": sha256(directory / "state.npz"),
              "state_bytes": (directory / "state.npz").stat().st_size,
              "request_sha256": sha256(request_path), "seed_sha256": sha256(seed_path),
              "forced_balanced_cuts": args.cuts, "trajectory": trajectory + polished,
              "diagnostics": diagnostics(tensors, request, checked["energy"])}
    write_json(directory / "teacher_internal.json", result)
    print(json.dumps({"event": "reallocated_final", **checked}), flush=True)


if __name__ == "__main__":
    main()
