import copy
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np
from scipy.linalg import expm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "participant" / "baseline"))
from evaluate import load_configurations
from fleet import load_fleet, objective
from isolation import SubmissionFailure, run_isolated
from physics import QuantumCase
from scoring import InvalidPolicy, exact_score, strict_json, validate
from build_data import case_configuration, write_json


def physics_checks():
    case = case_configuration(np.random.RandomState(531), "drifting_priors", "small", 6)
    case["entropy_sites"] = [0, 1, 2]
    model = QuantumCase(case)
    size = 1 << case["L"]
    identity = np.eye(2)
    raising = np.array([[0, 0], [1, 0]], dtype=complex)
    lowering = raising.T
    spinz = np.diag([-0.5, 0.5])

    def embed(site, local):
        operator = np.ones((1, 1), dtype=complex)
        for position in reversed(range(case["L"])):
            operator = np.kron(operator, local if position == site else identity)
        return operator

    plus = [embed(site, raising) for site in range(case["L"])]
    minus = [embed(site, lowering) for site in range(case["L"])]
    diagonal = [embed(site, spinz) for site in range(case["L"])]
    static_full = np.zeros((size, size), dtype=complex)
    drive_full = np.zeros_like(static_full)
    regime = case["regimes"][0]
    for site in range(case["L"]):
        adjacent = (site + 1) % case["L"]
        distant = (site + 2) % case["L"]
        nearest = case["J1xy"] / 2 * (plus[site] @ minus[adjacent] + minus[site] @ plus[adjacent])
        nearest += case["J1z"] * diagonal[site] @ diagonal[adjacent]
        next_nearest = case["J2xy"] / 2 * (plus[site] @ minus[distant] + minus[site] @ plus[distant])
        next_nearest += case["J2z"] * diagonal[site] @ diagonal[distant]
        static_full += (1 + (-1) ** site * case["delta"] * regime["delta_multiplier"]) * nearest
        static_full += regime["j2_multiplier"] * next_nearest
        drive_full += (-1) ** site * case["drive_amplitude"] * regime["drive_multiplier"] * nearest
    static, drive, frequency = model.parts[0]
    subset = np.ix_(model.states, model.states)
    hamiltonian_error = max(np.max(np.abs(static.toarray() - static_full[subset])),
                            np.max(np.abs(drive.toarray() - drive_full[subset])))
    assert hamiltonian_error < 2e-14
    projector_error = 0.0
    commutator_error = 0.0
    for sensor in case["sensors"]:
        projectors = [model.project(np.eye(model.dimension), sensor, sector)
                      for sector in range(sensor["order"])]
        projector_error = max(projector_error, float(np.max(np.abs(sum(projectors) - np.eye(model.dimension)))))
        for projector in projectors:
            projector_error = max(projector_error, float(np.max(np.abs(projector @ projector - projector))),
                                  float(np.max(np.abs(projector - projector.conj().T))))
            commutator_error = max(commutator_error, float(np.max(np.abs(static @ projector - projector @ static))),
                                   float(np.max(np.abs(drive @ projector - projector @ drive))))
    assert projector_error < 2e-14 and commutator_error < 2e-14
    assert abs(model.loss(model.initial) - (1 + case["imbalance_weight"]
               * (float(np.abs(model.initial) ** 2 @ model.stagger) * 2 / model.length) ** 2)) < 1e-13
    maximally_entangled = np.zeros(model.dimension, dtype=complex)
    for mask in range(8):
        occupied = [pair if (mask >> pair) & 1 else pair + 3 for pair in range(3)]
        maximally_entangled[model.index[sum(1 << site for site in occupied)]] = 1 / np.sqrt(8)
    assert abs(model.loss(maximally_entangled)) < 1e-13
    midpoint = model.initial.copy()
    stop = 0.7
    steps = 600
    for step in range(steps):
        moment = (step + 0.5) * stop / steps
        hamiltonian = static_full[subset] + np.sin(frequency * moment) * drive_full[subset]
        midpoint = expm(-1j * hamiltonian * stop / steps) @ midpoint
    reference = model.evolve(model.initial, 0, stop, 0)
    evolution_error = float(np.max(np.abs(midpoint - reference)))
    assert evolution_error < 2e-6
    catalog_model = QuantumCase(case, propagators=True)
    catalog = catalog_model.catalog()
    route_error = 0.0
    normalization_error = 0.0
    sensor_indices = {sensor["sensor_id"]: index for index, sensor in enumerate(case["sensors"])}
    for first_id, sectors in case["calibration_test"]["allowed_second_sensor_ids_by_sector"].items():
        total = np.zeros(len(case["regimes"]))
        for sector, seconds in enumerate(sectors):
            first_probability = None
            for second_id in seconds:
                probability, numerator = model.route(first_id, sector, second_id)
                name = "route_{}_{}_{}".format(sensor_indices[first_id], sector, sensor_indices[second_id])
                route_error = max(route_error, float(np.max(np.abs(numerator - catalog[name]))))
                if first_probability is not None:
                    normalization_error = max(normalization_error, float(np.max(np.abs(first_probability - probability.sum(axis=1)))))
                first_probability = probability.sum(axis=1)
            total += first_probability
        normalization_error = max(normalization_error, float(np.max(np.abs(total - 1))))
    assert route_error < 2e-7 and normalization_error < 2e-8
    return {"full_hilbert_hamiltonian_error": float(hamiltonian_error),
            "projector_error": projector_error, "symmetry_commutator_error": commutator_error,
            "independent_midpoint_evolution_error": evolution_error,
            "direct_vs_catalog_route_error": route_error, "born_normalization_error": normalization_error,
            "analytic_entropy_checks": 2}


