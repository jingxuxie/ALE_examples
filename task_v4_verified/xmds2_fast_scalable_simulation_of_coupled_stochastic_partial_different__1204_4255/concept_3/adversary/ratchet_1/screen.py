import hashlib
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from field_control import evolve, fidelities, read_json, references, validate_artifact


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    started = time.perf_counter()
    protocol = read_json(ROOT / "evaluator/hidden/protocol.json")
    artifact_path = ROOT / "attempts/v_2/control.json"
    artifact = read_json(artifact_path)
    splines, certificate = validate_artifact(artifact, protocol)
    parameters = list(protocol["uncertainty"])
    cases = []
    for index, bits in enumerate(itertools.product((0, 1), repeat=len(parameters))):
        case = {"id": "corner_%03d" % index, "family": "joint"}
        case.update({name: protocol["uncertainty"][name][bit] for name, bit in zip(parameters, bits)})
        cases.append(case)
    generator = np.random.default_rng(2026082801)
    fractions = np.column_stack([(generator.permutation(64) + generator.random(64)) / 64 for name in parameters])
    for index, row in enumerate(fractions):
        case = {"id": "interior_%03d" % index, "family": "joint"}
        case.update({name: float(protocol["uncertainty"][name][0] + fraction * np.ptp(protocol["uncertainty"][name])) for name, fraction in zip(parameters, row)})
        cases.append(case)
    dump("broad_cases.json", cases)
    freeze = {"date": "2026-08-28", "source_artifact": "attempts/v_2/control.json", "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(), "case_sha256": hashlib.sha256((HERE / "broad_cases.json").read_bytes()).hexdigest(), "sampling": "All 256 Cartesian corners plus 64 independently predeclared Latin-hypercube interiors", "interior_seed": 2026082801, "grid": [64, 32], "dt": 0.02, "case_count": len(cases)}
    dump("screen_input_freeze.json", freeze)
    results = []
    for offset in range(0, len(cases), 16):
        batch = cases[offset:offset + 16]
        initial, target, residual = references(batch, (64, 32), HERE / "reference_cache")
        state, diagnostics = evolve(splines, batch, (64, 32), 0.02, initial)
        scores = fidelities(state, target, (64, 32))
        for index, case in enumerate(batch):
            results.append({"case": case, "fidelity": float(scores[index]), "reference_residual": residual, "diagnostics": {key: float(value[index]) for key, value in diagnostics.items()}})
        dump("broad_screen.json", {"status": "running", "count": len(results), "results": results, "frozen_inputs": freeze})
        print(json.dumps({"completed": len(results), "minimum_fidelity": min(entry["fidelity"] for entry in results), "below_0_98": sum(entry["fidelity"] < 0.98 for entry in results), "seconds": time.perf_counter() - started}), flush=True)
    ranked = sorted(results, key=lambda entry: entry["fidelity"])
    safe = [entry for entry in ranked if entry["diagnostics"]["boundary_mass"] < 4e-9]
    selected = safe[:24]
    selected_ids = {entry["case"]["id"] for entry in selected}
    for entry in sorted(results, key=lambda entry: entry["diagnostics"]["boundary_mass"], reverse=True)[:2]:
        if entry["case"]["id"] not in selected_ids:
            selected.append(entry)
            selected_ids.add(entry["case"]["id"])
    dump("certification_cases.json", [entry["case"] for entry in selected])
    corner_results = [entry for entry in results if entry["case"]["id"].startswith("corner_")]
    effects = {}
    for name in parameters:
        bounds = protocol["uncertainty"][name]
        effects[name] = {}
        for label, endpoint in (("low", bounds[0]), ("high", bounds[1])):
            subset = [entry for entry in corner_results if entry["case"][name] == endpoint]
            effects[name][label] = {"mean_fidelity": float(np.mean([entry["fidelity"] for entry in subset])), "count_below_0_98": sum(entry["fidelity"] < 0.98 for entry in subset)}
    summary = {"status": "complete", "count": len(results), "corner_count": 256, "interior_count": 64, "below_0_98": sum(entry["fidelity"] < 0.98 for entry in results), "corner_below_0_98": sum(entry["fidelity"] < 0.98 for entry in corner_results), "interior_below_0_98": sum(entry["fidelity"] < 0.98 for entry in results if entry["case"]["id"].startswith("interior_")), "screen_boundary_guard_exceedances": sum(entry["diagnostics"]["boundary_mass"] > 1e-8 for entry in results), "minimum_fidelity": min(entry["fidelity"] for entry in results), "maximum_boundary_mass": max(entry["diagnostics"]["boundary_mass"] for entry in results), "runtime_seconds": time.perf_counter() - started, "results": results, "parameter_effects": effects, "frozen_inputs": freeze, "note": "Surrogate results are leads only; staged failures require independent refined audits."}
    dump("broad_screen.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key not in ("results", "parameter_effects", "frozen_inputs")}), flush=True)


if __name__ == "__main__":
    main()
