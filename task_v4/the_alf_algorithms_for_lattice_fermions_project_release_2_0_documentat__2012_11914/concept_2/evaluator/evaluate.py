import argparse
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import time


HIDDEN = Path(__file__).resolve().parent / "hidden"


def reject_constant(value):
    raise ValueError("nonstandard JSON constant: " + value)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def parse_json(text):
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)


def contract():
    return json.loads((HIDDEN / "contract.json").read_text(encoding="utf-8"))


def validate(payload, rules):
    if type(payload) is not dict or set(payload) != {"schema_version", "stages"}:
        raise ValueError("expected exactly schema_version and stages")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    stages = payload["stages"]
    limits = rules["constraints"]
    if type(stages) is not list or len(stages) != limits["stage_count"]:
        raise ValueError("exactly 33 stages required")
    totals = {component: [] for component in rules["components"]}
    for index, stage in enumerate(stages):
        if type(stage) is not dict or set(stage) != {"component", "coefficient"}:
            raise ValueError("each stage requires exactly component and coefficient")
        component, coefficient = stage["component"], stage["coefficient"]
        if type(component) is not str or component not in totals:
            raise ValueError("unknown component")
        if type(coefficient) not in (int, float) or not math.isfinite(coefficient):
            raise ValueError("coefficients must be finite numbers, not booleans")
        if not limits["minimum_coefficient"] <= coefficient <= limits["maximum_coefficient"]:
            raise ValueError("coefficient outside positive interval")
        if index and stages[index - 1]["component"] == component:
            raise ValueError("adjacent identical components must be merged")
        totals[component].append(coefficient)
    for index, stage in enumerate(stages):
        reflected = stages[-1 - index]
        if reflected["component"] != stage["component"]:
            raise ValueError("component word is not palindromic")
        if abs(reflected["coefficient"] - stage["coefficient"]) > limits["palindrome_tolerance"]:
            raise ValueError("coefficient palindrome mismatch")
    if any(abs(math.fsum(values) - 1.0) > limits["sum_tolerance"] for values in totals.values()):
        raise ValueError("each component must have unit total time")
    return stages


def read_submission(path, rules):
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("submission must be a regular nonsymlink file")
        maximum = rules["constraints"]["max_submission_bytes"]
        if metadata.st_size > maximum:
            raise ValueError("submission exceeds byte limit")
        raw = handle.read(maximum + 1)
        if len(raw) > maximum:
            raise ValueError("submission exceeds byte limit")
    payload = parse_json(raw.decode("utf-8"))
    validate(payload, rules)
    return payload, len(raw)


def reference_stages(rules):
    order = rules["baseline"]["order"]
    repeats = rules["baseline"]["equal_substeps"]
    result = []
    single = [(name, 0.5 / repeats) for name in order[:-1]]
    single += [(order[-1], 1.0 / repeats)]
    single += [(name, 0.5 / repeats) for name in reversed(order[:-1])]
    for repeat in range(repeats):
        for name, weight in single:
            if result and result[-1]["component"] == name:
                result[-1]["coefficient"] += weight
            else:
                result.append({"component": name, "coefficient": weight})
    return result


def matrices(instance, names):
    import numpy as np

    dimension = math.prod(instance["shape"])
    result = {name: np.zeros((dimension, dimension), dtype=np.complex128) for name in names}
    for name, source, target, amplitude, phase in instance["bonds"]:
        value = -amplitude * np.exp(1j * phase)
        result[name][source, target] += value
        result[name][target, source] += value.conjugate()
    result["V"] = np.diag(np.asarray(instance["site_potential"], dtype=np.complex128))
    return result


def product(stages, components, step):
    import numpy as np
    from scipy.linalg import expm

    dimension = next(iter(components.values())).shape[0]
    propagator = np.eye(dimension, dtype=np.complex128)
    for stage in stages:
        propagator = propagator @ expm(-step * stage["coefficient"] * components[stage["component"]])
    return propagator


