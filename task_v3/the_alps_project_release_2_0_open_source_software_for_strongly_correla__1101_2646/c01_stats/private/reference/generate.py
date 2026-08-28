import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from independent import solve as independent_solve


ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT.parent
PILOT = PRIVATE.parent
sys.path.insert(0, str(PRIVATE))
from evaluator import measure_errors, score_answer


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def moment(index):
    return {"moment": index}


def constant(value):
    return {"constant": value}


def operation(name, *arguments):
    return {"op": name, "args": list(arguments)}


def squared(expression):
    return operation("mul", expression, expression)


def family_data(family, latent, variant):
    first, second, third = latent.T
    if family == "thermodynamic_response":
        energy = -0.7 + 0.5 * first + 0.10 * second ** 2
        density = 1.0 + 0.18 * np.tanh(second) + 0.07 * first + 0.03 * third
        measurements = np.column_stack((energy, energy ** 2, density, density ** 2, energy * density))
        beta = 1.4 + 0.2 * variant
        expressions = [moment(0),
                       operation("mul", constant(beta ** 2), operation("sub", moment(1), squared(moment(0)))),
                       operation("mul", constant(beta), operation("sub", moment(3), squared(moment(2)))),
                       operation("mul", constant(beta), operation("sub", moment(4),
                                                                  operation("mul", moment(0), moment(2))))]
    elif family == "magnetic_cumulants":
        magnetization = 0.75 * np.tanh(1.4 * first) + 0.12 * second + 0.025 * third
        measurements = np.column_stack((magnetization ** 2, magnetization ** 4,
                                        magnetization ** 6, np.abs(magnetization)))
        expressions = [moment(0),
                       operation("sub", constant(1.0), operation("div", moment(1),
                                                                 operation("mul", constant(3.0), squared(moment(0))))),
                       operation("div", moment(2), operation("mul", squared(moment(0)), moment(0))),
                       operation("sub", moment(0), squared(moment(3)))]
    elif family == "coupled_susceptibilities":
        charge = 0.5 + 0.6 * first + 0.12 * third
        spin = -0.3 + (-0.65 if variant % 2 else 0.65) * first + 0.5 * second + 0.08 * third
        measurements = np.column_stack((charge, spin, charge ** 2, spin ** 2, charge * spin))
        charge_variance = operation("sub", moment(2), squared(moment(0)))
        spin_variance = operation("sub", moment(3), squared(moment(1)))
        cross = operation("sub", moment(4), operation("mul", moment(0), moment(1)))
        expressions = [cross,
                       operation("div", cross, operation("sqrt", operation("mul", charge_variance, spin_variance))),
                       operation("div", charge_variance, spin_variance),
                       operation("sub", moment(0), moment(1))]
    else:
        amplitude = np.exp(0.14 * first)
        mass = 0.7 + 0.07 * np.tanh(second) + 0.02 * np.tanh(third)
        spacing = 0.6 + 0.03 * variant
        measurements = np.column_stack([
            amplitude * np.exp(-mass * spacing * index)
            + 0.25 * np.exp(0.1 * third) * np.exp(-1.8 * spacing * index)
            + 0.015 * np.exp(0.12 * (index + 1) * np.tanh(first - second))
            for index in range(4)])
        expressions = [operation("div", operation("log", operation("div", moment(0), moment(1))), constant(spacing)),
                       operation("div", operation("log", operation("div", moment(1), moment(2))), constant(spacing)),
                       operation("div", moment(2), moment(0)), operation("div", moment(3), moment(0))]
    return measurements, expressions


def make_case(family, variant, seed):
    generator = np.random.default_rng(seed)
    replica_count = 3 + (variant % 2)
    replicas = []
    for replica_index in range(replica_count):
        length = 1957 + 773 * replica_index + 157 * variant + int(generator.integers(0, 101))
        coefficient = [0.55, 0.94, 0.82, 0.975, 0.985][variant]
        coefficient = min(0.991, coefficient + 0.002 * replica_index)
        latent = np.empty((length + 512, 3))
        latent[0] = generator.normal(size=3)
        noise = generator.normal(size=latent.shape)
        mixing = np.array([[1.0, 0.0, 0.0], [0.35, 0.93675, 0.0], [-0.2, 0.25, 0.94736]])
        noise = noise @ mixing.T
        for index in range(1, len(latent)):
            latent[index] = coefficient * latent[index - 1] + np.sqrt(1 - coefficient ** 2) * noise[index]
        latent = latent[512:]
        measurements, expressions = family_data(family, latent, variant)
        sign = 1
        signs = []
        persistence = [0.1, 0.72, 0.5, 0.85, 0.90][variant]
        for row in latent:
            if generator.random() > persistence:
                probability = 0.79 - 0.025 * variant + 0.045 * np.tanh(row[0])
                sign = 1 if generator.random() < probability else -1
            signs.append(sign)
        if np.mean(signs) < 0.22:
            return make_case(family, variant, seed + 100003)
        replicas.append({"signs": signs, "measurements": measurements.tolist()})
    return {"schema_version": 1, "block_sizes": [1, 16 if variant % 2 == 0 else 32, 128],
            "expressions": expressions, "replicas": replicas}


