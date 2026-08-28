import argparse

from protocol import bit_indices, lower_operations, make_answer, merge_probability
from protocol import read_json, write_json


def compile_case(case):
    trajectory = []
    faults = []
    for operation in lower_operations(case):
        if operation["op"] == "ERROR":
            if operation["probability"]:
                faults.append((len(trajectory), operation))
        elif operation["op"] != "TICK":
            trajectory.append(operation)
    terms = {}
    for location, fault in faults:
        x_frame = 0
        z_frame = 0
        for qubit, pauli in zip(fault["qubits"], fault["paulis"]):
            if pauli in ("X", "Y"):
                x_frame ^= 1 << qubit
            if pauli in ("Z", "Y"):
                z_frame ^= 1 << qubit
        record_flips = 0
        detector_flips = 0
        observable_flips = 0
        for operation_index in range(location, len(trajectory)):
            operation = trajectory[operation_index]
            name = operation["op"]
            if name == "H":
                for qubit in operation["qubits"]:
                    changed = ((x_frame ^ z_frame) >> qubit) & 1
                    x_frame ^= changed << qubit
                    z_frame ^= changed << qubit
            elif name in ("S", "S_DAG"):
                for qubit in operation["qubits"]:
                    z_frame ^= x_frame & (1 << qubit)
            elif name in ("CX", "CZ", "SWAP"):
                targets = operation["qubits"]
                for pair_index in range(0, len(targets), 2):
                    control, target = targets[pair_index:pair_index + 2]
                    if name == "CX":
                        x_frame ^= ((x_frame >> control) & 1) << target
                        z_frame ^= ((z_frame >> target) & 1) << control
                    elif name == "CZ":
                        z_frame ^= ((x_frame >> control) & 1) << target
                        z_frame ^= ((x_frame >> target) & 1) << control
                    else:
                        changed_x = ((x_frame >> control) ^ (x_frame >> target)) & 1
                        changed_z = ((z_frame >> control) ^ (z_frame >> target)) & 1
                        x_frame ^= (changed_x << control) | (changed_x << target)
                        z_frame ^= (changed_z << control) | (changed_z << target)
            elif name in ("R", "RX"):
                for qubit in operation["qubits"]:
                    x_frame &= ~(1 << qubit)
                    z_frame &= ~(1 << qubit)
            elif name in ("M", "MX"):
                frame = x_frame if name == "M" else z_frame
                for offset, qubit in enumerate(operation["qubits"]):
                    record_flips ^= ((frame >> qubit) & 1) << (operation["record_start"] + offset)
            elif name == "DETECTOR":
                parity = (record_flips & operation["record_mask"]).bit_count() & 1
                detector_flips ^= parity << operation["detector"]
            elif name == "OBSERVABLE":
                parity = (record_flips & operation["record_mask"]).bit_count() & 1
                observable_flips ^= parity << operation["index"]
            else:
                raise ValueError(f"Unsupported operation: {name}")
        if detector_flips or observable_flips:
            signature = (tuple(bit_indices(detector_flips)), tuple(bit_indices(observable_flips)))
            terms[signature] = merge_probability(terms.get(signature, 0.0), fault["probability"])
    return make_answer(case, terms)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    write_json(args.output, compile_case(read_json(args.input)))


if __name__ == "__main__":
    main()
