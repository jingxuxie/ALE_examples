from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

from author import ROOT, evaluate, load_model
import numpy as np


def relative(actual, expected):
    return float(np.max(np.abs(actual - expected))) / max(1., float(np.max(np.abs(expected))))


def check_references(refine=False):
    results = {}
    for folder in (ROOT / "private" / "reference" / "cases", ROOT / "private" / "challenge_pool"):
        manifest = json.loads((folder / "manifest.json").read_text())
        for record in manifest["cases"]:
            with np.load(folder / record["expected"], allow_pickle=False) as archive:
                assert all(np.isfinite(archive[key]).all() for key in archive.files)
            assert record["reference_seconds"] > 0
            assert record["reference_metrics"]["cores"] == [40, 41, 42, 43]
    results["finite_reference_cases"] = 18
    folder = ROOT / "private" / "reference" / "cases"
    request = dict(np.load(folder / "native32.input.npz", allow_pickle=False))
    expected = dict(np.load(folder / "native32.expected.npz", allow_pickle=False))
    spec = importlib.util.spec_from_file_location("dense_starter", ROOT / "participant" / "workspace" / "solve.py")
    dense = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dense)
    started = time.perf_counter()
    output = dense.solve(request)
    results["dense_native32_compute_seconds"] = time.perf_counter() - started
    results["dense_native32_errors"] = {key: relative(output[key], expected[key]) for key in expected}
    assert max(results["dense_native32_errors"].values()) < 1e-10
    transition = dict(np.load(ROOT / "private" / "challenge_pool" / "coupling_transition.expected.npz", allow_pickle=False))
    results["conditional_center_crossing_fd"] = {}
    for key in ("velocity", "divergence"):
        derivative = (transition[key][1] - transition[key][0]) / 2e-5
        target = np.mean(transition["dlam_" + key], axis=0)
        error = relative(derivative, target)
        results["conditional_center_crossing_fd"][key] = error
        assert error < 1e-7
    constant = dict(request, phi=np.full((1, 32, 32), .21), logp=np.array([.7]))
    params, orbits = load_model("single-L32")
    sample, _ = evaluate(constant)
    changed = dict(constant, phi=constant["phi"].copy())
    changed["phi"][0, 3, 7] += 1e-5
    upper, _ = evaluate(changed)
    changed["phi"][0, 3, 7] -= 2e-5
    lower, _ = evaluate(changed)
    diagonal = (upper["velocity"][0, 3, 7] - lower["velocity"][0, 3, 7]) / 2e-5
    results["constant_field_trace_fd"] = relative(np.array([diagonal * 1024]), sample["divergence"])
    assert results["constant_field_trace_fd"] < 1e-7
    lifted = dict(constant, phi=np.tile(constant["phi"], (1, 2, 2)), profile=np.array("transfer"))
    transferred, _ = evaluate(lifted)
    results["transfer_constant_velocity"] = relative(transferred["velocity"], np.tile(sample["velocity"], (1, 2, 2)))
    results["transfer_trace_volume"] = relative(transferred["divergence"], sample["divergence"] * 4)
    assert results["transfer_constant_velocity"] < 1e-10
    assert results["transfer_trace_volume"] < 1e-10
    odd_folder = ROOT / "private" / "challenge_pool"
    impulse = dict(np.load(odd_folder / "odd_transfer33.expected.npz", allow_pickle=False))
    target = np.roll(np.rot90(impulse["velocity"][0]), (4, -2), axis=(0, 1))
    results["transfer_impulse_equivariance"] = relative(impulse["velocity"][1], target)
    assert results["transfer_impulse_equivariance"] < 1e-10
    if refine:
        for name in ("forward32", "forward64", "conditional_reverse64"):
            request = dict(np.load(folder / (name + ".input.npz"), allow_pickle=False))
            expected = dict(np.load(folder / (name + ".expected.npz"), allow_pickle=False))
            output, timing = evaluate(request, steps=200)
            errors = {key: relative(output[key] - (request["logp"] if key == "logp" else 0),
                                    expected[key] - (request["logp"] if key == "logp" else 0)) for key in expected}
            results[name + "_100_vs_200"] = dict(errors=errors, timing=timing)
            assert max(errors.values()) < 2e-5
            if name == "forward32":
                back = dict(request, operation=np.array("reverse"), phi=expected["phi"], logp=expected["logp"])
                reversed_output, _ = evaluate(back)
                errors = {key: relative(reversed_output[key], request[key]) for key in ("phi", "logp")}
                results["native32_round_trip"] = errors
                assert max(errors.values()) < 2e-5
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refine", action="store_true")
    parser.add_argument("--report", type=Path, default=ROOT / "attempt" / "validation.json")
    args = parser.parse_args()
    result = check_references(args.refine)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
