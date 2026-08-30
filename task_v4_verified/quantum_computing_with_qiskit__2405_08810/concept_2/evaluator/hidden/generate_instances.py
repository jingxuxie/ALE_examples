import argparse
import hashlib
import json
from pathlib import Path
import random
import secrets


CONCEPT_ROOT = Path(__file__).resolve().parents[2]
DESIGNS = (
    ("mesh_22", "mesh", 22, 146),
    ("bridge_26", "bottleneck", 26, 178),
    ("mesh_30", "mesh", 30, 214),
    ("bridge_34", "bottleneck", 34, 246),
)


def encode_json(document):
    return (json.dumps(document, indent=2, allow_nan=False) + "\n").encode("utf-8")


def private_random(seed, label):
    digest = hashlib.sha256(bytes.fromhex(seed) + label.encode("ascii")).digest()
    return random.Random(int.from_bytes(digest, "big"))


def cycle_with_chords(vertices, random_source):
    shuffled = list(vertices)
    random_source.shuffle(shuffled)
    edges = {
        tuple(sorted((vertex, shuffled[(position + 1) % len(shuffled)])))
        for position, vertex in enumerate(shuffled)
    }
    available = set(vertices)
    candidates = [
        (first, second)
        for first in sorted(vertices)
        for second in sorted(vertices)
        if first < second and (first, second) not in edges
    ]
    random_source.shuffle(candidates)
    desired_chords = max(1, len(vertices) * 3 // 8)
    added = 0
    for first, second in candidates:
        if first in available and second in available:
            edges.add((first, second))
            available.difference_update((first, second))
            added += 1
            if added == desired_chords:
                break
    return edges, sorted(available)


def make_hardware(qubit_count, family, random_source):
    labels = list(range(qubit_count))
    random_source.shuffle(labels)
    if family == "mesh":
        edges, available = cycle_with_chords(labels, random_source)
    else:
        midpoint = qubit_count // 2
        left_edges, left_available = cycle_with_chords(labels[:midpoint], random_source)
        right_edges, right_available = cycle_with_chords(labels[midpoint:], random_source)
        left_ports = random_source.sample(left_available, 2)
        right_ports = random_source.sample(right_available, 2)
        bridges = {tuple(sorted(pair)) for pair in zip(left_ports, right_ports)}
        edges = left_edges | right_edges | bridges
    native_cx = []
    for first, second in sorted(edges):
        forward_duration = random_source.randint(1, 5)
        reverse_duration = random_source.randint(1, 5)
        native_cx.extend(((first, second, forward_duration), (second, first, reverse_duration)))
    return [list(instruction) for instruction in sorted(native_cx)]


def would_cancel(program, control, target):
    for previous_control, previous_target in reversed(program):
        if (previous_control, previous_target) == (control, target):
            return True
        if previous_control == target or control == previous_target:
            return False
    return False


def random_native_program(native_cx, length, random_source):
    edges = [(control, target) for control, target, duration in native_cx if control < target]
    program = []
    while len(program) < length:
        shuffled_edges = list(edges)
        random_source.shuffle(shuffled_edges)
        occupied = set()
        for first, second in shuffled_edges:
            if first in occupied or second in occupied:
                continue
            control, target = (first, second) if random_source.getrandbits(1) else (second, first)
            if would_cancel(program, control, target):
                control, target = target, control
            if would_cancel(program, control, target):
                continue
            program.append([control, target])
            occupied.update((control, target))
            if len(program) == length:
                break
    return program


def matrix_from_basis_states(qubit_count, program):
    columns = [1 << column for column in range(qubit_count)]
    for control, target in program:
        for column, state in enumerate(columns):
            if state & (1 << control):
                columns[column] = state ^ (1 << target)
    return [
        [(state >> row) & 1 for state in columns]
        for row in range(qubit_count)
    ]


def dependency_schedule(native_cx, program):
    durations = {(control, target): duration for control, target, duration in native_cx}
    schedule = []
    for position, (control, target) in enumerate(program):
        predecessors = [
            schedule[previous][1]
            for previous, (previous_control, previous_target) in enumerate(program[:position])
            if control in (previous_control, previous_target) or target in (previous_control, previous_target)
        ]
        start = max(predecessors, default=0)
        schedule.append([start, start + durations[(control, target)]])
    return schedule


def sufficiently_mixed(matrix, native_cx, program):
    qubit_count = len(matrix)
    row_weights = [sum(row) for row in matrix]
    column_weights = [sum(matrix[row][column] for row in range(qubit_count)) for column in range(qubit_count)]
    touched_edges = {tuple(sorted(gate)) for gate in program}
    required_edges = {tuple(sorted((control, target))) for control, target, duration in native_cx}
    return (
        min(row_weights + column_weights) >= 2
        and sum(row_weights) * 100 >= qubit_count * qubit_count * 28
        and touched_edges == required_edges
    )


def generate(seed):
    suite = {"schema_version": 1, "suite_id": "native_cx_linear_v1", "targets": []}
    witness = {"schema_version": 1, "circuits": {}}
    provenance = {"generator_version": 1, "private_cases": []}
    for name, family, qubit_count, length in DESIGNS:
        hardware_random = private_random(seed, name + "/hardware")
        native_cx = make_hardware(qubit_count, family, hardware_random)
        for candidate_index in range(2048):
            circuit_random = private_random(seed, name + "/program/" + str(candidate_index))
            program = random_native_program(native_cx, length, circuit_random)
            matrix = matrix_from_basis_states(qubit_count, program)
            if sufficiently_mixed(matrix, native_cx, program):
                break
        else:
            raise RuntimeError("Mixing filter exhausted for " + name)
        schedule = dependency_schedule(native_cx, program)
        depth = max(finish for start, finish in schedule)
        suite["targets"].append({
            "name": name,
            "family": family,
            "n_qubits": qubit_count,
            "native_cx": native_cx,
            "matrix": matrix,
            "max_cx": (length * 106 + 99) // 100,
            "max_weighted_depth": (depth * 108 + 99) // 100,
        })
        witness["circuits"][name] = program
        provenance["private_cases"].append({
            "name": name,
            "candidate_index": candidate_index,
            "cx_count": length,
            "weighted_depth": depth,
            "schedule": schedule,
            "matrix_ones": sum(sum(row) for row in matrix),
        })
    return suite, witness, provenance


def main():
    parser = argparse.ArgumentParser(description="Privileged one-time instance generation; never release this program or its seed.")
    parser.add_argument("--verify", action="store_true", help="Recompute and compare without modifying frozen files.")
    arguments = parser.parse_args()
    hidden_root = CONCEPT_ROOT / "evaluator" / "hidden"
    seed_path = hidden_root / "seed.json"
    paths = {
        "public": CONCEPT_ROOT / "participant" / "input" / "instances.json",
        "private": hidden_root / "instances.json",
        "witness": hidden_root / "planted_solution.json",
        "provenance": hidden_root / "generation_metadata.json",
    }
    if arguments.verify:
        seed = json.loads(seed_path.read_text(encoding="utf-8"))["seed_hex"]
    else:
        if seed_path.exists() or any(path.exists() for path in paths.values()):
            parser.error("Refusing to replace an existing generation; use --verify.")
        seed = secrets.token_hex(32)
    suite, witness, provenance = generate(seed)
    documents = {"public": suite, "private": suite, "witness": witness, "provenance": provenance}
    for label, path in paths.items():
        encoded = encode_json(documents[label])
        if arguments.verify:
            if path.read_bytes() != encoded:
                raise RuntimeError("Frozen generation differs: " + label)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encoded)
    if not arguments.verify:
        seed_path.write_bytes(encode_json({"seed_hex": seed}))
    print(json.dumps({
        "verified" if arguments.verify else "generated": True,
        "thresholds": [
            {key: target[key] for key in ("name", "n_qubits", "max_cx", "max_weighted_depth")}
            for target in suite["targets"]
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