def canonical_stages(stages):
    canonical = [dict(stage) for stage in stages]
    for index in range(len(stages) // 2):
        reflected = len(stages) - index - 1
        coefficient = (stages[index]["coefficient"] + stages[reflected]["coefficient"]) / 2.0
        canonical[index]["coefficient"] = coefficient
        canonical[reflected]["coefficient"] = coefficient
    return canonical


def positive_spectrum(stages, components, step):
    import numpy as np
    from scipy.linalg import expm, svd

    center = len(stages) // 2
    dimension = next(iter(components.values())).shape[0]
    half_product = np.eye(dimension, dtype=np.complex128)
    for stage in stages[:center]:
        half_product = half_product @ expm(-step * stage["coefficient"] * components[stage["component"]])
    middle = stages[center]
    half_product = half_product @ expm(-step * middle["coefficient"] * components[middle["component"]] / 2.0)
    vectors, singular_values, _ = svd(half_product, full_matrices=False, lapack_driver="gesvd")
    if np.any(singular_values <= 0) or not np.all(np.isfinite(singular_values)):
        raise ValueError("positive propagator spectrum could not be resolved")
    return vectors, 2.0 * np.log(singular_values)


def spectral_observables(vectors, log_eigenvalues, repeats):
    import numpy as np
    from scipy.special import expit

    logarithms = repeats * log_eigenvalues
    propagator = (vectors * np.exp(logarithms)) @ vectors.conj().T
    green = (vectors * expit(-logarithms)) @ vectors.conj().T
    return propagator, green


def score(payload, rules, instances):
    import numpy as np
    from scipy.linalg import eigh, norm

    stages = canonical_stages(validate(payload, rules))
    reference = reference_stages(rules)
    validate({"schema_version": 1, "stages": reference}, rules)
    ratios = {family["name"]: [] for family in rules["sampling"]["families"]}
    absolute = {name: {"submission": [], "baseline": []} for name in ratios}
    worst = {"ratio": -1.0}
    floor = rules["scoring"]["numerical_floor"]
    for instance in instances:
        components = matrices(instance, rules["components"])
        total = sum(components.values())
        exact_eigenvalues, exact_vectors = eigh(total)
        for step in rules["sampling"]["dtau"]:
            candidate_vectors, candidate_log_values = positive_spectrum(stages, components, step)
            baseline_vectors, baseline_log_values = positive_spectrum(reference, components, step)
            for repeats in rules["sampling"]["repetitions"]:
                exact, exact_green = spectral_observables(exact_vectors, -step * exact_eigenvalues, repeats)
                candidate, candidate_green = spectral_observables(candidate_vectors, candidate_log_values, repeats)
                baseline, baseline_green = spectral_observables(baseline_vectors, baseline_log_values, repeats)
                for observable, truth, proposed, control in (("propagator", exact, candidate, baseline), ("green", exact_green, candidate_green, baseline_green)):
                    proposed_error = float(norm(proposed - truth, "fro") / norm(truth, "fro"))
                    control_error = float(norm(control - truth, "fro") / norm(truth, "fro"))
                    ratio = max(proposed_error, floor) / max(control_error, floor)
                    if not all(math.isfinite(value) for value in (ratio, proposed_error, control_error)):
                        raise ValueError("nonfinite numerical result")
                    family = instance["family"]
                    ratios[family].append(ratio)
                    absolute[family]["submission"].append(proposed_error)
                    absolute[family]["baseline"].append(control_error)
                    if ratio > worst["ratio"]:
                        worst = {"ratio": ratio, "case_id": instance["id"], "family": family, "dtau": step, "repetitions": repeats, "observable": observable}
    family_scores = {name: float(1 / np.sqrt(np.mean(np.square(values)))) for name, values in ratios.items()}
    core = math.exp(math.fsum(math.log(value) for value in family_scores.values()) / len(family_scores))
    minimum = min(family_scores.values())
    targets = rules["scoring"]["targets"]
    failures = []
    if core < targets["core_score_min"]:
        failures.append("core_score below target")
    if minimum < targets["worst_family_score_min"]:
        failures.append("worst_family_score below target")
    if worst["ratio"] > targets["max_point_ratio_max"]:
        failures.append("pointwise regression cap exceeded")
    absolute_rms = {name: {kind: float(np.sqrt(np.mean(np.square(values)))) for kind, values in entries.items()} for name, entries in absolute.items()}
    return {"valid": True, "passed": not failures, "reason": "; ".join(failures) if failures else "all frozen targets met", "core_score": core, "worst_family_score": minimum, "resource_score": 1.0, "runtime_score": 1.0, "family_scores": family_scores, "max_point_ratio": worst["ratio"], "worst_point": worst, "absolute_error_rms": absolute_rms, "scored_points": sum(map(len, ratios.values())), "stage_count": len(stages), "targets": targets}


def invalid_report(reason):
    return {"valid": False, "passed": False, "reason": reason, "core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0, "runtime_score": 0.0}


def worker():
    import resource

    rules = contract()
    limits = rules["constraints"]
    resource.setrlimit(resource.RLIMIT_CPU, (limits["worker_cpu_seconds"], limits["worker_cpu_seconds"]))
    resource.setrlimit(resource.RLIMIT_AS, (limits["worker_address_space_bytes"], limits["worker_address_space_bytes"]))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    started = time.monotonic()
    try:
        payload = parse_json(sys.stdin.read(limits["max_submission_bytes"] + 1))
        instances = json.loads((HIDDEN / "instances.json").read_text())["instances"]
        report = score(payload, rules, instances)
    except Exception as error:
        report = invalid_report("evaluation failed: " + type(error).__name__ + ": " + str(error))
    report["runtime_seconds"] = time.monotonic() - started
    report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(report, allow_nan=False))


def evaluate(path):
    started = time.monotonic()
    try:
        rules = contract()
        payload, byte_count = read_submission(path, rules)
        environment = dict(os.environ)
        for name in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
            environment[name] = "1"
        result = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker"], input=json.dumps(payload), text=True, capture_output=True, timeout=rules["constraints"]["worker_wall_seconds"], env=environment)
        if result.returncode:
            report = invalid_report("worker exited or exceeded resource cap: " + str(result.returncode))
        else:
            report = parse_json(result.stdout)
        report["submission_bytes"] = byte_count
    except subprocess.TimeoutExpired:
        report = invalid_report("worker wall-time cap exceeded")
    except (OSError, ValueError, TypeError, OverflowError, RecursionError) as error:
        report = invalid_report(type(error).__name__ + ": " + str(error))
    report["total_runtime_seconds"] = time.monotonic() - started
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    if arguments.worker:
        worker()
        return
    if arguments.submission is None:
        parser.error("--submission is required")
    report = evaluate(arguments.submission)
    serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()