def public_example():
    replicas = []
    for replica_index, length in enumerate((11, 14)):
        values = np.linspace(0.7, 1.4, length) + 0.1 * replica_index
        replicas.append({"signs": [-1 if index % 5 == 2 else 1 for index in range(length)],
                         "measurements": np.column_stack((values, values ** 2,
                                                           0.8 + 0.1 * np.cos(values * 4))).tolist()})
    return {"schema_version": 1, "block_sizes": [1, 3],
            "expressions": [moment(0), operation("sub", moment(1), squared(moment(0))),
                            operation("div", moment(2), moment(0))], "replicas": replicas}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n")


def reference_difference(actual, expected):
    maximum_mean = 0.0
    maximum_covariance = 0.0
    for actual_block, target_block in zip(actual["analyses"], expected["analyses"]):
        for actual_statistics, target_statistics in zip([actual_block["pooled"]] + actual_block["replicas"],
                                                        [target_block["pooled"]] + target_block["replicas"]):
            for key in ("mean", "covariance"):
                values = np.asarray(actual_statistics[key])
                target = np.asarray(target_statistics[key])
                relative = float(np.linalg.norm(values - target) / max(np.linalg.norm(target), 1e-14))
                if key == "mean":
                    maximum_mean = max(maximum_mean, relative)
                else:
                    maximum_covariance = max(maximum_covariance, relative)
    return maximum_mean, maximum_covariance


def main():
    weak = load_module("public_weak", PILOT / "participant" / "workspace" / "solve.py")
    families = ["thermodynamic_response", "magnetic_cumulants", "coupled_susceptibilities", "effective_gaps"]
    manifest = {"schema_version": 1, "reference_commit": "fccd5403b08c4e5c450229714d28be5ca4a07229",
                "core": [], "challenge": []}
    checks = []
    write_json(PILOT / "participant" / "input" / "example.json", public_example())
    for split, variants in (("core", (0, 1)), ("challenge", (2, 3, 4))):
        case_index = 0
        for family_index, family in enumerate(families):
            for variant in variants:
                case_index += 1
                case_id = "%s_%02d" % (split, case_index)
                directory = ROOT / "core" if split == "core" else PRIVATE / "challenge_pool"
                input_path = directory / "inputs" / (case_id + ".json")
                reference_path = directory / "outputs" / (case_id + ".json")
                data = make_case(family, variant, 431071 + family_index * 9001 + variant * 503)
                write_json(input_path, data)
                reference_path.parent.mkdir(parents=True, exist_ok=True)
                started = time.monotonic()
                subprocess.run([str(ROOT / "alea_oracle"), "--input", str(input_path),
                                "--output", str(reference_path)], check=True, timeout=120)
                runtime = time.monotonic() - started
                actual = json.loads(reference_path.read_text())
                expected = independent_solve(data)
                mean_difference, covariance_difference = reference_difference(actual, expected)
                if mean_difference > 2e-8 or covariance_difference > 2e-6:
                    raise RuntimeError("independent check failed for %s: %s %s" %
                                       (case_id, mean_difference, covariance_difference))
                weak_answer = weak.solve(data)
                weak_errors = measure_errors(weak_answer, actual)
                entry = {"case_id": case_id, "family": family,
                         "input": str(input_path.relative_to(PRIVATE)),
                         "reference": str(reference_path.relative_to(PRIVATE)),
                         "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
                         "reference_sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
                         "weak_errors": weak_errors,
                         "reference_seconds": runtime}
                manifest[split].append(entry)
                checks.append({"case_id": case_id, "family": family, "mean_relative_error": mean_difference,
                               "covariance_relative_error": covariance_difference, "reference_seconds": runtime,
                               "weak_score": score_answer(weak_answer, actual, weak_errors)["score"],
                               "independent_score": score_answer(expected, actual, weak_errors)["score"],
                               "rows": sum(len(replica["signs"]) for replica in data["replicas"]),
                               "average_signs": [float(np.mean(replica["signs"])) for replica in data["replicas"]]})
                print(case_id, "native_s=%.3f" % runtime, "check_cov=%.3g" % covariance_difference, flush=True)
    write_json(PRIVATE / "manifest.json", manifest)
    write_json(ROOT / "generation_checks.json", {"cases": checks})


if __name__ == "__main__":
    main()
