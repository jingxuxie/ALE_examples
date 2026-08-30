import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
CONCEPT = ROOT / "concept_2"
PUBLIC = CONCEPT / "participant"
sys.path[:0] = [str(ROOT / "authoring" / "deps"), str(ROOT / "authoring" / "upstream" / "src"), str(PUBLIC / "workspace")]
os.environ["OPENBLAS_NUM_THREADS"] = "1"
import stim
from honeycomb_layout import HoneycombLayout
from design_common import aggregate, ambiguity, generate_supports, load_case, score_case, selected_columns


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def binary_rank(values):
    pivots = {}
    for value in values:
        while value:
            pivot = value.bit_length()
            if pivot not in pivots:
                pivots[pivot] = value
                break
            value ^= pivots[pivot]
    return len(pivots)


def pauli_bits(pauli):
    result = 0
    for qubit, value in enumerate(pauli):
        if value in (1, 2):
            result ^= 1 << (2 * qubit)
        if value in (2, 3):
            result ^= 2 << (2 * qubit)
    return result


def record_relations(circuit):
    pivots = {}
    relations = []
    for flow in circuit.flow_generators():
        boundary = pauli_bits(flow.input_copy()) | (pauli_bits(flow.output_copy()) << (2 * circuit.num_qubits))
        record = 0
        for index in flow.measurements_copy():
            record ^= 1 << index
        while boundary:
            pivot = boundary.bit_length()
            if pivot not in pivots:
                pivots[pivot] = boundary, record
                break
            other_boundary, other_record = pivots[pivot]
            boundary ^= other_boundary
            record ^= other_record
        if not boundary and record:
            relations.append(record)
    if binary_rank(relations) != len(relations):
        raise ValueError("dependent relation generators")
    return relations


def record_targets(bits, total):
    targets = []
    while bits:
        lowest = bits & -bits
        targets.append(stim.target_rec(lowest.bit_length() - 1 - total))
        bits ^= lowest
    return targets


def logicals(layout, phase):
    result = []
    for offset in (0, 3):
        for direction in ("h", "v"):
            basis, qubits = getattr(layout, "obs_" + direction + "_before_sub_round")(phase + offset)
            pauli = stim.PauliString(layout.num_qubits + 2)
            for coordinate in qubits:
                pauli[layout.q2i[coordinate]] = basis
            result.append(pauli)
    for left in range(4):
        for right in range(4):
            expected = left // 2 != right // 2 or left == right
            if result[left].commutes(result[right]) != expected:
                raise ValueError("logical symplectic pairing invalid")
    return result


def append_product(circuit, pauli):
    targets = []
    for qubit, value in enumerate(pauli):
        if value:
            if targets:
                targets.append(stim.target_combiner())
            targets.append((stim.target_x, stim.target_y, stim.target_z)[value - 1](qubit))
    circuit.append("MPP", targets)


