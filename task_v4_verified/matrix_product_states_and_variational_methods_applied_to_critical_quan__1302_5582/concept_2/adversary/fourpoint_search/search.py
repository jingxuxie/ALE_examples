import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import csv
import hashlib
import itertools
import json
import time

import numpy as np
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg

from fourpoint import ExactTargets, TensorContractions, cauchy_determinant, high_precision_target, write_json, trusted_physics

AUTHORIZED_TENSOR = ROOT.parents[1] / "attempts" / "v_3" / "state.npz"


def validate_ed():
    reports = []
    for size in (6, 8, 10, 12):
        labels = np.arange(2**size, dtype=np.int64)
        magnetizations = sum(1 - 2 * ((labels >> site) & 1) for site in range(size))
        rows = [labels]
        columns = [labels]
        elements = [-magnetizations.astype(float)]
        for site in range(size):
            rows.append(labels)
            columns.append(labels ^ ((1 << site) | (1 << ((site + 1) % size))))
            elements.append(-np.ones(len(labels)))
        hamiltonian = sparse.coo_matrix((np.concatenate(elements), (np.concatenate(rows), np.concatenate(columns))),
                                        shape=(len(labels), len(labels))).tocsr()
        energies, vectors = sparse_linalg.eigsh(hamiltonian, k=1, which="SA", tol=2e-14,
                                               v0=np.ones(len(labels)), maxiter=10000)
        ground = vectors[:, 0]
        residual = np.linalg.norm(hamiltonian @ ground - energies[0] * ground)
        parity = np.prod([1 - 2 * ((labels >> site) & 1) for site in range(size)], axis=0)
        parity_mean = float(np.dot(ground**2, parity))
        worst = None
        maximum = 0.0
        count = 0
        for positions in itertools.combinations(range(size), 4):
            mask = sum(1 << site for site in positions)
            observed = float(np.dot(ground, ground[labels ^ mask]))
            expected = cauchy_determinant(positions, size)
            difference = abs(observed - expected)
            if difference > maximum:
                maximum = difference
                worst = {"positions": list(positions), "spin_ed": observed, "sine_determinant": expected}
            count += 1
        report = {"size": size, "quartets_checked": count, "ground_energy": float(energies[0]),
                  "energy_closed_form": float(-2 / np.sin(np.pi / (2 * size))), "residual": float(residual),
                  "parity_mean": parity_mean, "maximum_absolute_difference": maximum, "worst": worst}
        reports.append(report)
        print(json.dumps({"event": "ed_validation", **report}), flush=True)
        if maximum > 2e-11 or residual > 2e-10 or abs(parity_mean - 1) > 1e-10:
            raise RuntimeError("Independent finite spin ED did not validate the sine determinant")
    exact = ExactTargets(1024)
    generator = np.random.default_rng(137)
    determinant_audit = []
    for unused_sample in range(40):
        lengths = generator.integers(1, 50, size=3)
        positions = (0, int(lengths[0]), int(sum(lengths[:2])), int(sum(lengths)))
        direct = cauchy_determinant(positions)
        stable = exact.evaluate(positions)["raw"]
        determinant_audit.append({"positions": positions, "absolute_difference": abs(direct - stable)})
    if max(record["absolute_difference"] for record in determinant_audit) > 1e-11:
        raise RuntimeError("Stable Cauchy-product formula disagrees with dense determinant")
    result = {"finite_spin_ed": reports, "infinite_dense_determinant_audit": determinant_audit}
    write_json(ROOT / "validation_ed.json", result)
    return result


