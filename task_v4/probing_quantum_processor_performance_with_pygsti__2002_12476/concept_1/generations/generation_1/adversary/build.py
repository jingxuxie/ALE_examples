import json
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import expm

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "participant"
sys.path.insert(0, str(PUBLIC / "workspace"))
sys.path.insert(0, str(PUBLIC / "baseline"))
from physics import (AXES, FAMILIES, MEASUREMENTS, fisher_features, nominal_parameters,
                     probabilities, risks, sample_parameters)
from solve import allocate


def generate_candidates():
    rng = np.random.default_rng(82021)
    candidates = []
    seen = set()

    def add(germ, repetitions, preparation, measurement):
        key = (germ, repetitions, preparation, measurement)
        if key not in seen:
            seen.add(key)
            candidates.append(dict(germ=germ, repetitions=int(repetitions),
                                   preparation=int(preparation), measurement=int(measurement)))

    for germ in "XYI":
        for preparation in range(6):
            for measurement in range(3):
                add(germ, 1, preparation, measurement)
    germs = ["X", "Y", "I", "XY", "XI", "YI", "XXY", "XYY", "XIXY", "XYII", "XXYYI"]
    for length in range(3, 9):
        for repetition in range(6):
            germs.append("".join(rng.choice(list("XYI"), length)))
    while len(candidates) < 840:
        germ = str(rng.choice(germs))
        repetitions = int(rng.choice([1, 2, 4, 8, 16, 32, 64]))
        if len(germ) * repetitions <= 256:
            add(germ, repetitions, int(rng.integers(6)), int(rng.integers(3)))
    return candidates


def density_probabilities(parameters, candidates):
    paulis = np.array([[[0, 1], [1, 0]], [[0, -1j], [1j, 0]], [[1, 0], [0, -1]]])
    rotations = parameters[:9].reshape(3, 3).copy()
    rotations[0, 0] += np.pi / 2
    rotations[1, 1] += np.pi / 2
    unitaries = [expm(-0.5j * np.einsum("i,ijk->jk", vector, paulis)) for vector in rotations]
    answers = []
    for circuit in candidates:
        state = (np.eye(2) + np.einsum("i,ijk->jk", AXES[circuit["preparation"]], paulis)) / 2
        for label in circuit["germ"] * circuit["repetitions"]:
            index = "XYI".index(label)
            state = unitaries[index] @ state @ unitaries[index].conj().T
            attenuation = np.exp(-parameters[9 + index])
            state = attenuation * state + (1 - attenuation) * np.eye(2) / 2
        effect = ((1 + parameters[12]) * np.eye(2) +
                  parameters[13] * np.einsum("i,ijk->jk", MEASUREMENTS[circuit["measurement"]], paulis)) / 2
        answers.append(float(np.trace(effect @ state).real))
    return np.array(answers)


def main():
    for directory in [PUBLIC / "input", ROOT / "evaluator/hidden", ROOT / "attempts",
                      ROOT / "champions", ROOT / "adversary/results"]:
        directory.mkdir(parents=True, exist_ok=True)
    candidates = generate_candidates()
    contract = dict(shots_per_batch=64, reset_ticks=20, setup_ticks=12000,
                    execution_budget_ticks=1600000, max_distinct_circuits=24,
                    max_batches_per_circuit=48, target_core_reduction=0.50,
                    target_worst_family_reduction=0.40,
                    numerical_information_ridge=1e-10,
                    parameter_order=[f"{gate}_{axis}" for gate in "XYI" for axis in "xyz"] +
                    ["X_depolarization_rate", "Y_depolarization_rate", "I_depolarization_rate",
                     "readout_bias", "readout_visibility"])
    (PUBLIC / "input/candidates.json").write_text(json.dumps(candidates, indent=2) + "\n")
    for destination in [PUBLIC / "input/contract.json", ROOT / "evaluator/hidden/contract.json"]:
        destination.write_text(json.dumps(contract, indent=2) + "\n")
    nominal_features = fisher_features(nominal_parameters(), candidates)
    baseline = allocate(nominal_features, candidates, contract)
    (PUBLIC / "baseline/design.json").write_text(json.dumps({"batches": baseline.tolist()}) + "\n")
    for name, seed, per_family in [("development", 51210, 3), ("benchmark", 717342918, 10)]:
        rng = np.random.default_rng(seed)
        parameters = []
        families = []
        features = []
        for family in FAMILIES:
            for index in range(per_family):
                operating_point = sample_parameters(rng, family)
                parameters.append(operating_point)
                families.append(family)
                features.append(fisher_features(operating_point, candidates))
            print(name, family, flush=True)
        features = np.array(features)
        destination = PUBLIC / "input/development.npz" if name == "development" else ROOT / "evaluator/hidden/benchmark.npz"
        costs = np.array([64 * (20 + len(circuit["germ"]) * circuit["repetitions"]) for circuit in candidates])
        np.savez_compressed(destination, features=features, families=np.array(families),
                            parameters=parameters, nominal_features=nominal_features,
                            baseline_risks=risks(features, baseline), costs=costs)
    check_rng = np.random.default_rng(985215)
    model_errors = []
    derivative_errors = []
    for family in FAMILIES:
        parameters = sample_parameters(check_rng, family)
        subset = [candidates[int(index)] for index in check_rng.choice(len(candidates), 30, replace=False)]
        model_errors.append(float(np.max(np.abs(probabilities(parameters, subset) - density_probabilities(parameters, subset)))))
        derivative_errors.append(float(np.max(np.abs(fisher_features(parameters, subset) -
                                                      fisher_features(parameters, subset, step=5e-7)))))
    audit = dict(density_matrix_max_error=max(model_errors), derivative_step_max_error=max(derivative_errors),
                 simulator_valid=max(model_errors) < 1e-11 and max(derivative_errors) < 1e-6,
                 gate_channels="unitary followed by nonnegative-rate depolarization",
                 measurement_validity="all disclosed regimes satisfy abs(bias)+visibility<1",
                 target_frozen_before_attempt=True, scenarios_per_hidden_family=10)
    (ROOT / "adversary/results/build_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (ROOT / "status.json").write_text(json.dumps(dict(concept="robust_characterization_allocation", mode="A",
                    status="built", target_core_reduction=0.50, target_worst_family_reduction=0.40,
                    solvability="unknown", ratchet_generations=0), indent=2) + "\n")
    print(json.dumps(audit), flush=True)


if __name__ == "__main__":
    main()
