import json
from pathlib import Path


def expand_operations(operations):
    for operation in operations:
        if operation["op"] == "REPEAT":
            for repeat_index in range(operation["count"]):
                yield from expand_operations(operation["body"])
        else:
            yield operation


def bit_indices(mask):
    result = []
    while mask:
        lowest = mask & -mask
        result.append(lowest.bit_length() - 1)
        mask ^= lowest
    return result


def parity_mask(indices):
    result = 0
    for index in indices:
        result ^= 1 << index
    return result


def lower_operations(case):
    measurement_count = 0
    detector_count = 0
    result = []
    for original in expand_operations(case["operations"]):
        operation = dict(original)
        name = operation["op"]
        if name in ("M", "MX"):
            operation["record_start"] = measurement_count
            measurement_count += len(operation["qubits"])
        elif name in ("DETECTOR", "OBSERVABLE"):
            indices = [measurement_count + offset for offset in operation["records"]]
            if any(index < 0 or index >= measurement_count for index in indices):
                raise ValueError("Invalid measurement reference")
            operation["record_mask"] = parity_mask(indices)
            if name == "DETECTOR":
                operation["detector"] = detector_count
                detector_count += 1
        result.append(operation)
    if measurement_count != case["num_measurements"]:
        raise ValueError("Measurement count mismatch")
    if detector_count != case["num_detectors"]:
        raise ValueError("Detector count mismatch")
    return result


def merge_probability(previous, probability):
    return previous * (1.0 - probability) + probability * (1.0 - previous)


def make_answer(case, terms):
    errors = []
    for signature, probability in sorted(terms.items()):
        detectors, observables = signature
        if probability == 0 or not (detectors or observables):
            continue
        errors.append({"detectors": list(detectors), "observables": list(observables),
                       "probability": float(probability)})
    return {"schema_version": 1, "num_detectors": case["num_detectors"],
            "num_observables": case["num_observables"], "errors": errors}


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, separators=(",", ":")) + "\n")
