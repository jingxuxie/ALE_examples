import json

MAX_BYTES = 64 * 1024 * 1024
PARSER_CAP = 100000


class Invalid(ValueError):
    pass


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Invalid("Duplicate JSON key")
        result[key] = value
    return result


def integer(text):
    if len(text) > 10:
        raise Invalid("Oversized integer")
    return int(text)


def no_float(text):
    raise Invalid("Only integer JSON numbers are permitted")


def load(raw):
    if len(raw) > MAX_BYTES:
        raise Invalid("Artifact exceeds 64 MiB")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys,
                      parse_int=integer, parse_float=no_float, parse_constant=no_float)


def fields(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise Invalid("Incorrect object fields")


def parse_pauli(text, width):
    if type(text) is not str or len(text) != width + 1 or text[0] not in "+-":
        raise Invalid("Invalid signed Pauli")
    x_mask = z_mask = 0
    for qubit, letter in enumerate(text[1:]):
        if letter not in "IXYZ":
            raise Invalid("Invalid Pauli alphabet")
        if letter in "XY":
            x_mask |= 1 << qubit
        if letter in "YZ":
            z_mask |= 1 << qubit
    return [x_mask, z_mask, int(text[0] == "-")]


def pauli_text(row, width):
    return ("-" if row[2] else "+") + "".join(
        "IXZY"[((row[0] >> qubit) & 1) + 2 * ((row[1] >> qubit) & 1)]
        for qubit in range(width))


def apply_gate(rows, gate, targets):
    first = 1 << targets[0]
    for row in rows:
        x_first = int(bool(row[0] & first))
        z_first = int(bool(row[1] & first))
        if gate == "H":
            row[2] ^= x_first & z_first
            if x_first != z_first:
                row[0] ^= first
                row[1] ^= first
        elif gate == "S":
            row[2] ^= x_first & z_first
            if x_first:
                row[1] ^= first
        elif gate == "CX":
            second = 1 << targets[1]
            x_second = int(bool(row[0] & second))
            z_second = int(bool(row[1] & second))
            row[2] ^= x_first & z_second & (x_second ^ z_first ^ 1)
            if x_first:
                row[0] ^= second
            if z_second:
                row[1] ^= first
        else:
            raise Invalid("Unknown gate")


def tableau(artifact):
    width = artifact["num_qubits"]
    rows = [[1 << qubit, 0, 0] for qubit in range(width)]
    rows.extend([0, 1 << qubit, 0] for qubit in range(width))
    for layer in artifact["layers"]:
        for operation in layer:
            apply_gate(rows, operation["gate"], operation["targets"])
    return rows


def metrics(artifact, constraints):
    fields(artifact, ["schema_version", "num_qubits", "layers"])
    if type(artifact["schema_version"]) is not int or artifact["schema_version"] != 1:
        raise Invalid("schema_version must be integer 1")
    width = constraints["num_qubits"]
    if type(artifact["num_qubits"]) is not int or artifact["num_qubits"] != width:
        raise Invalid("Incorrect qubit count")
    layers = artifact["layers"]
    if type(layers) is not list or len(layers) > PARSER_CAP:
        raise Invalid("Invalid layer list")
    edges = {tuple(sorted(edge)) for edge in constraints["edges"]}
    result = dict(gate_count=0, cx_count=0, entangling_depth=0, layer_count=len(layers))
    for layer in layers:
        if type(layer) is not list or not 0 < len(layer) <= width:
            raise Invalid("Each layer must be a nonempty list")
        used = set()
        has_cx = False
        for operation in layer:
            fields(operation, ["gate", "targets"])
            gate, targets = operation["gate"], operation["targets"]
            if type(gate) is not str or gate not in ("H", "S", "CX"):
                raise Invalid("Only H, S and CX are permitted")
            if type(targets) is not list or len(targets) != (2 if gate == "CX" else 1):
                raise Invalid("Wrong gate arity")
            if any(type(qubit) is not int or not 0 <= qubit < width for qubit in targets):
                raise Invalid("Qubit indices must be in-range integers")
            if len(set(targets)) != len(targets) or used.intersection(targets):
                raise Invalid("Layer qubits must be disjoint")
            used.update(targets)
            if gate == "CX":
                if tuple(sorted(targets)) not in edges:
                    raise Invalid("Non-native CX edge")
                result["cx_count"] += 1
                has_cx = True
            result["gate_count"] += 1
            if result["gate_count"] > PARSER_CAP:
                raise Invalid("Parser gate cap exceeded")
        result["entangling_depth"] += int(has_cx)
    return result


def check(artifact, instance):
    constraints, target = instance["constraints"], instance["target"]
    counts = metrics(artifact, constraints)
    width = constraints["num_qubits"]
    if len(target["x_outputs"]) != width or len(target["z_outputs"]) != width:
        raise Invalid("Incomplete trusted target")
    expected = [parse_pauli(text, width) for text in target["x_outputs"] + target["z_outputs"]]
    for first_index, first in enumerate(expected):
        for second_index in range(first_index + 1, len(expected)):
            second = expected[second_index]
            parity = ((first[0] & second[1]).bit_count() + (first[1] & second[0]).bit_count()) & 1
            if parity != int(first_index < width and second_index == first_index + width):
                raise Invalid("Trusted target is not symplectic")
    actual = tableau(artifact)
    mismatches = sum(left != right for left, right in zip(actual, expected))
    names = ("cx_count", "entangling_depth", "gate_count")
    violations = [name for name in names if counts[name] > constraints["budgets"]["max_" + name]]
    fraction = min([1.0] + [constraints["budgets"]["max_" + name] / max(1, counts[name]) for name in names])
    return dict(valid=not mismatches, semantic_valid=not mismatches, native_valid=True,
                passed=not mismatches and not violations, within_budgets=not violations,
                score=100 * fraction if not mismatches else 0.0, metrics=counts,
                mismatched_generators=mismatches, budget_violations=violations,
                reason="signed tableau mismatch" if mismatches else ("resource budgets exceeded" if violations else "accepted"))


def rejection(reason, kind="artifact"):
    return dict(valid=False, passed=False, score=0.0, reason=reason, error_kind=kind)
