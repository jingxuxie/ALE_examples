import sys

sys.dont_write_bytecode = True

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parents[1]


def load(name, relative):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main():
    started = time.monotonic()
    public = load("audit_public", "participant/workspace/check.py")
    oracle = load("audit_hidden", "evaluator/hidden/oracle.py")
    original_manifest = json.loads((ORIGINAL / "evaluator/hidden/frozen_manifest.json").read_text())
    for relative, expected in original_manifest["files_sha256"].items():
        assert hashlib.sha256((ORIGINAL / relative).read_bytes()).hexdigest() == expected
    assert (ROOT / "participant/baseline/champion.json").read_bytes() == (ORIGINAL / "champions/generation_1/witness.json").read_bytes()
    assert hashlib.sha256((ROOT / "adversary/known_witness.json").read_bytes()).hexdigest() == original_manifest["known_private_witness_sha256"]
    graph = json.loads((ROOT / "participant/input/graph.json").read_text())
    masks = [sum(1 << detector for detector in edge["detectors"]) | (edge["logical"] << 20) for edge in graph["edges"]]
    assert masks == oracle.edge_masks()
    assert len(set(mask & ((1 << 20) - 1) for mask in masks)) == 39
    maximum_mass_error, maximum_cost_error = 0.0, 0.0
    independent_reports = {}
    for label, relative in (("known", "adversary/known_witness.json"), ("baseline", "participant/baseline/champion.json")):
        data = oracle.read_artifact(ROOT / relative)
        fast = json.loads((ROOT / f"adversary/{label}_public_metrics.json").read_text())
        exact = json.loads((ROOT / f"adversary/{label}_independent_metrics.json").read_text())
        independent_reports[label] = exact
        assert fast["passed"] == exact["passed"] == (label == "known")
        assert len(exact["groups"]) == 45 and exact["inference_points"] == 2265
        assert abs(fast["core_score"] - exact["core_score"]) < 3e-12
        public_groups, private_groups = public.calibrations(data), oracle.schedule(data["probabilities"])
        assert [group["id"] for group in public_groups] == [group["id"] for group in private_groups]
        for public_group, private_group in zip(public_groups, private_groups):
            np.testing.assert_allclose(public_group["probabilities"], private_group["rates"], rtol=1e-14, atol=1e-16)
            assert abs(public_group["derivative_bound"] - private_group["derivative"]) < 1e-12
            if public_group["family"] != "global":
                totals = private_group["rates"].sum(axis=1)
                np.testing.assert_allclose(totals, public_group["background_scale"] * math.fsum(data["probabilities"]), rtol=3e-14, atol=1e-14)
        for first, second in zip(fast["groups"], exact["groups"]):
            assert first["id"] == second["id"] and first["failures"] == second["failures"]
            for first_anchor, second_anchor in zip(first["anchors"], second["anchors"]):
                first_mass, second_mass = np.array(first_anchor["joint_probabilities"]), np.array(second_anchor["joint_probabilities"])
                first_cost, second_cost = np.array(first_anchor["class_costs"]), np.array(second_anchor["class_costs"])
                np.testing.assert_allclose(first_mass, second_mass, rtol=3e-12, atol=0)
                np.testing.assert_allclose(first_cost, second_cost, rtol=3e-12, atol=1e-12)
                maximum_mass_error = max(maximum_mass_error, float(np.max(np.abs(first_mass / second_mass - 1))))
                maximum_cost_error = max(maximum_cost_error, float(np.max(np.abs(first_cost - second_cost))))
        physical = exact["physical_class"]
        for group, certificate in zip(public_groups[1:], exact["groups"][1:]):
            for amplitude in (-0.049, -0.013, 0.007, 0.049):
                rates = group["background_scale"] * np.array(data["probabilities"]) * (1 + amplitude * np.array(group["levels"]))
                joint, costs = public.frontier(rates, data["syndrome"])
                assert costs[1 - physical] - costs[physical] + 1e-12 >= certificate["certified_gap"]
                assert joint[1 - physical] / sum(joint) + 1e-12 >= certificate["certified_opposite_posterior"]
                assert sum(joint) + 1e-15 >= certificate["certified_syndrome_probability"]
    old_score = json.loads((ROOT / "participant/baseline/generation_1_metrics.json").read_text())["core_score"]
    assert abs(independent_reports["baseline"]["nominal_score"] - old_score) < 3e-12
    toy_masks, toy_rates = [9, 3, 6, 4, 5], [0.031, 0.09, 0.12, 0.02, 0.075]
    brute_mass, brute_cost = np.zeros(16), np.full(16, np.inf)
    for subset in range(32):
        state, mass, cost = 0, 1.0, 0.0
        for edge, (mask, rate) in enumerate(zip(toy_masks, toy_rates)):
            present = (subset >> edge) & 1
            mass *= rate if present else 1 - rate
            if present:
                state ^= mask
                cost += math.log((1 - rate) / rate)
        brute_mass[state] += mass
        brute_cost[state] = min(brute_cost[state], cost)
    for target in range(8):
        native = oracle.native_many([toy_rates], toy_masks, 3, target)[0]
        np.testing.assert_allclose(native[:2], brute_mass[[target, target + 8]], rtol=3e-13, atol=0)
        np.testing.assert_allclose(native[2:], brute_cost[[target, target + 8]], rtol=3e-13, atol=1e-13)
    assert abs(sum(brute_mass) - 1) < 1e-14
    for target in range(8):
        small = oracle.native_many([toy_rates[:2]], toy_masks[:2], 3, target)[0]
        reference = oracle.full_state(toy_rates[:2], toy_masks[:2], 3, target=target)
        np.testing.assert_allclose(small[:2], reference[0], rtol=3e-13, atol=0)
        np.testing.assert_allclose(small[2:], reference[1], rtol=3e-13, atol=1e-13)
    distance = oracle.native_many([[1 / (1 + math.e)] * 39], masks, 20, 0)[0]
    assert abs(distance[3] - 6) < 1e-12 and distance[2] == 0
    champion = oracle.read_artifact(ROOT / "participant/baseline/champion.json")
    target = sum(1 << detector for detector in champion["syndrome"])
    exact = independent_reports["baseline"]
    group_index = min(range(1, 45), key=lambda index: min(anchor["opposite_posterior"] for anchor in exact["groups"][index]["anchors"]))
    parameter_index = min(range(51), key=lambda index: exact["groups"][group_index]["anchors"][index]["opposite_posterior"])
    rates = oracle.schedule(champion["probabilities"])[group_index]["rates"][parameter_index]
    slow = oracle.full_state(rates, masks, 20, target=target)
    saved = exact["groups"][group_index]["anchors"][parameter_index]
    np.testing.assert_allclose(slow[0], saved["joint_probabilities"], rtol=3e-12, atol=0)
    np.testing.assert_allclose(slow[1], saved["class_costs"], rtol=3e-12, atol=1e-12)
    permutation = np.random.default_rng(238).permutation(39)
    reordered = oracle.native_many([rates[permutation]], np.array(masks)[permutation], 20, target)[0]
    np.testing.assert_allclose(reordered[:2], slow[0], rtol=3e-12, atol=0)
    np.testing.assert_allclose(reordered[2:], slow[1], rtol=3e-12, atol=1e-12)
    rejected = []
    for path in sorted((ORIGINAL / "adversary/audit_cases").iterdir()):
        for reader in (public.load_submission, oracle.read_artifact):
            try:
                reader(path)
            except (ValueError, OSError, OverflowError, RecursionError):
                continue
            raise AssertionError("malformed artifact accepted: " + path.name)
        rejected.append(path.name)
    for name in ("bad_utf8.json", "boolean_version.json", "nan.json", "fifo.json"):
        command = [sys.executable, "-B", str(ROOT / "evaluator/evaluate.py"), str(ORIGINAL / "adversary/audit_cases" / name), "--summary-only"]
        result = json.loads(subprocess.run(command, capture_output=True, text=True, check=True).stdout)
        assert not result["valid"] and not result["passed"] and result["core_score"] == 0
    assert all(not path.is_symlink() for path in (ROOT / "participant").rglob("*"))
    assert not any(path.name in {"known_witness.json", "search.cpp", "calibrate.py", "full_state.so"} for path in (ROOT / "participant").rglob("*"))
    report = {"passed": True, "native_frontier_points_compared": 4530, "calibration_groups_per_artifact": 45,
              "maximum_mass_relative_error": maximum_mass_error, "maximum_cost_absolute_error": maximum_cost_error,
              "off_anchor_checks": 352, "brute_force_toy_subsets": 32, "rank_deficient_native_targets": 8,
              "slow_generic_full_state_check": True, "native_edge_order_invariance": True,
              "logical_distance": 6, "noise_budget_preservation": True, "original_nominal_contract_retained": True,
              "original_frozen_assets_unchanged": True, "actual_promoted_champion_baseline": True,
              "private_known_witness_not_exposed": True, "malformed_artifacts_rejected": rejected,
              "malformed_cli_checks": 4, "elapsed_seconds": time.monotonic() - started}
    (ROOT / "adversary/audit_report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
