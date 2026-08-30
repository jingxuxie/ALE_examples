import collections
import datetime
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import random
import sys
import time


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
G2 = ROOT.parent / "generation_2"
SPECIFICATION = importlib.util.spec_from_file_location("phase_stress_g2_helpers", G2 / "adversary/generate.py")
HELPERS = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(HELPERS)
FAMILIES = HELPERS.FAMILIES
SOURCES = (G2 / "adversary/generate.py", G2 / "participant/baseline/solve.py", G2 / "evaluator/routing.py",
           G2 / "evaluator/hidden/manifest.json", G2 / "freeze.json")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")


def components(vertices, edges):
    adjacency = {vertex: set() for vertex in vertices}
    for first, second in edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(vertices)
    sizes = []
    while remaining:
        pending = [remaining.pop()]
        size = 0
        while pending:
            vertex = pending.pop()
            size += 1
            fresh = adjacency[vertex] & remaining
            remaining.difference_update(fresh)
            pending.extend(fresh)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def all_distances(count, edges):
    distance = [[float("inf")] * count for _ in range(count)]
    for vertex in range(count):
        distance[vertex][vertex] = 0.0
    for first, second, weight in edges:
        distance[first][second] = distance[second][first] = 3 * weight
    for middle in range(count):
        for first in range(count):
            for second in range(count):
                distance[first][second] = min(distance[first][second], distance[first][middle] + distance[middle][second])
    return distance


def construct(family, seed, identifier):
    generator = random.Random(seed)
    count, graph = HELPERS.architecture(family, generator)
    labels = list(range(count))
    generator.shuffle(labels)
    graph = [(labels[first], labels[second]) for first, second in graph]
    regions = HELPERS.find_regions(count, graph, generator)
    if regions is None:
        return None, {"reason": "no_disjoint_calibration_regions"}
    first_path, second_path, destination = regions
    expensive = HELPERS.path_edges(first_path) | HELPERS.path_edges(second_path)
    cheap = HELPERS.path_edges(destination)
    edges = [[first, second, round(generator.uniform(2.76, 2.8) if tuple(sorted((first, second))) in expensive
                                    else generator.uniform(0.45, 0.47) if tuple(sorted((first, second))) in cheap
                                    else generator.uniform(0.55, 0.70), 4)] for first, second in graph]
    initial = list(range(count))
    generator.shuffle(initial)
    occupants = [0] * count
    for logical, physical in enumerate(initial):
        occupants[physical] = logical
    old_wires = [occupants[physical] for physical in first_path + second_path]
    initial_work, operations, positions, occupants = HELPERS.tree_route(
        count, edges, initial, dict(zip(old_wires, destination)), generator)
    gates = []
    phases = []

    def burst(physical_path, length, mechanism):
        start = len(gates)
        operation_start = len(operations)
        logical_path = [occupants[physical] for physical in physical_path]
        interactions = list(zip(logical_path, logical_path[1:]))
        while len(gates) < start + length:
            selected = interactions[:]
            generator.shuffle(selected)
            for first, second in selected:
                pair = [first, second]
                if generator.random() < 0.5:
                    pair.reverse()
                operations.append(["gate", len(gates)])
                gates.append(pair)
        phases.append({"mechanism": mechanism, "start": start, "end": len(gates),
                       "operation_start": operation_start, "operation_end": len(operations),
                       "physical_path": list(physical_path), "logical_path": logical_path})

    burst(destination[:4], 48, "first_block_four_wire_epoch")
    burst(destination[1:5], 48, "overlapping_window_in_five_wire_block")
    burst(destination[5:9], 48, "second_four_wire_block_epoch")
    burst(destination[1:5], 48, "returning_overlapping_block_epoch")
    first, second = destination[4], destination[5]
    operations.append(["swap", first, second])
    occupants[first], occupants[second] = occupants[second], occupants[first]
    positions[occupants[first]], positions[occupants[second]] = first, second
    burst(destination[3:7], 12, "paid_cross_block_exchange_and_coupling")
    distance = all_distances(count, edges)
    inactive = [logical for logical in range(count) if logical not in old_wires]
    placements = []
    for physical_path in (destination[:4], destination[5:9]):
        for anchor_index in (0, 3):
            anchor_physical = physical_path[anchor_index]
            anchor = occupants[anchor_physical]
            targets = [physical for physical in physical_path if physical != anchor_physical]
            nearest = sorted(inactive, key=lambda logical: min(distance[positions[logical]][target] for target in targets))[:6]
            newcomers = min(itertools.permutations(nearest, 3),
                            key=lambda choices: sum(distance[positions[logical]][physical] for logical, physical in zip(choices, targets)))
            goals = {anchor: anchor_physical, **dict(zip(newcomers, targets))}
            route = HELPERS.tree_route(count, edges, positions, goals, generator)
            placements.append((route[0], physical_path, newcomers, anchor, route))
    _, late_path, newcomers, anchor, late_route = min(placements, key=lambda record: record[0])
    late_work, late_operations, positions, occupants = late_route
    if not late_operations:
        return None, {"reason": "no_paid_late_transition"}
    operations.extend(late_operations)
    burst(late_path, 36, "three_incoming_wires_reuse_prior_four_wire_region")
    case = {"id": identifier, "family": family, "n": count, "edges": edges, "initial": initial, "gates": gates}
    answer = {"operations": operations}
    witness_score = HELPERS.CHECKER.validate(case, answer)
    baseline_answer = HELPERS.BASELINE.solve(case)
    baseline_score = HELPERS.CHECKER.validate(case, baseline_answer)
    improvement = 1 - witness_score["cost"] / baseline_score["cost"]
    metadata = {"seed": seed, "n": count, "gates": len(gates), "old_wires": old_wires,
                "incoming_wires": list(newcomers), "late_anchor": anchor,
                "cheap_region": list(destination), "cheap_threshold": 0.50,
                "source_regions": [list(first_path), list(second_path)], "phases": phases,
                "initial_relocation_work": initial_work, "late_relocation_work": late_work,
                "late_relocation_swaps": len(late_operations), "initial_route_portfolio": 24,
                "late_target_choices": 4, "late_route_portfolio_per_choice": 24,
                "baseline": baseline_score, "certificate": witness_score, "improvement": improvement}
    if improvement < 0.5:
        return None, {"reason": "certificate_below_50pct", **metadata}
    return {"case": case, "answer": answer, "baseline_answer": baseline_answer, "design": metadata}, metadata