def corruption_checks(manifest, configurations, policy, input_directory):
    checks = []

    def rejected(name, altered, altered_manifest=None, altered_configurations=None):
        try:
            validate(manifest if altered_manifest is None else altered_manifest,
                     configurations if altered_configurations is None else altered_configurations, altered)
        except InvalidPolicy as error:
            checks.append({"name": name, "rejected": True, "reason": str(error)})
            return
        raise AssertionError("accepted corruption: " + name)

    altered = copy.deepcopy(policy)
    altered["overall_worst_expected_loss"] = -1e100
    rejected("forged_loss_field", altered)
    altered = copy.deepcopy(policy)
    altered["shared_actions"].append(altered["shared_actions"][0])
    rejected("duplicate_manufacturing", altered)
    altered = copy.deepcopy(policy)
    altered["cases"].pop()
    rejected("missing_case", altered)
    altered = copy.deepcopy(policy)
    altered["shared_actions"] = []
    rejected("unmanufactured_action", altered)
    caps = copy.deepcopy(manifest)
    caps["action_usage_caps"] = dict.fromkeys(caps["action_usage_caps"], 0)
    rejected("action_capacity", policy, altered_manifest=caps)
    if any(case["root"] == "probe" for case in policy["cases"]):
        caps = copy.deepcopy(manifest)
        caps["sensor_usage_caps"] = dict.fromkeys(caps["sensor_usage_caps"], 0)
        rejected("sensor_capacity", policy, altered_manifest=caps)
        altered = copy.deepcopy(policy)
        next(case for case in altered["cases"] if case["root"] == "probe")["branches"][0]["seconds"].pop()
        rejected("omitted_sector", altered)
        configs = copy.deepcopy(configurations)
        for case in configs:
            case["total_budget"] = 0
        rejected("path_budget", policy, altered_configurations=configs)
    for text in ('{"fake":NaN}', '{"fake":1e999}', '{"fake":1,"fake":2}'):
        try:
            strict_json(text)
        except InvalidPolicy:
            checks.append({"name": "invalid_json_" + text, "rejected": True})
        else:
            raise AssertionError("invalid JSON accepted")
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        submission = base / "malicious"
        submission.mkdir()
        hidden_path = str(ROOT / "evaluator" / "hidden" / "targets.json")
        source = ("import argparse,json,pathlib,socket\n"
                  "parser=argparse.ArgumentParser();parser.add_argument('--input');parser.add_argument('--output');arguments=parser.parse_args()\n"
                  "denied=[]\n"
                  "for path in " + repr([hidden_path, str(ROOT / "adversary" / "build_data.py"), "/home", "/srv"]) + ":\n"
                  " try:\n  pathlib.Path(path).read_bytes()\n  denied.append(False)\n"
                  " except (OSError,PermissionError):\n  denied.append(True)\n"
                  "pathlib.Path(arguments.output).write_text(json.dumps({'denied':denied}))\n")
        (submission / "solve.py").write_text(source)
        scratch = base / "run"
        scratch.mkdir()
        response, elapsed = run_isolated(submission, input_directory, scratch, 60)
        assert all(json.loads(response)["denied"])
        checks.append({"name": "hidden_filesystem_isolation", "rejected": True})
        (submission / "solve.py").write_text("while True:\n    pass\n")
        scratch = base / "timeout"
        scratch.mkdir()
        try:
            run_isolated(submission, input_directory, scratch, 0.5)
        except SubmissionFailure as error:
            assert "timeout" in str(error)
            checks.append({"name": "timeout", "rejected": True})
        else:
            raise AssertionError("timeout not enforced")
    return checks


def main():
    started = time.monotonic()
    report = {"physics": physics_checks(), "baselines": {}}
    print("independent physics checks passed", flush=True)
    suite = json.loads((ROOT / "evaluator" / "hidden" / "suite.json").read_text())
    baseline_records = {}
    last = None
    for entry in suite["fleets"]:
        directory = ROOT / "evaluator" / "hidden" / entry["directory"]
        with tempfile.TemporaryDirectory(prefix="xdiag_calibrate_") as temporary:
            response, seconds = run_isolated(ROOT / "participant" / "baseline", directory, temporary)
        policy = strict_json(response)
        manifest, configurations = load_configurations(directory)
        result = exact_score(manifest, configurations, policy)
        loaded_manifest, data = load_fleet(directory)
        catalog_value = objective(data, policy["cases"])
        difference = abs(catalog_value - result["objective"])
        assert difference < 2e-7
        result.update({"submission_seconds": seconds, "catalog_objective_error": difference,
                       "probe_cases": sum(case["root"] == "probe" for case in policy["cases"]),
                       "family": entry["family"],
                       "policy_sha256": hashlib.sha256(response.encode()).hexdigest()})
        baseline_records[entry["id"]] = result
        write_json(ROOT / "champions" / "baseline" / (entry["id"] + ".json"), policy)
        write_json(ROOT / "evaluator" / "hidden" / "baseline.json", {"fleets": baseline_records})
        print("baseline", entry["id"], result["objective"], "seconds", seconds, "probe", result["probe_cases"], flush=True)
        last = manifest, configurations, policy, directory
    report["baselines"] = baseline_records
    report["corruptions"] = corruption_checks(*last)
    report["passed"] = True
    report["elapsed_seconds"] = time.monotonic() - started
    write_json(ROOT / "adversary" / "validation_report.json", report)
    print("validation passed", flush=True)


if __name__ == "__main__":
    main()