def scan():
    started = time.monotonic()
    validate_ed()
    tensor = trusted_physics.load_tensor(AUTHORIZED_TENSOR)
    original = trusted_physics.score_metrics(trusted_physics.metrics(tensor))
    write_json(ROOT / "champion_v2_recheck.json", original)
    contractions = TensorContractions(tensor)
    intervals = list(range(1, 13)) + [16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768]
    gaps = list(range(1, 17)) + [24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, 1000]
    contractions.prepare(1024)
    targets = ExactTargets(1024)
    transfer = contractions.even_transfer()
    left_vectors = np.stack([contractions.pack_even(contractions.left_intervals[length]).conj() for length in intervals])
    right_vectors = np.stack([contractions.pack_even(contractions.right_intervals[length]
                                                    - contractions.pairs[length] * contractions.identity)
                              for length in intervals], axis=1)
    records = []
    for gap in range(1, max(gaps) + 1):
        if gap in gaps:
            values = left_vectors @ right_vectors
            if np.max(np.abs(values.imag)) > 1e-9:
                raise RuntimeError("Non-real batched composite covariance")
            for left_index, left in enumerate(intervals):
                for right_index, right in enumerate(intervals):
                    span = left + gap + right
                    if span > 1024:
                        continue
                    positions = (0, left, left + gap, span)
                    exact = targets.evaluate(positions)
                    covariance = float(values[left_index, right_index].real)
                    pair_product = contractions.pairs[left] * contractions.pairs[right]
                    raw = covariance + pair_product
                    pair_errors = [abs(contractions.pairs[positions[end] - positions[start]]
                                       / targets.pair(positions[end] - positions[start]) - 1)
                                   for start, end in itertools.combinations(range(4), 2)]
                    records.append({"left": left, "gap": gap, "right": right, "span": span,
                                    "cross_ratio": exact["cross_ratio"], "exact_raw": exact["raw"],
                                    "observed_raw": raw, "exact_covariance": exact["covariance"],
                                    "observed_covariance": covariance, "raw_relative_error": abs(raw / exact["raw"] - 1),
                                    "covariance_relative_error": abs(covariance / exact["covariance"] - 1),
                                    "normalized_covariance_relative_error": abs((covariance / pair_product)
                                                                                 / exact["connected_ratio"] - 1),
                                    "pair_product_relative_error": abs(pair_product / exact["pair_product"] - 1),
                                    "all_six_pair_max_relative_error": max(pair_errors)})
            print(json.dumps({"event": "gap_completed", "gap": gap, "records": len(records),
                              "elapsed_seconds": time.monotonic() - started}), flush=True)
        right_vectors = transfer @ right_vectors
    with (ROOT / "scan.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    strata = {}
    for maximum_span in (64, 128, 256, 512, 1024):
        for minimum_interval in (1, 4, 16):
            for maximum_gap in (128, 256, 1024):
                eligible = [record for record in records if record["span"] <= maximum_span
                            and min(record["left"], record["right"]) >= minimum_interval
                            and record["gap"] <= maximum_gap and record["exact_covariance"] >= 1e-6]
                if eligible:
                    name = f"span{maximum_span}_intervalmin{minimum_interval}_gapmax{maximum_gap}"
                    strata[name] = {"count": len(eligible),
                                    "maximum_raw": max(eligible, key=lambda record: record["raw_relative_error"]),
                                    "maximum_covariance": max(eligible, key=lambda record: record["covariance_relative_error"]),
                                    "covariance_error_quantiles": np.quantile([record["covariance_relative_error"]
                                                                               for record in eligible], [.5, .9, .99]).tolist()}
    ranked = sorted([record for record in records if min(record["left"], record["right"]) >= 4
                     and record["gap"] <= 256 and record["exact_covariance"] >= 1e-6],
                    key=lambda record: record["covariance_relative_error"], reverse=True)
    selected = []
    for record in ranked:
        if not any((record["left"], record["gap"], record["right"]) ==
                   (other["right"], other["gap"], other["left"]) for other in selected):
            selected.append(record)
        if len(selected) >= 12:
            break
    audit = []
    for record in selected:
        positions = (0, record["left"], record["left"] + record["gap"], record["span"])
        direct = contractions.evaluate(positions)
        precision = high_precision_target(positions)
        audit.append({"positions": positions, "sequential": direct, "high_precision": precision,
                      "batch_vs_sequential_covariance_absolute_difference": abs(direct["covariance"] - record["observed_covariance"]),
                      "target_covariance_relative_difference": abs(float(precision["covariance"]) / record["exact_covariance"] - 1)})
    result = {"authorized_tensor": str(AUTHORIZED_TENSOR),
              "tensor_sha256": hashlib.sha256(AUTHORIZED_TENSOR.read_bytes()).hexdigest(),
              "only_authorized_attempt_tensor_read": True, "no_attempt_source_or_logs_read": True,
              "original_v2_passed": original["passed"], "quartets_scanned": len(records),
              "maximum_span": 1024, "target_covariance_floor_for_ranking": 1e-6,
              "strata": strata, "selected_failures_or_near_misses": selected,
              "independent_numerical_audit": audit, "elapsed_seconds": time.monotonic() - started}
    write_json(ROOT / "search_results.json", result)
    write_json(ROOT / "candidate_quartets.json", {"quartets": [entry["positions"] for entry in audit],
                                                 "note": "Private measured candidates, not frozen task targets"})
    print(json.dumps({"event": "scan_finished", "quartets": len(records), "selected": selected,
                      "elapsed_seconds": result["elapsed_seconds"]}, indent=2), flush=True)


if __name__ == "__main__":
    scan()
