import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from physics import QuantumCase


FAMILIES = ("drifting_priors", "sector_congestion", "frustrated_bridges")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def case_configuration(random, family, case_id, length=8):
    sites = np.arange(length)
    regime_ids = ["regime_{}".format(index) for index in range(4)]
    temperature = random.uniform(0.65, 1.45)
    final_time = random.uniform(2.15, 3.5)
    initial = sorted(random.choice(length, length // 2, replace=False).tolist())
    entropy = sorted(random.choice(length, length // 2, replace=False).tolist())
    case = {"case_id": case_id, "L": length, "nup": length // 2,
            "J1xy": 1.0, "J1z": float(random.uniform(0.55, 1.35)),
            "J2xy": float(random.uniform(0.15, 0.65)), "J2z": float(random.uniform(0.1, 0.55)),
            "delta": float(random.uniform(0.15, 0.45)), "drive_amplitude": float(random.uniform(0.2, 0.65)),
            "drive_omega": float(random.uniform(1.3, 3.2)), "t_final": final_time,
            "open_loop_time": final_time * 0.48, "initial_up_sites": initial,
            "entropy_sites": entropy, "imbalance_weight": float(random.uniform(0.25, 0.8)),
            "total_budget": int(random.choice([5, 6, 7])), "regimes": [], "prior_scenarios": []}
    if family == "frustrated_bridges":
        case["J2xy"] *= 1.65
        case["J2z"] *= 1.5
    for index, identifier in enumerate(regime_ids):
        scale = (index - 1.5) / 1.5
        case["regimes"].append({"regime_id": identifier,
                                "j2_multiplier": 1 + 0.48 * scale,
                                "delta_multiplier": 1 - 0.45 * scale,
                                "drive_multiplier": 1 + 0.4 * scale,
                                "omega_multiplier": 1 - 0.22 * scale})
    for index in range(5):
        prior = random.dirichlet(np.full(4, 1.8 if index == 0 else 0.2))
        if index:
            prior = 0.3 * prior + 0.7 * np.eye(4)[index - 1]
        case["prior_scenarios"].append({"scenario_id": "prior_{}".format(index),
                                        "prior": dict(zip(regime_ids, prior.tolist()))})
    phase_templates = [np.zeros(length), 0.6 * (-1.0) ** sites, -0.65 * (-1.0) ** sites,
                       1.2 * np.cos(2 * np.pi * sites / length),
                       1.1 * np.sin(2 * np.pi * sites / length),
                       np.linspace(-1.5, 1.5, length), np.linspace(1.8, -1.8, length),
                       1.5 * np.cos(4 * np.pi * sites / length),
                       random.normal(0, 0.95, length), random.normal(0, 1.25, length)]
    case["actions"] = [{"action_id": "feedback_{}".format(index), "cost": [0, 1, 1, 2, 2, 2, 2, 1, 3, 3][index],
                         "phase": (temperature * phase).tolist()} for index, phase in enumerate(phase_templates)]
    permutations = [((sites + 2) % length).tolist(), ((1 - sites) % length).tolist(),
                    ((3 - sites) % length).tolist()]
    case["sensors"] = []
    for index in range(7):
        early = index < 3
        permutation_index = index if early else [0, 1, 2, 0][index - 3]
        order = length // 2 if permutation_index == 0 else 2
        time_fraction = [0.21, 0.26, 0.31, 0.51, 0.59, 0.65, 0.72][index]
        phases = random.normal(0, 0.65 if family != "frustrated_bridges" else 1.2, (order, length))
        phases -= phases.mean(axis=1)[:, None]
        case["sensors"].append({"sensor_id": "sensor_{}".format(index),
                                 "permutation": permutations[permutation_index], "order": order,
                                 "time": final_time * time_fraction, "cost": [1, 1, 2, 1, 1, 2, 2][index],
                                 "bridge_phase_by_sector": phases.tolist() if early else np.zeros_like(phases).tolist()})
    results = ["red", "green", "blue"]
    probe = {"test_id": "calibration", "cost": 1, "results": results,
             "likelihood_by_regime": {}, "allowed_first_sensor_ids": {},
             "allowed_second_sensor_ids_by_sector": {}}
    for index, identifier in enumerate(regime_ids):
        likelihood = np.array([[0.72, 0.19, 0.09], [0.38, 0.45, 0.17],
                               [0.17, 0.48, 0.35], [0.06, 0.2, 0.74]])[index]
        if family == "drifting_priors":
            likelihood = 0.75 * likelihood + 0.25 * random.dirichlet(np.ones(3))
        probe["likelihood_by_regime"][identifier] = dict(zip(results, likelihood.tolist()))
    for result in results:
        probe["allowed_first_sensor_ids"][result] = ["sensor_{}".format(index) for index in random.permutation(3)]
    for sensor in case["sensors"][:3]:
        probe["allowed_second_sensor_ids_by_sector"][sensor["sensor_id"]] = [
            ["sensor_{}".format(index) for index in random.permutation(np.arange(3, 7))]
            for sector in range(sensor["order"])]
    case["calibration_test"] = probe
    return case


def build_fleet(destination, family, seed, case_count):
    random = np.random.RandomState(seed)
    manifest = {"schema_version": 1, "fleet_id": "fleet_{}".format(seed),
                "shared_sensor_count": 4, "shared_action_count": 4,
                "sensor_usage_caps": {}, "action_usage_caps": {}, "cases": []}
    for index in range(7):
        multiplier = [1.6, 1.8, 1.5, 4.0, 3.5, 3.0, 3.8][index]
        if family == "sector_congestion":
            multiplier *= [1.0, 0.85, 0.9, 0.8, 0.75, 0.8, 0.9][index]
        manifest["sensor_usage_caps"]["sensor_{}".format(index)] = max(3, int(case_count * multiplier))
    for index in range(10):
        manifest["action_usage_caps"]["feedback_{}".format(index)] = max(case_count, int(case_count * random.uniform(9, 16)))
    destination.mkdir(parents=True, exist_ok=True)
    for index in range(case_count):
        case_id = "unit_{}".format(index)
        length = 10 if index == case_count - 1 and case_count >= 6 else 8
        case = case_configuration(random, family, case_id, length)
        configuration = "{}.json".format(case_id)
        responses = "{}.npz".format(case_id)
        write_json(destination / configuration, case)
        model = QuantumCase(case, propagators=True)
        catalog = model.catalog()
        np.savez_compressed(destination / responses, **catalog)
        manifest["cases"].append({"case_id": case_id, "configuration": configuration, "responses": responses})
        print(f"built {family} {seed} {case_id} dim={model.dimension}", flush=True)
    write_json(destination / "manifest.json", manifest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-only", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    arguments = parser.parse_args()
    private_index = []
    for family_index, family in enumerate(FAMILIES):
        public_destination = ROOT / "participant" / "input" / "examples" / family
        if not arguments.skip_existing or not (public_destination / "manifest.json").exists():
            build_fleet(public_destination, family, 9100 + family_index, 4)
        if not arguments.public_only:
            for replicate in range(2):
                identifier = "{}_{}".format(family, replicate)
                destination = ROOT / "evaluator" / "hidden" / "fleets" / identifier
                if not arguments.skip_existing or not (destination / "manifest.json").exists():
                    build_fleet(destination, family, 48071 + 397 * family_index + replicate * 73, 7 + replicate)
                private_index.append({"id": identifier, "family": family,
                                      "directory": "fleets/" + identifier})
    if private_index:
        write_json(ROOT / "evaluator" / "hidden" / "suite.json", {"fleets": private_index})
    hashes = {}
    for base in (ROOT / "participant" / "input" / "examples", ROOT / "evaluator" / "hidden" / "fleets"):
        for path in sorted(base.rglob("*")):
            if path.is_file():
                hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(ROOT / "adversary" / "asset_hashes.json", hashes)


if __name__ == "__main__":
    main()
