import math


def canonical(answer, expected):
    if answer.get("schema_version") != 1:
        raise ValueError("Wrong schema version")
    for key in ("num_detectors", "num_observables"):
        if type(answer.get(key)) is not int or answer[key] != expected[key]:
            raise ValueError(f"Wrong {key}")
    errors = answer.get("errors")
    if not isinstance(errors, list):
        raise ValueError("errors must be a list")
    terms = {}
    for error in errors:
        signature = []
        for name, bound in (("detectors", expected["num_detectors"]),
                            ("observables", expected["num_observables"])):
            indices = error.get(name)
            if not isinstance(indices, list) or any(type(index) is not int for index in indices):
                raise ValueError("Indices must be integer lists")
            if indices != sorted(set(indices)) or any(index < 0 or index >= bound for index in indices):
                raise ValueError("Invalid, duplicate, or unsorted index")
            signature.append(tuple(indices))
        signature = tuple(signature)
        probability = error.get("probability")
        if isinstance(probability, bool) or not isinstance(probability, (int, float)):
            raise ValueError("Invalid probability type")
        if not math.isfinite(probability) or not 0 < probability <= 1:
            raise ValueError("Probability must be finite and in (0,1]")
        if not any(signature) or signature in terms:
            raise ValueError("Silent or duplicate signature")
        terms[signature] = float(probability)
    return terms


def compare(answer, expected):
    reference = canonical(expected, expected)
    try:
        proposed = canonical(answer, expected)
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        return {"quality": 0.0, "exact": False, "error": str(error)}
    intersection = len(reference.keys() & proposed.keys())
    total_terms = len(reference) + len(proposed)
    support_f1 = 2 * intersection / total_terms if total_terms else 1.0
    total_mass = sum(reference.values()) + sum(proposed.values())
    discrepancy = sum(abs(reference.get(key, 0.0) - proposed.get(key, 0.0))
                      for key in reference.keys() | proposed.keys())
    fidelity = max(0.0, 1 - discrepancy / total_mass) if total_mass else 1.0
    exact = reference.keys() == proposed.keys() and all(
        math.isclose(probability, proposed[key], rel_tol=1e-9, abs_tol=1e-12)
        for key, probability in reference.items())
    return {"quality": support_f1 * fidelity, "exact": exact, "support_f1": support_f1,
            "probability_fidelity": fidelity, "expected_terms": len(reference),
            "returned_terms": len(proposed)}


def relative_score(quality, elapsed, baseline):
    epsilon = 1e-6
    weak_time = baseline["weak_seconds"]
    reference_time = baseline["reference_seconds"]
    if weak_time <= reference_time:
        raise ValueError("Calibration requires a slower weak baseline")
    speed = math.log((weak_time + epsilon) / (elapsed + epsilon)) / math.log(
        (weak_time + epsilon) / (reference_time + epsilon))
    weak_quality = baseline["weak_quality"]
    score = 100 * (quality ** 4 * (1 + speed) - weak_quality ** 4) / (2 - weak_quality ** 4)
    return score, speed
