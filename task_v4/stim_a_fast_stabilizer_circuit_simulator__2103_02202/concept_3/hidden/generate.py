import hashlib
import json
import math
from pathlib import Path
import random
import secrets
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT.parent / "authoring" / "vendor"
sys.path.insert(0, str(VENDOR))
sys.path.insert(0, str(ROOT / "evaluator"))
import stim
from checker import check, metrics, pauli_text, tableau


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def operation(gate, *targets):
    return {"gate": gate, "targets": list(targets)}


def to_stim(artifact):
    result = stim.Circuit()
    for layer in artifact["layers"]:
        for item in layer:
            result.append(item["gate"], item["targets"])
    result.append("I", [artifact["num_qubits"] - 1])
    return result


def native_rows(artifact):
    native = stim.Tableau.from_circuit(to_stim(artifact))
    return [str(native.x_output(qubit)).replace("_", "I") for qubit in range(len(native))] + [
        str(native.z_output(qubit)).replace("_", "I") for qubit in range(len(native))]


def compact(seed):
    rng = random.Random(seed)
    layers = []
    choices = [(), ("H",), ("S",), ("H", "S"), ("S", "H"), ("H", "S", "H")]
    for round_index in range(17):
        rotations = [rng.choice(choices) for qubit in range(36)]
        for offset in range(3):
            layer = [operation(sequence[offset], qubit) for qubit, sequence in enumerate(rotations) if offset < len(sequence)]
            if layer:
                layers.append(layer)
        if round_index == 16:
            break
        orientation, parity = divmod(round_index % 4, 2)
        layer = []
        for row in range(6):
            for column in range(6):
                if orientation == 0 and column % 2 == parity and column < 5:
                    endpoints = [6 * row + column, 6 * row + column + 1]
                elif orientation == 1 and row % 2 == parity and row < 5:
                    endpoints = [6 * row + column, 6 * (row + 1) + column]
                else:
                    continue
                if rng.getrandbits(1):
                    endpoints.reverse()
                layer.append(operation("CX", *endpoints))
        layers.append(layer)
    return dict(schema_version=1, num_qubits=36, layers=layers)