def validate_records(records):
    rows = []
    for record in records:
        case, design = record["case"], record["design"]
        count = case["n"]
        assert 12 <= count <= 28 and 96 <= len(case["gates"]) <= 240
        assert sorted(case["initial"]) == list(range(count))
        edge_keys = set()
        for first, second, weight in case["edges"]:
            assert type(first) is int and type(second) is int and 0 <= first < count and 0 <= second < count and first != second
            assert math.isfinite(weight) and 0.45 <= weight <= 2.8
            edge = tuple(sorted((first, second)))
            assert edge not in edge_keys
            edge_keys.add(edge)
        assert components(range(count), edge_keys) == [count]
        usage = collections.Counter(logical for gate in case["gates"] for logical in gate)
        assert len(usage) == 12 and min(usage.values()) >= 12
        interactions = {tuple(sorted(gate)) for gate in case["gates"]}
        assert components(usage, interactions) == [12]
        cheap_edges = [(first, second) for first, second, weight in case["edges"] if weight <= design["cheap_threshold"]]
        cheap_components = components(range(count), cheap_edges)
        assert cheap_components[0] == 9 < len(usage)
        operations = record["answer"]["operations"]
        previous_operation = 0
        previous_gate = 0
        transition_swaps = []
        active_sets = []
        for phase in design["phases"]:
            assert phase["start"] == previous_gate and phase["end"] > phase["start"]
            phase_gates = case["gates"][phase["start"]:phase["end"]]
            active = set(logical for gate in phase_gates for logical in gate)
            phase_interactions = collections.Counter(tuple(sorted(gate)) for gate in phase_gates)
            assert len(active) == 4 and components(active, phase_interactions) == [4]
            assert len(phase_interactions) == 3 and len(set(phase_interactions.values())) == 1
            assert set(phase["logical_path"]) == active
            assert all(tuple(sorted(edge)) in edge_keys for edge in zip(phase["physical_path"], phase["physical_path"][1:]))
            before = operations[previous_operation:phase["operation_start"]]
            assert all(operation[0] == "swap" for operation in before)
            assert operations[phase["operation_start"]:phase["operation_end"]] == [["gate", index] for index in range(phase["start"], phase["end"])]
            transition_swaps.append(len(before))
            active_sets.append(active)
            previous_operation = phase["operation_end"]
            previous_gate = phase["end"]
        assert previous_gate == len(case["gates"]) and previous_operation == len(operations)
        assert len(active_sets) == 6 and sum(value > 0 for value in transition_swaps[1:]) >= 2
        assert len(set(design["incoming_wires"])) == 3 and not set(design["incoming_wires"]) & set(design["old_wires"])
        assert set(design["incoming_wires"]) <= active_sets[-1]
        assert active_sets[-1] & set().union(*active_sets[:-1])
        assert design["phases"][-1]["end"] - design["phases"][-1]["start"] == 36
        witness_score = HELPERS.CHECKER.validate(case, record["answer"])
        baseline_score = HELPERS.CHECKER.validate(case, record["baseline_answer"])
        assert abs(witness_score["cost"] - design["certificate"]["cost"]) < 1e-8
        assert abs(baseline_score["cost"] - design["baseline"]["cost"]) < 1e-8
        improvement = 1 - witness_score["cost"] / baseline_score["cost"]
        assert improvement >= 0.5
        rows.append({"id": case["id"], "family": case["family"], "active_wires": len(usage),
                     "minimum_wire_gate_count": min(usage.values()), "connected_four_wire_epochs": len(active_sets),
                     "cheap_component_capacity": cheap_components[0], "inter_epoch_swap_counts": transition_swaps[1:],
                     "baseline_cost": baseline_score["cost"], "certificate_cost": witness_score["cost"],
                     "improvement": improvement})
    if records:
        first = records[0]
        invalid = {"operations": first["answer"]["operations"][:-1]}
        try:
            HELPERS.CHECKER.validate(first["case"], invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("checker accepted a dropped gate")
    return rows


def main():
    if (ROOT / "freeze.json").exists():
        raise SystemExit("Private pool already frozen; refusing overwrite")
    started = time.monotonic()
    source_hashes = {str(path): digest(path) for path in SOURCES}
    assert source_hashes[str(G2 / "participant/baseline/solve.py")] == HELPERS.ORIGINAL_SHA256
    records = []
    counts = collections.Counter()
    trials = collections.Counter()
    history = []
    generation_budget_seconds = 480
    while time.monotonic() - started < generation_budget_seconds:
        pending = [family for family in FAMILIES if counts[family] < 4 and trials[family] < 64]
        if not pending:
            break
        family = min(pending, key=lambda value: (counts[value], trials[value], FAMILIES.index(value)))
        seed = 2026082801 + FAMILIES.index(family) * 100000 + trials[family] * 977
        identifier = f"phase_stress_{family}_{counts[family]}"
        trials[family] += 1
        record, result = construct(family, seed, identifier)
        entry = {"family": family, "seed": seed, "accepted": record is not None,
                 "improvement": result.get("improvement"), "reason": result.get("reason")}
        history.append(entry)
        if record is not None:
            validate_records([record])
            records.append(record)
            counts[family] += 1
            print(json.dumps({"accepted": identifier, "family_trials": trials[family],
                              "certificate_improvement": result["improvement"], "late_swaps": result["late_relocation_swaps"]}), flush=True)
            write_json("certificates.json", {item["case"]["id"]: item for item in records})
        write_json("generation_progress.json", {"counts": dict(counts), "trials": dict(trials), "elapsed_seconds": time.monotonic() - started})
    rows = validate_records(records)
    cases = sorted((record["case"] for record in records), key=lambda case: (FAMILIES.index(case["family"]), case["id"]))
    family_scores = {family: 1 - math.exp(sum(math.log(row["certificate_cost"] / row["baseline_cost"]) for row in rows if row["family"] == family) / counts[family])
                     for family in FAMILIES if counts[family]}
    core = 1 - math.exp(sum(math.log(row["certificate_cost"] / row["baseline_cost"]) for row in rows) / len(rows)) if rows else None
    complete = len(records) == 24 and all(counts[family] == 4 for family in FAMILIES)
    write_json("cases.json", cases)
    write_json("manifest.json", {"purpose": "private prospective champion stress pool; not generation 3",
               "case_count": len(cases), "requested_case_count": 24, "complete": complete,
               "family_counts": dict(counts), "case_ids": [case["id"] for case in cases],
               "quality_targets_unchanged": {"core": 0.40, "worst_family": 0.30},
               "resource_contract_unchanged": {"case_seconds": 12, "suite_seconds": 360},
               "baseline": {record["case"]["id"]: record["design"]["baseline"] for record in records},
               "source_sha256": source_hashes, "certificate_acceptance_improvement": 0.50,
               "champion_not_evaluated": True, "attempts_not_read": True, "fresh_agents_launched": 0})
    write_json("validation.json", {"valid": True, "complete": complete, "checked_cases": len(rows), "rows": rows,
               "minimum_certificate_improvement": min((row["improvement"] for row in rows), default=None),
               "certificate_core": core, "certificate_worst_family": min(family_scores.values(), default=None),
               "certificate_family_scores": family_scores, "static_all_cheap_placement_impossible": bool(rows),
               "static_target_infeasibility_claimed": False, "dropped_gate_rejected": bool(rows)})
    write_json("generation_report.json", {"counts": dict(counts), "trials": dict(trials), "candidate_count": len(history),
               "accepted_count": len(records), "elapsed_seconds": time.monotonic() - started,
               "generation_budget_seconds": generation_budget_seconds, "candidate_limit_per_family": 64,
               "history": history, "complete": complete, "no_champion_access_or_evaluation": True,
               "certificates_generation_only_not_resource_qualified_solver": True})
    assert all(digest(Path(path)) == expected for path, expected in source_hashes.items())
    inventory = {str(path.relative_to(ROOT)): digest(path) for path in sorted(ROOT.rglob("*"))
                 if path.is_file() and path.name != "freeze.json" and "__pycache__" not in path.parts}
    write_json("freeze.json", {"frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "private_pool_only": True, "complete": complete, "fresh_agents_launched": 0,
               "generation_2_unchanged": True, "champion_not_inspected": True, "sha256": inventory})
    print(json.dumps({"complete": complete, "case_count": len(records), "candidate_count": len(history),
                      "elapsed_seconds": time.monotonic() - started, "certificate_core": core,
                      "certificate_worst_family": min(family_scores.values(), default=None),
                      "minimum_certificate_improvement": min((row["improvement"] for row in rows), default=None),
                      "family_scores": family_scores}, indent=2), flush=True)


if __name__ == "__main__":
    main()
