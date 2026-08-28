import argparse
from pathlib import Path
import sys
import time

from bootstrap import enable_vendor

VENDOR = enable_vendor()
import stim

PUBLIC = Path(__file__).resolve().parents[2] / "participant/workspace"
sys.path.insert(0, str(PUBLIC))
from protocol import make_answer, merge_probability, read_json, write_json


def to_stim(operations):
    circuit = stim.Circuit()
    pauli_target = {"X": stim.target_x, "Y": stim.target_y, "Z": stim.target_z}
    for operation in operations:
        name = operation["op"]
        if name == "REPEAT":
            circuit.append(stim.CircuitRepeatBlock(operation["count"], to_stim(operation["body"])))
        elif name == "ERROR":
            targets = [pauli_target[pauli](qubit) for qubit, pauli in
                       zip(operation["qubits"], operation["paulis"])]
            circuit.append("CORRELATED_ERROR", targets, operation["probability"])
        elif name in ("DETECTOR", "OBSERVABLE"):
            targets = [stim.target_rec(offset) for offset in operation["records"]]
            if name == "DETECTOR":
                circuit.append(name, targets)
            else:
                circuit.append("OBSERVABLE_INCLUDE", targets, operation["index"])
        elif name == "TICK":
            circuit.append("TICK")
        else:
            circuit.append(name, operation["qubits"])
    return circuit


def compile_case(case):
    if stim.__version__ != "1.16.0":
        raise RuntimeError(f"Expected Stim 1.16.0, found {stim.__version__}")
    conversion_start = time.perf_counter()
    circuit = to_stim(case["operations"])
    if (circuit.num_detectors, circuit.num_observables, circuit.num_measurements) != (
            case["num_detectors"], case["num_observables"], case["num_measurements"]):
        raise ValueError("Circuit metadata mismatch")
    compiler_start = time.perf_counter()
    model = circuit.detector_error_model(decompose_errors=False, flatten_loops=True,
                                        allow_gauge_detectors=False, approximate_disjoint_errors=False)
    compiler_stop = time.perf_counter()
    terms = {}
    for instruction in model.flattened():
        if instruction.type != "error":
            continue
        detectors = set()
        observables = set()
        for target in instruction.targets_copy():
            if target.is_relative_detector_id():
                detectors.symmetric_difference_update([target.val])
            elif target.is_logical_observable_id():
                observables.symmetric_difference_update([target.val])
            else:
                raise ValueError("Unexpected decomposition separator")
        signature = tuple(sorted(detectors)), tuple(sorted(observables))
        if any(signature):
            terms[signature] = merge_probability(terms.get(signature, 0.0), instruction.args_copy()[0])
    answer = make_answer(case, terms)
    metrics = {"stim_version": stim.__version__, "conversion_seconds": compiler_start - conversion_start,
               "compiler_seconds": compiler_stop - compiler_start,
               "canonicalization_seconds": time.perf_counter() - compiler_stop,
               "terms": len(answer["errors"])}
    return answer, metrics, circuit, model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metrics")
    args = parser.parse_args()
    answer, metrics, circuit, model = compile_case(read_json(args.input))
    write_json(args.output, answer)
    if args.metrics:
        write_json(args.metrics, metrics)


if __name__ == "__main__":
    main()