def route(native):
    operations = []
    for instruction in native.to_circuit(method="elimination"):
        targets = [target.value for target in instruction.targets_copy()]
        if instruction.name in ("H", "S"):
            operations.extend(operation(instruction.name, target) for target in targets)
        elif instruction.name == "CX":
            for offset in range(0, len(targets), 2):
                control, target = targets[offset:offset + 2]
                path = [control]
                while path[-1] // 6 != target // 6:
                    path.append(path[-1] + (6 if path[-1] // 6 < target // 6 else -6))
                while path[-1] != target:
                    path.append(path[-1] + (1 if path[-1] < target else -1))
                swaps = list(zip(path[:-2], path[1:-1]))
                for first, second in swaps:
                    operations.extend([operation("CX", first, second), operation("CX", second, first), operation("CX", first, second)])
                operations.append(operation("CX", path[-2], path[-1]))
                for first, second in reversed(swaps):
                    operations.extend([operation("CX", first, second), operation("CX", second, first), operation("CX", first, second)])
        else:
            raise RuntimeError("Unexpected synthesis gate " + instruction.name)
    layers = []
    last_layer = [-1] * 36
    for item in operations:
        layer_index = 1 + max(last_layer[qubit] for qubit in item["targets"])
        while len(layers) <= layer_index:
            layers.append([])
        layers[layer_index].append(item)
        for qubit in item["targets"]:
            last_layer[qubit] = layer_index
    return dict(schema_version=1, num_qubits=36, layers=layers)


def main():
    if stim.__version__ != "1.15.0":
        raise RuntimeError("Requires the private Stim 1.15.0 vendor")
    if (ROOT / "status.json").exists():
        raise RuntimeError("Frozen target already exists; refusing regeneration")
    seed = secrets.randbits(256)
    witness = compact(seed)
    native = stim.Tableau.from_circuit(to_stim(witness))
    images = native_rows(witness)
    target = dict(schema_version=1, instance_id="grid36_clifford_v1", num_qubits=36,
                  convention="U P U_dagger; qubit index increases left to right",
                  x_outputs=images[:36], z_outputs=images[36:])
    edges = [[qubit, other] for qubit in range(36) for other in (qubit + 1, qubit + 6)
             if other < 36 and (other == qubit + 6 or qubit // 6 == other // 6)]
    constraints = dict(num_qubits=36, grid_shape=[6, 6], edges=edges, allowed_gates=["H", "S", "CX"])
    counts = metrics(witness, constraints)
    constraints["budgets"] = {"max_" + name: math.ceil(counts[name] * 1.4)
                              for name in ("cx_count", "entangling_depth", "gate_count")}
    constraints["artifact_max_bytes"] = 64 * 1024 * 1024
    instance = dict(target=target, constraints=constraints)
    baseline = route(native)
    for artifact in (witness, baseline):
        assert native_rows(artifact) == images
        assert [pauli_text(row, 36) for row in tableau(artifact)] == images
    witness_report, baseline_report = check(witness, instance), check(baseline, instance)
    assert witness_report["passed"]
    assert baseline_report["semantic_valid"] and not baseline_report["passed"]
    assert baseline_report["metrics"]["cx_count"] > 3 * constraints["budgets"]["max_cx_count"]
    save(ROOT / "evaluator" / "hidden" / "generation_secret.json", dict(seed_hex=hex(seed), stim_version=stim.__version__, native_depth=16))
    save(ROOT / "evaluator" / "hidden" / "witness" / "circuit.json", witness)
    save(ROOT / "evaluator" / "hidden" / "instance.json", instance)
    save(ROOT / "participant" / "input" / "target.json", target)
    save(ROOT / "participant" / "input" / "constraints.json", constraints)
    save(ROOT / "participant" / "baseline" / "circuit.json", baseline)
    save(ROOT / "participant" / "workspace" / "circuit.json", baseline)
    shutil.copyfile(ROOT / "evaluator" / "checker.py", ROOT / "participant" / "input" / "checker.py")
    gate_schema = {"type": "object", "additionalProperties": False, "required": ["gate", "targets"],
                   "properties": {"gate": {"enum": ["H", "S", "CX"]}, "targets": {
                       "type": "array", "minItems": 1, "maxItems": 2, "uniqueItems": True,
                       "items": {"type": "integer", "minimum": 0, "maximum": 35}}},
                   "allOf": [{"if": {"properties": {"gate": {"const": "CX"}}},
                              "then": {"properties": {"targets": {"minItems": 2}}},
                              "else": {"properties": {"targets": {"maxItems": 1}}}}]}
    save(ROOT / "participant" / "input" / "circuit.schema.json", {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "additionalProperties": False,
        "required": ["schema_version", "num_qubits", "layers"], "properties": {
            "schema_version": {"type": "integer", "const": 1}, "num_qubits": {"type": "integer", "const": 36},
            "layers": {"type": "array", "maxItems": 100000, "items": {
                "type": "array", "minItems": 1, "maxItems": 36, "items": gate_schema}}}})
    for directory in ("attempts", "champions", "adversary"):
        (ROOT / directory).mkdir(exist_ok=True)
    shutil.copyfile(ROOT.parent / "DISCOVERY.md", ROOT / "adversary" / "concept_research.md")
    for path in (ROOT / "hidden").rglob("*"):
        path.chmod(0o700 if path.is_dir() else 0o600)
    (ROOT / "hidden").chmod(0o700)
    for path in (ROOT / "evaluator" / "hidden").rglob("*"):
        path.chmod(0o700 if path.is_dir() else 0o600)
    (ROOT / "evaluator" / "hidden").chmod(0o700)
    save(ROOT / "hidden" / "authoring_validation.json", dict(witness=witness_report, baseline=baseline_report,
                                                               independent_python_matches_stim=True))
    hashes = {str(path.relative_to(ROOT / "participant")): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted((ROOT / "participant").rglob("*")) if path.is_file()}
    save(ROOT / "adversary" / "public_manifest.json", hashes)
    save(ROOT / "status.json", dict(concept="Graph-constrained exact Clifford design", verification_mode="C",
         status="generated_pending_selftests", target_frozen=True, num_qubits=36, fresh_agent_tested=False,
         private_stim_version="1.15.0", budgets=constraints["budgets"], baseline=baseline_report, private_witness=witness_report,
         solvability="private compact native witness; independent Python and Stim agree",
         empirical_hardness="not tested; synthesis difficulty is a generation-time hypothesis"))
    print(json.dumps(dict(witness=witness_report, baseline=baseline_report, budgets=constraints["budgets"]), indent=2))


if __name__ == "__main__":
    main()
