import math


def block_cost(case, block):
    gates = case["gates"]
    qubits = set()
    kinds = set()
    for index in block:
        qubits.update(gates[index]["qubits"])
        kinds.add(gates[index]["kind"])
    width = len(qubits)
    specialized = len(kinds) == 1 and "dense" not in kinds
    arithmetic = 1 if specialized else 2 ** width
    hardware = case["hardware"]
    stride = 1 + hardware["stride_penalty"] * max(0, min(qubits) - hardware["cache_qubits"])
    update = hardware["launch"] + max(hardware["memory"] * stride, arithmetic * hardware["compute"])
    entries = 2 ** width if specialized else 4 ** width
    construction = hardware["build"] * max(0, len(block) - 1) * entries
    return case["repetitions"] * update + construction


def validate_and_cost(case, blocks):
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("schedule must be a nonempty list")
    gates = case["gates"]
    seen = set()
    last_by_qubit = {}
    previous_epoch = -1
    total = 0.0
    for block in blocks:
        if not isinstance(block, list) or not 1 <= len(block) <= case["max_block_operations"]:
            raise ValueError("invalid operation cap or empty block")
        qubits = set()
        epochs = set()
        for index in block:
            if type(index) is not int or not 0 <= index < len(gates) or index in seen:
                raise ValueError("gate index invalid or repeated")
            gate = gates[index]
            if gate["epoch"] < previous_epoch:
                raise ValueError("barrier order violated")
            previous_epoch = gate["epoch"]
            epochs.add(gate["epoch"])
            for qubit in gate["qubits"]:
                if last_by_qubit.get(qubit, -1) > index:
                    raise ValueError("per-qubit dependency violated")
                last_by_qubit[qubit] = index
            qubits.update(gate["qubits"])
            seen.add(index)
        if len(epochs) != 1 or len(qubits) > case["max_block_qubits"]:
            raise ValueError("block crosses barrier or support cap")
        total += block_cost(case, block)
    if len(seen) != len(gates):
        raise ValueError("missing gates")
    if not math.isfinite(total) or total <= 0:
        raise ValueError("nonfinite/nonpositive cost")
    return total


def predecessors(case):
    previous = {}
    result = []
    for index, gate in enumerate(case["gates"]):
        dependencies = set()
        for qubit in gate["qubits"]:
            if qubit in previous:
                dependencies.add(previous[qubit])
            previous[qubit] = index
        result.append(dependencies)
    return result
