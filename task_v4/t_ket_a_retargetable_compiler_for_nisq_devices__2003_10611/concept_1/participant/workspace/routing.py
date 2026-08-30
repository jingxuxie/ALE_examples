import math


def validate(instance, answer):
    count = instance["n"]
    if not isinstance(answer, dict) or not isinstance(answer.get("operations"), list):
        raise ValueError("output needs an operations list")
    operations = answer["operations"]
    if len(operations) > 30000:
        raise ValueError("too many operations")
    edges = {tuple(sorted((first, second))): weight for first, second, weight in instance["edges"]}
    positions = instance["initial"][:]
    occupants = [0] * count
    for logical, physical in enumerate(positions):
        occupants[physical] = logical
    gates = instance["gates"]
    wire_gates = [[] for _ in range(count)]
    for gate_index, (first, second) in enumerate(gates):
        wire_gates[first].append(gate_index)
        wire_gates[second].append(gate_index)
    cursors = [0] * count
    depths = [0] * count
    seen = set()
    work = 0.0
    swaps = 0
    for operation in operations:
        if not isinstance(operation, list) or not operation:
            raise ValueError("malformed operation")
        if operation[0] == "gate":
            if len(operation) != 2 or type(operation[1]) is not int:
                raise ValueError("malformed gate")
            gate_index = operation[1]
            if not 0 <= gate_index < len(gates) or gate_index in seen:
                raise ValueError("duplicate or out-of-range gate")
            logical_first, logical_second = gates[gate_index]
            for logical in (logical_first, logical_second):
                if cursors[logical] >= len(wire_gates[logical]) or wire_gates[logical][cursors[logical]] != gate_index:
                    raise ValueError("logical dependency violation")
                cursors[logical] += 1
            first, second = positions[logical_first], positions[logical_second]
            duration = 1
            seen.add(gate_index)
        elif operation[0] == "swap":
            if len(operation) != 3 or any(type(value) is not int for value in operation[1:]):
                raise ValueError("malformed swap")
            first, second = operation[1:]
            if not 0 <= first < count or not 0 <= second < count or first == second:
                raise ValueError("invalid physical swap operands")
            duration = 3
            swaps += 1
        else:
            raise ValueError("unknown operation")
        edge = tuple(sorted((first, second)))
        if edge not in edges:
            raise ValueError("operation violates architecture")
        work += duration * edges[edge]
        finish = max(depths[first], depths[second]) + duration
        depths[first] = finish
        depths[second] = finish
        if operation[0] == "swap":
            occupants[first], occupants[second] = occupants[second], occupants[first]
            positions[occupants[first]] = first
            positions[occupants[second]] = second
    if len(seen) != len(gates):
        raise ValueError("missing logical gates")
    cost = work + 0.05 * max(depths)
    if not math.isfinite(cost) or cost <= 0:
        raise ValueError("invalid cost")
    return {"cost": cost, "calibrated_work": work, "depth": max(depths), "swaps": swaps,
            "final": positions, "valid": True}
