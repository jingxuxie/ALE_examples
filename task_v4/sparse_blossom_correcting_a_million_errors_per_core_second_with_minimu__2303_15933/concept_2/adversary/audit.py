import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def rank(vectors):
    pivots = {}
    for vector in vectors:
        while vector:
            pivot = vector.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = vector
                break
            vector ^= pivots[pivot]
    return len(pivots)


def main():
    started = time.monotonic()
    public = load_module("public_checker_audit", "participant/workspace/check.py")
    oracle = load_module("hidden_checker_audit", "evaluator/hidden/oracle.py")
    witness = oracle.read_artifact(ROOT / "adversary/known_witness.json")
    baseline = oracle.read_artifact(ROOT / "participant/baseline/weak.json")
    assert baseline == {"version": 1, "probabilities": [0.03 + 0.08 * ((17 * edge + 11) % 39) / 38 for edge in range(39)], "syndrome": [1, 6, 11, 16]}
    spec = json.loads((ROOT / "participant/input/spec.json").read_text())
    assert spec["targets"] == {"gap": oracle.GAP_TARGET, "opposite_posterior": oracle.POSTERIOR_TARGET, "syndrome_probability": oracle.MASS_TARGET}
    assert np.max(np.abs(np.array(spec["anchors"]) - np.array(oracle.ANCHORS))) < 1e-15
    graph = json.loads((ROOT / "participant/input/graph.json").read_text())
    masks = [sum(1 << detector for detector in edge["detectors"]) | (edge["logical"] << 20) for edge in graph["edges"]]
    assert masks == oracle.edge_masks()
    assert len(masks) == 39 and len(set(mask & ((1 << 20) - 1) for mask in masks)) == 39
    assert rank(masks) == 21
    assert rank([mask & ((1 << 20) - 1) for mask in masks]) == 20
    degrees = [sum(detector in edge["detectors"] for edge in graph["edges"]) for detector in range(20)]
    assert min(degrees) == 3 and max(degrees) == 4
    for edge in graph["edges"]:
        assert len(edge["detectors"]) in (1, 2)
        if len(edge["detectors"]) == 2:
            first, second = edge["detectors"]
            assert abs(first // 4 - second // 4) + abs(first % 4 - second % 4) == 1
        else:
            assert edge["detectors"][0] // 4 == (0 if edge["boundary"] == "left" else 4)
    toy_masks = [9, 3, 6, 4, 5]
    toy_rates = [0.031, 0.09, 0.12, 0.02, 0.075]
    brute_mass = np.zeros(16)
    brute_cost = np.full(16, np.inf)
    for subset in range(32):
        state, probability, cost = 0, 1.0, 0.0
        for edge, (rate, mask) in enumerate(zip(toy_rates, toy_masks)):
            if (subset >> edge) & 1:
                state ^= mask
                probability *= rate
                cost += math.log((1 - rate) / rate)
            else:
                probability *= 1 - rate
        brute_mass[state] += probability
        brute_cost[state] = min(brute_cost[state], cost)
    toy_mass, toy_cost = oracle.full_state(toy_rates, toy_masks, 3, return_all=True)
    np.testing.assert_allclose(toy_mass, brute_mass, rtol=2e-14, atol=1e-18)
    np.testing.assert_allclose(toy_cost, brute_cost, rtol=2e-14, atol=1e-14)
    full_mass, full_cost = oracle.full_state([1 / (1 + math.e)] * 39, masks, 20, return_all=True)
    assert abs(full_mass.sum() - 1) < 2e-13 and np.min(full_mass) > 0
    assert abs(full_cost[1 << 20] - 6) < 2e-13
    assert full_cost[0] == 0
    del full_mass, full_cost
    rng = np.random.default_rng(451993)
    discrepancies = []
    for scale in (0.95, 1.05):
        rates = rng.uniform(0.02, 0.14, 39)
        syndrome = [0, 5, 10, 15, 16]
        target = sum(1 << detector for detector in syndrome)
        independent = oracle.full_state(rates * scale, masks, 20, target=target)
        frontier = public.frontier(rates, syndrome, scale)
        np.testing.assert_allclose(independent[0], frontier[0], rtol=3e-13, atol=0)
        np.testing.assert_allclose(independent[1], frontier[1], rtol=3e-13, atol=1e-12)
        discrepancies.append({"scale": scale, "mass_relative_error": float(np.max(np.abs(independent[0] / frontier[0] - 1))), "cost_absolute_error": float(np.max(np.abs(independent[1] - frontier[1])))})
    target = sum(1 << detector for detector in witness["syndrome"])
    extended = oracle.full_state(witness["probabilities"], masks, 20, dtype=np.longdouble, target=target)
    ordinary = public.frontier(witness["probabilities"], witness["syndrome"])
    np.testing.assert_allclose(extended[0], ordinary[0], rtol=3e-13, atol=0)
    np.testing.assert_allclose(extended[1], ordinary[1], rtol=3e-13, atol=1e-12)
    public_known = public.check(witness)
    public_baseline = public.check(baseline)
    assert public_known["passed"] and not public_baseline["passed"]
    for name, metrics in (("known", public_known), ("baseline", public_baseline)):
        saved = json.loads((ROOT / f"adversary/{name}_independent_metrics.json").read_text())
        assert saved["passed"] == metrics["passed"]
        for field in ("certified_gap", "certified_opposite_posterior", "certified_syndrome_probability", "core_score"):
            assert math.isclose(saved[field], metrics[field], rel_tol=3e-12, abs_tol=1e-13)
        for first, second in zip(saved["anchors"], metrics["anchors"]):
            np.testing.assert_allclose(first["joint_probabilities"], second["joint_probabilities"], rtol=3e-13, atol=0)
            np.testing.assert_allclose(first["class_costs"], second["class_costs"], rtol=3e-13, atol=1e-12)
    dense = []
    physical = public_known["physical_class"]
    for scale in np.linspace(0.95, 1.05, 1001):
        joint, costs = public.frontier(witness["probabilities"], witness["syndrome"], scale)
        dense.append((float(costs[1 - physical] - costs[physical]), float(joint[1 - physical] / sum(joint)), float(sum(joint))))
    dense_minima = np.min(dense, axis=0)
    assert dense_minima[0] >= public_known["certified_gap"]
    assert dense_minima[1] >= public_known["certified_opposite_posterior"]
    assert dense_minima[2] >= public_known["certified_syndrome_probability"]
    directory = ROOT / "adversary/audit_cases"
    directory.mkdir(exist_ok=True)
    rejected = []
    corruptions = {
        "boolean_version": ("version", True), "float_version": ("version", 1.0),
        "zero_syndrome": ("syndrome", []), "duplicate_detector": ("syndrome", [0, 2, 5, 5, 17]),
        "unsorted": ("syndrome", [2, 0, 5, 17]), "boolean_detector": ("syndrome", [False, 2, 5, 17]),
        "float_detector": ("syndrome", [0.0, 2, 5, 17]), "outside_detector": ("syndrome", [0, 2, 5, 21]),
        "not_spread": ("syndrome", [0, 1, 2]), "uniform_rates": ("probabilities", [0.08] * 39),
        "mean_exceeded": ("probabilities", [0.14] * 20 + [0.06] * 19),
        "wrong_length": ("probabilities", [0.07] * 38), "extra_graph": ("edges", []),
    }
    for label, (field, value) in corruptions.items():
        data = copy.deepcopy(witness)
        data[field] = value
        path = directory / (label + ".json")
        path.write_text(json.dumps(data))
    for label, value in (("nan", float("nan")), ("infinity", float("inf")), ("boolean_rate", True), ("string_rate", "0.02"), ("zero_rate", 0), ("negative_rate", -0.1), ("high_rate", 0.141)):
        data = copy.deepcopy(witness)
        data["probabilities"][0] = value
        (directory / (label + ".json")).write_text(json.dumps(data))
    (directory / "bad_utf8.json").write_bytes(b"\xff\xfe")
    (directory / "duplicate_key.json").write_text('{"version":1,"version":1}')
    (directory / "oversized.json").write_bytes(b" " * 16385)
    (directory / "exponent_overflow.json").write_text(json.dumps(witness).replace("0.02", "1e999", 1))
    (directory / "null.json").write_text("null")
    (directory / "malformed.json").write_text("{")
    (directory / "deeply_nested.json").write_text("[" * 1500 + "0" + "]" * 1500)
    symlink = directory / "symlink.json"
    if not symlink.is_symlink():
        symlink.symlink_to(ROOT / "adversary/known_witness.json")
    fifo = directory / "fifo.json"
    if not fifo.exists():
        os.mkfifo(fifo)
    for path in sorted(directory.iterdir()):
        for reader in (public.load_submission, oracle.read_artifact):
            try:
                reader(path)
            except (ValueError, OSError, OverflowError, RecursionError):
                continue
            raise AssertionError("accepted malicious fixture " + path.name)
        rejected.append(path.name)
    for fixture in ("bad_utf8.json", "nan.json", "boolean_version.json", "fifo.json"):
        process = subprocess.run([sys.executable, "-B", str(ROOT / "evaluator/evaluate.py"), str(directory / fixture)], capture_output=True, text=True, check=True)
        result = json.loads(process.stdout)
        assert not result["valid"] and not result["passed"] and result["core_score"] == 0
        assert "reason" in result and "resources" in result
    public_files = list((ROOT / "participant").rglob("*"))
    assert all(not path.is_symlink() for path in public_files)
    assert not any(path.name in {"search", "search.cpp", "known_witness.json", "prepare.py", "SEARCH_REPORT.md"} for path in public_files)
    report = {"passed": True, "topology": {"detectors": 20, "edges": 39, "logical_distance": 6, "detector_rank": 20, "augmented_rank": 21, "maximum_degree": 4},
              "brute_force_toy_subsets": 32, "full_state_random_crosschecks": discrepancies,
              "all_anchors_crosschecked_artifacts": ["known", "baseline"], "longdouble_crosscheck": True,
              "dense_scales": 1001, "dense_min_gap_posterior_mass": dense_minima.tolist(),
              "malformed_artifacts_rejected_by_both": rejected, "malformed_cli_checks": 4,
              "participant_leakage_filename_check": True, "elapsed_seconds": time.monotonic() - started}
    (ROOT / "adversary/audit_report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
