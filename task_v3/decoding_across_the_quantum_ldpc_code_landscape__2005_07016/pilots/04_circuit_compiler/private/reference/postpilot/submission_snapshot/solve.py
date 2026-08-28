import argparse
from bisect import bisect_left
import gc
import json


def prepare_operations(operations):
    result = []
    stack = [(iter(operations), result)]
    while stack:
        iterator, destination = stack[-1]
        operation = next(iterator, None)
        if operation is None:
            stack.pop()
            continue
        name = operation["op"]
        if name == "ERROR":
            probability = float(operation["probability"])
            if not probability:
                continue
            targets = []
            for qubit, pauli in zip(operation["qubits"], operation["paulis"]):
                if pauli == "X":
                    targets.append(2 * qubit)
                elif pauli == "Z":
                    targets.append(2 * qubit + 1)
                elif pauli == "Y":
                    targets.extend((2 * qubit, 2 * qubit + 1))
                elif pauli != "I":
                    raise ValueError("Unsupported Pauli: " + pauli)
            if targets:
                destination.append((0, probability, targets))
        elif name == "CX" or name == "CZ":
            qubits = operation["qubits"]
            pairs = []
            for position in range(len(qubits) - 2, -1, -2):
                control = 2 * qubits[position]
                target = 2 * qubits[position + 1]
                if name == "CX":
                    pairs.extend(((control, target), (target + 1, control + 1)))
                else:
                    pairs.extend(((control, target + 1), (target, control + 1)))
            destination.append((1, pairs))
        elif name == "S" or name == "S_DAG":
            destination.append((1, [(2 * qubit, 2 * qubit + 1) for qubit in operation["qubits"]]))
        elif name == "M" or name == "MX":
            basis = int(name == "MX")
            destination.append((2, [2 * qubit + basis for qubit in operation["qubits"]]))
        elif name == "DETECTOR":
            destination.append((3, operation["records"]))
        elif name == "OBSERVABLE":
            destination.append((4, operation["index"], operation["records"]))
        elif name == "R" or name == "RX":
            destination.append((5, [2 * qubit for qubit in operation["qubits"]]))
        elif name == "H":
            destination.append((6, [(2 * qubit, 2 * qubit + 1) for qubit in operation["qubits"]]))
        elif name == "SWAP":
            qubits = operation["qubits"]
            pairs = []
            for position in range(len(qubits) - 2, -1, -2):
                first = 2 * qubits[position]
                second = 2 * qubits[position + 1]
                pairs.extend(((first, second), (first + 1, second + 1)))
            destination.append((6, pairs))
        elif name == "REPEAT":
            if operation["count"] > 0 and operation["body"]:
                nested = []
                destination.append((7, operation["count"], nested))
                stack.append((iter(operation["body"]), nested))
        elif name != "TICK":
            raise ValueError("Unsupported operation: " + name)
    return result


def reverse_instructions(operations):
    stack = [(operations, len(operations) - 1, 1)]
    while stack:
        body, position, repetitions = stack.pop()
        while True:
            if position < 0:
                repetitions -= 1
                if repetitions == 0:
                    break
                position = len(body) - 1
            operation = body[position]
            position -= 1
            if operation[0] == 7:
                count = operation[1]
                nested = operation[2]
                if count > 0 and nested:
                    stack.append((body, position, repetitions))
                    body = nested
                    position = len(body) - 1
                    repetitions = count
            else:
                yield operation


def compile_terms(case, instructions):
    num_detectors = case["num_detectors"]
    num_observables = case["num_observables"]
    measurement_count = case["num_measurements"]
    detector_count = num_detectors
    effects = [set() for _ in range(2 * case["num_qubits"])]
    pending_records = {}
    terms = {}
    for operation in reverse_instructions(instructions):
        name = operation[0]
        if name == 0:
            probability = operation[1]
            targets = operation[2]
            if len(targets) == 1:
                signature = effects[targets[0]]
            elif len(targets) == 2:
                signature = effects[targets[0]] ^ effects[targets[1]]
            else:
                signature = set()
                for target in targets:
                    signature ^= effects[target]
            if signature:
                key = tuple(sorted(signature))
                previous = terms.get(key)
                if previous is None:
                    terms[key] = probability
                else:
                    terms[key] = previous * (1.0 - probability) + probability * (1.0 - previous)
        elif name == 1:
            for target, source in operation[1]:
                effects[target] ^= effects[source]
        elif name == 2:
            targets = operation[1]
            measurement_count -= len(targets)
            for offset, target in enumerate(targets):
                signature = pending_records.pop(measurement_count + offset, None)
                if signature:
                    effects[target] ^= signature
        elif name == 3 or name == 4:
            if name == 3:
                detector_count -= 1
                label = detector_count
                records = operation[1]
            else:
                observable = operation[1]
                if observable < 0 or observable >= num_observables:
                    raise ValueError("Invalid observable index")
                label = num_detectors + observable
                records = operation[2]
            for offset in records:
                record = measurement_count + offset
                if record < 0 or record >= measurement_count:
                    raise ValueError("Invalid measurement reference")
                signature = pending_records.get(record)
                if signature is None:
                    pending_records[record] = {label}
                elif label in signature:
                    signature.remove(label)
                else:
                    signature.add(label)
        elif name == 5:
            for target in operation[1]:
                effects[target].clear()
                effects[target + 1].clear()
        else:
            for first, second in operation[1]:
                effects[first], effects[second] = effects[second], effects[first]
    if measurement_count != 0:
        raise ValueError("Measurement count mismatch")
    if detector_count != 0:
        raise ValueError("Detector count mismatch")
    return terms


def make_answer(case, terms):
    num_detectors = case["num_detectors"]
    errors = []
    for signature, probability in terms.items():
        if probability == 0:
            continue
        detectors = []
        observables = []
        for label in signature:
            if label < num_detectors:
                detectors.append(label)
            else:
                observables.append(label - num_detectors)
        errors.append({"detectors": detectors, "observables": observables,
                       "probability": probability})
    return {"schema_version": 1, "num_detectors": num_detectors,
            "num_observables": case["num_observables"], "errors": errors}


def compile_case(case):
    return make_answer(case, compile_terms(case, prepare_operations(case["operations"])))


def write_answer(destination, case, terms):
    num_detectors = case["num_detectors"]
    num_observables = case["num_observables"]
    destination.write(f'{{"schema_version":1,"num_detectors":{num_detectors},'
                      f'"num_observables":{num_observables},"errors":[')
    batch = []
    probability_strings = {}
    separator = ""
    for signature, probability in terms.items():
        if probability == 0:
            continue
        boundary = bisect_left(signature, num_detectors)
        detectors = list(signature[:boundary])
        observables = [label - num_detectors for label in signature[boundary:]]
        probability_text = probability_strings.get(probability)
        if probability_text is None:
            probability_text = str(probability)
            if len(probability_strings) < 1024:
                probability_strings[probability] = probability_text
        batch.append(f'{{"detectors":{detectors},"observables":{observables},'
                     f'"probability":{probability_text}}}')
        if len(batch) == 4096:
            destination.write(separator + ",".join(batch))
            separator = ","
            batch.clear()
    if batch:
        destination.write(separator + ",".join(batch))
    destination.write("]}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    gc.disable()
    with open(arguments.input, encoding="utf-8") as source:
        case = json.load(source)
    instructions = prepare_operations(case.pop("operations"))
    terms = compile_terms(case, instructions)
    del instructions
    with open(arguments.output, "w", encoding="utf-8") as destination:
        write_answer(destination, case, terms)


if __name__ == "__main__":
    main()