def append_caps(circuit, layout, phase):
    for logical_index, pauli in enumerate(logicals(layout, phase)):
        pauli[layout.num_qubits + logical_index // 2] = "XZ"[logical_index % 2]
        append_product(circuit, pauli)


def make_case(scale, noisy_rounds):
    started = time.monotonic()
    layout = HoneycombLayout(data_width=4 * scale, data_height=6 * scale, sub_rounds=12 + noisy_rounds, style="EM3", obs="H", noise=0)
    cell = HoneycombLayout(data_width=4, data_height=6, sub_rounds=12, style="EM3", obs="H", noise=0)
    coordinates = sorted(layout.data_qubit_coords, key=lambda coordinate: layout.q2i[coordinate])
    cell_coordinates = sorted(cell.data_qubit_coords, key=lambda coordinate: cell.q2i[coordinate])
    cell_lookup = {(int(coordinate.real), int(coordinate.imag)): index for index, coordinate in enumerate(cell_coordinates)}
    cell_ids = [cell_lookup[(int(coordinate.real) % cell.coord_width, int(coordinate.imag) % cell.coord_height)] for coordinate in coordinates]
    memory = stim.Circuit()
    observable_records = [0] * 4
    fault_instructions = {}
    slot_count = len(coordinates) * noisy_rounds
    total_rounds = noisy_rounds + 12
    mixed_stabilizers = []
    phase_ranks = []
    for subround in range(total_rounds):
        edges = layout.round_edges(subround)
        basis = layout.sub_round_edge_basis(subround)
        paths = (set(layout.obs_h_edges), set(layout.obs_v_edges))
        for edge in edges:
            pauli = stim.PauliString(layout.num_qubits + 2)
            pauli[layout.q2i[edge.left]] = basis
            pauli[layout.q2i[edge.right]] = basis
            record_index = memory.num_measurements
            append_product(memory, pauli)
            for logical_index in range(4):
                if edge in paths[logical_index % 2]:
                    observable_records[logical_index] ^= 1 << record_index
            anticommuting = [index for index, stabilizer in enumerate(mixed_stabilizers) if not stabilizer.commutes(pauli)]
            if anticommuting:
                pivot = anticommuting[0]
                old = mixed_stabilizers[pivot]
                for index in anticommuting[1:]:
                    mixed_stabilizers[index] *= old
                mixed_stabilizers[pivot] = pauli
            elif binary_rank([pauli_bits(stabilizer) for stabilizer in mixed_stabilizers] + [pauli_bits(pauli)]) > len(mixed_stabilizers):
                mixed_stabilizers.append(pauli)
        if subround >= 5:
            if len(mixed_stabilizers) != len(coordinates) - 2:
                raise ValueError("steady code does not encode exactly two qubits")
            if any(not logical.commutes(stabilizer) for logical in logicals(layout, subround + 1) for stabilizer in mixed_stabilizers):
                raise ValueError("logical does not centralize steady code")
            phase_ranks.append(len(mixed_stabilizers))
        if 6 <= subround < 6 + noisy_rounds:
            for axis, name in enumerate("XYZ"):
                instruction_index = len(memory)
                memory.append(name + "_ERROR", [layout.q2i[coordinate] for coordinate in coordinates], 0.001, tag=f"phase_{subround}_{name}")
                fault_instructions[instruction_index] = (subround - 6, axis)
        memory.append("TICK")
    noiseless_memory = memory.without_noise()
    for logical_index, (before, after) in enumerate(zip(logicals(layout, 0), logicals(layout, total_rounds))):
        records = [target.value + memory.num_measurements for target in record_targets(observable_records[logical_index], memory.num_measurements)]
        flow = stim.Flow(input=before, output=after, measurements=records)
        if not noiseless_memory.has_flow(flow, unsigned=True):
            raise ValueError("Stim rejects logical transport")
    relations = record_relations(noiseless_memory)
    circuit = stim.Circuit()
    append_caps(circuit, layout, 0)
    circuit.append("TICK")
    prefix_instruction_count = len(circuit)
    prefix_measurements = circuit.num_measurements
    circuit += memory
    append_caps(circuit, layout, total_rounds)
    all_relations = record_relations(circuit.without_noise())
    detector_records = [relation << prefix_measurements for relation in relations]
    logical_records = [(1 << index) ^ (observable_records[index] << prefix_measurements) ^ (1 << (prefix_measurements + memory.num_measurements + index)) for index in range(4)]
    if binary_rank(detector_records + logical_records) != len(relations) + 4:
        raise ValueError("four independent logical correlations missing")
    if binary_rank(all_relations + detector_records + logical_records) != len(all_relations) or len(all_relations) != len(relations) + 4:
        raise ValueError("detector/logical relation basis incomplete")
    for record in detector_records:
        circuit.append("DETECTOR", record_targets(record, circuit.num_measurements))
    for index, record in enumerate(logical_records):
        circuit.append("OBSERVABLE_INCLUDE", record_targets(record, circuit.num_measurements), index)
    circuit.without_noise().detector_error_model()
    if circuit.without_noise().compile_detector_sampler(seed=571).sample(32, append_observables=True).any():
        raise ValueError("noiseless EPR circuit not deterministic")
    columns = [[0, 0, 0] for _ in range(slot_count)]
    located = set()
    for explanation in circuit.explain_detector_error_model_errors():
        signature = 0
        for target in explanation.dem_error_terms:
            target = target.dem_target
            if target.is_relative_detector_id():
                signature ^= 1 << (target.val + 4)
            elif target.is_logical_observable_id():
                signature ^= 1 << target.val
            else:
                raise ValueError("unexpected decomposed detector target")
        for location in explanation.circuit_error_locations:
            if len(location.stack_frames) != 1 or len(location.flipped_pauli_product) != 1:
                raise ValueError("unexpected fault location")
            instruction_index = location.stack_frames[0].instruction_offset - prefix_instruction_count
            subround, axis = fault_instructions[instruction_index]
            qubit = location.flipped_pauli_product[0].gate_target.value
            if qubit >= len(coordinates):
                raise ValueError("fault on a reference")
            slot = subround * len(coordinates) + qubit
            key = slot, axis
            if key in located and columns[slot][axis] != signature:
                raise ValueError("ambiguous fault index")
            located.add(key)
            columns[slot][axis] = signature
    if any(triple[0] ^ triple[1] ^ triple[2] for triple in columns):
        raise ValueError("Pauli linearity check failed")
    verification = {"stim_version": stim.__version__, "logical_flows": 4, "logical_correlation_rank": 4, "steady_stabilizer_rank": phase_ranks[0], "complete_record_relation_rank": len(all_relations), "detector_rank": len(relations), "fault_columns": slot_count * 3, "nonzero_located_columns": len(located)}
    result = {"id": f"scale_{scale}", "scale": scale, "noisy_subrounds": noisy_rounds, "coordinate_period": [layout.coord_width, layout.coord_height], "cell_coordinates": [[int(coordinate.real), int(coordinate.imag)] for coordinate in cell_coordinates], "data_coordinates": [[int(coordinate.real), int(coordinate.imag)] for coordinate in coordinates], "slot_cells": cell_ids * noisy_rounds, "columns": [[format(value, "x") for value in triple] for triple in columns], "verification": verification}
    destination = PUBLIC / "input" / (result["id"] + ".json.gz")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(gzip.compress(json.dumps(result, separators=(",", ":")).encode(), mtime=0))
    circuit.to_file(PUBLIC / "input" / (result["id"] + ".stim"))
    save_json(CONCEPT / "evaluator" / "hidden" / (result["id"] + "_verification.json"), verification)
    print("built", result["id"], verification, "seconds", round(time.monotonic() - started, 2), flush=True)
    return load_case(destination)


def search(cases, records, trials, seed):
    generator = random.Random(seed)
    best = [2] * 24
    def objective(axes):
        fractions = []
        for case in cases:
            values = score_case(case, records[case["id"]], axes, False)
            fractions.extend(value["fraction"] for value in values.values())
        return sum(fractions) / len(fractions)
    best_score = objective(best)
    print("search baseline", best_score, flush=True)
    for trial in range(trials):
        if trial < trials // 3 or trial % 17 == 0:
            candidate = [generator.randrange(3) for _ in range(24)]
        else:
            candidate = best.copy()
            for position in generator.sample(range(24), generator.choice([1, 2, 3, 5])):
                candidate[position] = generator.randrange(3)
        candidate_score = objective(candidate)
        if candidate_score > best_score:
            best, best_score = candidate, candidate_score
            print("search improvement", trial, best_score, best, flush=True)
    return best, best_score


def validate_replay(case):
    circuit = stim.Circuit.from_file(PUBLIC / "input" / (case["id"] + ".stim"))
    locations = {}
    for instruction_index, instruction in enumerate(circuit):
        if instruction.name in ("X_ERROR", "Y_ERROR", "Z_ERROR"):
            _, subround, name = instruction.tag.split("_")
            locations[instruction_index] = int(subround) - 6, "XYZ".index(name)
    qubit_count = len(case["data_coordinates"])
    generator = random.Random(7324 + case["scale"])
    selections = [[(slot, axis)] for slot in (0, qubit_count - 1, len(case["columns"]) - 1) for axis in range(3)]
    selections += [[(generator.randrange(len(case["columns"])), generator.randrange(3))] for _ in range(39)]
    for logical_index in range(4):
        selection = next(((slot, axis) for slot, triple in enumerate(case["columns"]) for axis, value in enumerate(triple) if value & (1 << logical_index)), None)
        if selection is None:
            raise ValueError("one logical has no physical-fault response")
        selections.append([selection])
    selections += [[(generator.randrange(len(case["columns"])), generator.randrange(3)) for _ in range(7)] for _ in range(16)]
    for selection in selections:
        selected = set()
        expected = 0
        for key in selection:
            if key in selected:
                selected.remove(key)
            else:
                selected.add(key)
            expected ^= case["columns"][key[0]][key[1]]
        injected = stim.Circuit()
        for instruction_index, instruction in enumerate(circuit):
            if instruction_index not in locations:
                injected.append(instruction)
                continue
            subround, axis = locations[instruction_index]
            targets = [slot % qubit_count for slot, selected_axis in selected if slot // qubit_count == subround and selected_axis == axis]
            if targets:
                injected.append("XYZ"[axis] + "_ERROR", targets, 1)
        samples = injected.compile_detector_sampler(seed=1294).sample(4, append_observables=True)
        for sample in samples:
            signature = sum(int(bit) << (index + 4) for index, bit in enumerate(sample[:circuit.num_detectors]))
            signature |= sum(int(bit) << index for index, bit in enumerate(sample[circuit.num_detectors:]))
            if signature != expected:
                raise ValueError("fault-index replay mismatch")
    first_detector = next(index for index, instruction in enumerate(circuit) if instruction.name == "DETECTOR")
    memory = circuit[2:first_detector - 1].without_noise()
    layout = HoneycombLayout(data_width=4 * case["scale"], data_height=6 * case["scale"], sub_rounds=12 + case["noisy_subrounds"], style="EM3", obs="H", noise=0)
    for instruction in circuit:
        if instruction.name != "OBSERVABLE_INCLUDE":
            continue
        logical_index = int(instruction.gate_args_copy()[0])
        records = [target.value + circuit.num_measurements - 4 for target in instruction.targets_copy()]
        records = [index for index in records if 0 <= index < memory.num_measurements]
        before = logicals(layout, 0)[logical_index]
        after = logicals(layout, layout.sub_rounds)[logical_index]
        flow = stim.Flow(input=before, output=after, measurements=records)
        wrong_sign = stim.Flow(input=-before, output=after, measurements=records)
        if not memory.has_flow(flow, unsigned=False) or memory.has_flow(wrong_sign, unsigned=False):
            raise ValueError("signed logical-transport check failed")
    return {"case": case["id"], "single_fault_checks": 52, "multi_fault_checks": 16, "shots_each": 4, "signed_logical_checks": 4, "deliberate_wrong_sign_rejections": 4, "all_four_logical_bits_replayed": True, "passed": True}


def freeze_target(target, floor):
    protocol_path = CONCEPT / "evaluator" / "protocol.json"
    if protocol_path.exists():
        raise ValueError("objective is already frozen; refusing to overwrite")
    calibration = json.loads((CONCEPT / "champions" / "calibration.json").read_text())
    champion = calibration["generator_only"]
    if champion["correctness_fraction"] < target or champion["worst_group_fraction"] < floor:
        raise ValueError("generator construction does not meet proposed target")
    family = json.loads((PUBLIC / "input" / "family.json").read_text())
    evaluator = CONCEPT / "evaluator"
    for identifier in family["cases"]:
        path = PUBLIC / "input" / (identifier + ".json.gz")
        path.write_bytes(gzip.compress(gzip.decompress(path.read_bytes()), mtime=0))
        shutil.copyfile(path, evaluator / "hidden" / path.name)
    shutil.copyfile(PUBLIC / "workspace" / "design_common.py", evaluator / "design_common.py")
    hashes = {str(path.relative_to(evaluator)): hashlib.sha256(path.read_bytes()).hexdigest() for path in [evaluator / "design_common.py", evaluator / "evaluate.py", evaluator / "hidden" / "supports.json"] + [evaluator / "hidden" / (identifier + ".json.gz") for identifier in family["cases"]]}
    protocol = {"mode": "C", "metric": "exact_all_four_logicals_correctability_fraction", "target_fraction": target, "group_floors": {identifier: floor for identifier in champion["groups"]}, "baseline_fraction": calibration["baseline"]["correctness_fraction"], "cases": family["cases"], "supports_per_group": 256, "fixed_before_first_attempt": True, "fresh_agent_attempts": 0, "sha256": hashes}
    save_json(protocol_path, protocol)
    save_json(PUBLIC / "input" / "objective.json", {key: protocol[key] for key in ["mode", "metric", "target_fraction", "group_floors", "baseline_fraction", "supports_per_group", "fixed_before_first_attempt"]})
    save_json(CONCEPT / "status.json", {"readiness": "ready", "mode": "C", "status": "generator_verified", "fresh_agent_status": "not_run", "fresh_agent_attempts": 0, "fixed_before_first_attempt": True, "target_fraction": target, "group_floor": floor, "baseline_fraction": calibration["baseline"]["correctness_fraction"], "generator_fraction": champion["correctness_fraction"], "generator_worst_group": champion["worst_group_fraction"], "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(), "participant_dependencies": "Python standard library only"})
    save_json(CONCEPT / "attempts" / "status.json", {"fresh_attempts": 0, "status": "not_run", "objective_frozen": True})
    print(json.dumps(protocol, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--trials", type=int, default=120)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--freeze-target", type=float)
    parser.add_argument("--group-floor", type=float, default=0.60)
    arguments = parser.parse_args()
    if arguments.freeze_target is not None:
        freeze_target(arguments.freeze_target, arguments.group_floor)
        return
    if (CONCEPT / "evaluator" / "protocol.json").exists():
        raise ValueError("objective frozen; refusing to regenerate evaluation assets")
    for directory in ["attempts", "champions", "adversary", "evaluator/hidden", "participant/baseline", "participant/workspace", "participant/input"]:
        (CONCEPT / directory).mkdir(parents=True, exist_ok=True)
    cases = []
    for scale in (1, 2, 3):
        path = PUBLIC / "input" / f"scale_{scale}.json.gz"
        cases.append(make_case(scale, 6) if arguments.rebuild or not path.exists() else load_case(path))
    if arguments.verify:
        save_json(CONCEPT / "adversary" / "fault_replay.json", [validate_replay(case) for case in cases])
    densities = {"iid": [0.12, 0.16, 0.20], "stripe": [0.02, 0.04, 0.06], "burst": [0.00, 0.02, 0.04]}
    public_records = {case["id"]: generate_supports(case, 12423 + case["scale"] * 37, 48, densities) for case in cases}
    search_records = {case["id"]: generate_supports(case, 80912 + case["scale"] * 71, 36, densities) for case in cases}
    hidden_records = {case["id"]: generate_supports(case, 918341 + case["scale"] * 103, 256, densities) for case in cases}
    save_json(PUBLIC / "input" / "practice.json", public_records)
    save_json(PUBLIC / "input" / "family.json", {"cell_size": 24, "axis_encoding": {"0": "X", "1": "Y", "2": "Z"}, "cases": [case["id"] for case in cases], "densities": densities, "support_generator": "workspace/design_common.py:generate_supports", "column_format": "hexadecimal integer (syndrome << 4) | logical_action; slots are time-major, then data-qubit index", "noisy_subrounds": 6, "clean_prefix_subrounds": 6, "clean_suffix_subrounds": 6, "logical_order": ["X1", "Z1", "X2", "Z2"]})
    identity = [2] * 24
    save_json(PUBLIC / "baseline" / "design.json", {"z_image": identity})
    champion, search_score = search(cases, search_records, arguments.trials, 76021)
    baseline_results = {case["id"]: score_case(case, hidden_records[case["id"]], identity) for case in cases}
    champion_results = {case["id"]: score_case(case, hidden_records[case["id"]], champion) for case in cases}
    summary = {"baseline": aggregate(baseline_results), "generator_only": aggregate(champion_results), "search_score": search_score, "search_trials": arguments.trials, "search_uses_hidden_supports": False}
    save_json(CONCEPT / "evaluator" / "hidden" / "supports.json", hidden_records)
    save_json(CONCEPT / "champions" / "generator_only.json", {"z_image": champion})
    save_json(CONCEPT / "champions" / "calibration.json", summary)
    for case in cases:
        shutil.copyfile(PUBLIC / "input" / (case["id"] + ".json.gz"), CONCEPT / "evaluator" / "hidden" / (case["id"] + ".json.gz"))
    shutil.copyfile(PUBLIC / "workspace" / "design_common.py", CONCEPT / "evaluator" / "design_common.py")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
