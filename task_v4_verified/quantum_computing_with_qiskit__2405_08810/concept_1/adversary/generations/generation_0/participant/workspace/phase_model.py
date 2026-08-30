import math


def integer(value):
    return type(value) is int


def check(instance, response):
    if not isinstance(response, dict) or set(response) != {"ops"}:
        raise ValueError("expected exactly one ops member")
    operations = response["ops"]
    if not isinstance(operations, list) or len(operations) > 100000:
        raise ValueError("invalid operation list")
    size = instance["n"]
    edge_properties = {(control, target): (weight, duration) for control, target, weight, duration in instance["edges"]}
    rows = [1 << qubit for qubit in range(size)]
    ready = [0] * size
    terms_seen = set()
    error_cost = 0
    cx_count = 0
    for operation in operations:
        if not isinstance(operation, list) or len(operation) != 3:
            raise ValueError("operations must be triples")
        kind, first, second = operation
        if not integer(first) or not integer(second):
            raise ValueError("indices must be integers")
        if not 0 <= first < size:
            raise ValueError("qubit out of range")
        if kind == "cx":
            if (first, second) not in edge_properties:
                raise ValueError("non-native CX")
            rows[second] ^= rows[first]
            weight, duration = edge_properties[first, second]
            error_cost += weight
            cx_count += 1
            finish = max(ready[first], ready[second]) + duration
            ready[first] = finish
            ready[second] = finish
        elif kind == "rz":
            if not 0 <= second < len(instance["terms"]) or second in terms_seen:
                raise ValueError("missing, repeated, or unknown symbolic rotation")
            if rows[first] != instance["terms"][second]:
                raise ValueError("wrong parity at symbolic rotation")
            terms_seen.add(second)
        else:
            raise ValueError("unknown operation")
    if len(terms_seen) != len(instance["terms"]):
        raise ValueError("some symbolic rotations are absent")
    if rows != [1 << qubit for qubit in range(size)]:
        raise ValueError("final Boolean map is not identity")
    makespan = max(ready)
    cost = error_cost + 0.20 * makespan
    if not math.isfinite(cost) or cost <= 0:
        raise ValueError("invalid cost")
    return {"cost": cost, "error_weight": error_cost, "makespan": makespan, "cx_count": cx_count}
