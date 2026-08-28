import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import sys

from engine import infer_parameters, np, predict, simulate

BASE = pathlib.Path(__file__).resolve().parents[2]


def settings(length, spin, strength, protection, seed, inhomogeneous=False):
    random = np.random.default_rng(seed)
    positions = np.arange(length)
    profile = np.zeros(length)
    if inhomogeneous:
        profile = 0.3 * np.cos(positions * 2 * np.pi / length + random.uniform(0, 2))
        profile += random.uniform(-0.07, 0.07, length)
    return {"length": length, "spin": spin, "J": 1.0,
            "mass": float(random.uniform(-0.12, 0.2)), "electric": 0.5,
            "V": strength, "protection": protection,
            "coefficients": [float((-1) ** site) for site in positions],
            "profile": profile.tolist()}


def make_case(seed, family, size_index=0):
    random = np.random.default_rng(seed)
    parameters = [float(random.uniform(0.06, 0.21)), float(random.uniform(0.04, 0.17)), float(random.uniform(-0.17, 0.17))]
    if family == "full_half":
        configuration = settings([32, 48][size_index % 2], 0.5, [4.0, 8.0][size_index % 2], "full", seed)
        times = [0.0, 0.3, 1.0, 2.5, 5.0, 8.0]
    elif family == "linear_spin_one":
        configuration = settings([32, 40][size_index % 2], 1.0, [4.0, 7.0][size_index % 2], "linear", seed)
        times = [0.0, 0.25, 0.8, 2.0, 4.0, 6.0]
    elif family == "inhomogeneous_weak":
        configuration = settings([32, 48][size_index % 2], 0.5, [0.5, 1.0][size_index % 2], "full", seed, True)
        times = [0.0, 0.2, 0.7, 1.5, 3.0, 4.5]
    else:
        raise ValueError(family)
    calibration = []
    for index in range(2):
        small = settings(2, 0.5, float(index * 1.4), "full", seed + index + 31, True)
        small["mass"] += 0.3 * index
        sample_times = [0.0, 0.19, 0.43, 0.81, 1.3, 1.9]
        observed = simulate(small, parameters, sample_times, [[0, 1]])
        for name, values in observed.items():
            array = np.array(values)
            observed[name] = (array + random.normal(0, 2e-6, array.shape)).tolist()
        calibration.append({"settings": small, "times": sample_times, "pairs": [[0, 1]], "observed": observed, "noise_sigma": 2e-6})
    length = configuration["length"]
    pairs = [[length // 2 - 3, length // 2 - 1], [length // 2 - 3, length // 2 + 1],
             [length // 2 - 5, length // 2 + 3], [1, 5]]
    case = {"calibration": calibration, "experiment": configuration, "times": times, "pairs": pairs}
    return case, parameters


def build_record(arguments):
    split, seed, family, index, step, bond, engine_name = arguments
    identifier = f"{family}_{seed}"
    destination = BASE / "private" / "challenge_pool" / split / (identifier + ".json")
    if destination.exists():
        print("existing " + identifier, flush=True)
        return str(destination)
    case, parameters = make_case(seed, family, index)
    fitted, fit_audit = infer_parameters(case)
    predictor = predict
    if engine_name == "charge":
        from charge_engine import predict as predictor
    coarse, coarse_audit = predictor(case["experiment"], parameters, case["times"], case["pairs"], step=step * 2, bond=max(32, bond // 2), cutoff=1e-9)
    reference, fine_audit = predictor(case["experiment"], parameters, case["times"], case["pairs"], step=step, bond=bond, cutoff=1e-12)
    differences = {name: float(np.max(abs(np.asarray(reference[name]) - np.asarray(coarse[name]))))
                   for name in ("density", "violation", "correlation")}
    record = {"id": identifier, "family": family, "split": split, "case": case,
              "reference": reference, "true_parameters": parameters, "coarse_prediction": coarse,
              "audit": {"calibration_fit": fitted, "calibration_parameter_error": float(np.max(abs(np.array(fitted) - parameters))),
                        "calibration": fit_audit, "coarse": coarse_audit, "fine": fine_audit, "max_differences": differences}}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.pending')
    temporary.write_text(json.dumps(record, indent=2))
    temporary.replace(destination)
    print(json.dumps({"built": identifier, "differences": differences, "fine": fine_audit}), flush=True)
    return str(destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="screening", choices=["screening", "challenge", "confirmation"])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--step", type=float, default=0.0125)
    parser.add_argument("--bond", type=int, default=96)
    parser.add_argument("--one", action="store_true")
    parser.add_argument("--engine", choices=["quimb", "charge"], default="quimb")
    arguments = parser.parse_args()
    seed_base = {"screening": 18300, "challenge": 29400, "confirmation": 81700}[arguments.split]
    jobs = [(arguments.split, seed_base + 17 * family_index + index, family, index, arguments.step, arguments.bond, arguments.engine)
            for family_index, family in enumerate(["full_half", "linear_spin_one", "inhomogeneous_weak"])
            for index in range(2 if arguments.split != "challenge" else 3)]
    if arguments.one:
        jobs = jobs[:1]
    with concurrent.futures.ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        list(executor.map(build_record, jobs))
    lookup = {}
    for path in (BASE / "private" / "challenge_pool").glob("*/*.json"):
        record = json.loads(path.read_text())
        key = hashlib.sha256(json.dumps(record["case"], sort_keys=True).encode()).hexdigest()
        lookup[key] = record["reference"]
    (BASE / "private" / "reference" / "oracle" / "lookup.json").write_text(json.dumps(lookup))
    case, _ = make_case(153, "full_half")
    case["experiment"]["length"] = 4
    case["experiment"]["coefficients"] = case["experiment"]["coefficients"][:4]
    case["experiment"]["profile"] = case["experiment"]["profile"][:4]
    case["times"] = [0.0, 0.2, 0.5]
    case["pairs"] = [[0, 2]]
    example_path = BASE / "participant" / "input" / "example.json"
    if not example_path.exists():
        example_path.write_text(json.dumps(case, indent=2))


if __name__ == "__main__":
    main()
