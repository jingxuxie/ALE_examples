import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import statistics
import sys
import time


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "adversary/champion_fuzz_1"
ORIGINAL_BASELINE_SHA256 = "944d86402ef50921f7c8aa4b047c71734dce5e8dad7ce29e5712c7bb7dc03fd3"


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


BASELINE = load_module("fuzz_baseline", ROOT / "participant/baseline/solve.py")
CHECKER = load_module("fuzz_checker", ROOT / "participant/workspace/routing.py")
SANDBOX = load_module("fuzz_sandbox", ROOT.parent / "authoring/sandbox.py")


def source_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def architecture(family, pattern_index):
    edges = []
    if family in ("chain", "ring"):
        count = (24, 20, 28)[pattern_index]
        edges = [(index, index + 1) for index in range(count - 1)]
        if family == "ring":
            edges.append((count - 1, 0))
        regions = [min(3, 4 * index // count) for index in range(count)]
    elif family == "grid":
        rows, columns = ((4, 6), (4, 5), (3, 4))[pattern_index]
        count = rows * columns
        edges = [(row * columns + column, row * columns + column + 1)
                 for row in range(rows) for column in range(columns - 1)]
        edges += [(row * columns + column, (row + 1) * columns + column)
                  for row in range(rows - 1) for column in range(columns)]
        regions = [2 * (row >= rows // 2) + (column >= columns // 2)
                   for row in range(rows) for column in range(columns)]
    elif family == "ladder":
        width = (12, 10, 14)[pattern_index]
        count = 2 * width
        edges = [(index, index + 1) for index in range(width - 1)]
        edges += [(width + index, width + index + 1) for index in range(width - 1)]
        edges += [(index, width + index) for index in range(width)]
        regions = [min(3, 4 * (index % width) // width) for index in range(count)]
    elif family == "tree":
        count = (27, 23, 19)[pattern_index]
        edges = [(index, (index - 1) // 2) for index in range(1, count)]
        regions = []
        for index in range(count):
            ancestor = index
            while ancestor > 6:
                ancestor = (ancestor - 1) // 2
            regions.append((ancestor - 3) % 4 if ancestor >= 3 else ancestor % 4)
    elif family == "modular":
        width = (7, 6, 5)[pattern_index]
        count = 4 * width
        for block in range(4):
            base = block * width
            edges.extend((base + index, base + (index + 1) % width) for index in range(width))
            edges.append((base, base + width // 2))
        edges.extend((block * width - 1, block * width) for block in range(1, 4))
        regions = [index // width for index in range(count)]
    else:
        raise ValueError("unsupported architecture family")
    return count, edges, regions


def workload(pattern, groups, count, wanted, generator):
    gates = []
    last_partner = [-1] * count

    def append(first, second):
        if first == second or (last_partner[first] == second and last_partner[second] == first):
            return False
        if generator.random() < 0.5:
            first, second = second, first
        gates.append([first, second])
        last_partner[first] = second
        last_partner[second] = first
        return True

    for group in groups:
        shuffled = group[:]
        generator.shuffle(shuffled)
        for index in range(len(shuffled)):
            append(shuffled[index], shuffled[(index + 1) % len(shuffled)])
    proposals = 0
    while len(gates) < wanted:
        proposals += 1
        if proposals > wanted * 100:
            raise ValueError("workload generator failed to make progress")
        if pattern == "phase_switch":
            phase = min(3, 4 * len(gates) // wanted)
            region = generator.randrange(4)
            if phase in (0, 2):
                first, second = generator.sample(groups[(region + phase) % 4], 2)
            else:
                first = generator.choice(groups[region])
                second = generator.choice(groups[(region + (1 if phase == 1 else 2)) % 4])
        elif pattern == "moving_hotspot":
            phase = len(gates) // 24
            region = phase % 4
            if len(gates) % 7 == 0:
                first, second = generator.sample(range(count), 2)
            else:
                hub_group = groups[region if len(gates) % 2 == 0 else (region + 2) % 4]
                first = hub_group[(phase // 4) % len(hub_group)]
                second = generator.choice(groups[(region + 1 + len(gates) % 3) % 4])
        elif pattern == "alternating_cut":
            phase = len(gates) // 8
            region = (len(gates) + phase) % 4
            first_group = groups[region]
            second_group = groups[(region + (1 if phase % 2 else 2)) % 4]
            first = first_group[(len(gates) // 4 + phase + proposals) % len(first_group)]
            second = second_group[(len(gates) // 3 + 2 * phase + proposals // 3) % len(second_group)]
        else:
            raise ValueError("unsupported traffic pattern")
        append(first, second)
    return gates[:wanted]


def make_pair(family, family_index, pattern, pattern_index):
    seed = 481573903 + 104729 * family_index + 8191 * pattern_index
    generator = random.Random(seed)
    count, edges, regions = architecture(family, pattern_index)
    initial_unlabeled = list(range(count))
    generator.shuffle(initial_unlabeled)
    groups = [[logical for logical, physical in enumerate(initial_unlabeled)
               if regions[physical] == region] for region in range(4)]
    if min(map(len, groups)) < 2:
        raise ValueError("each traffic region needs at least two qubits")
    wanted = (240, 192, 120)[pattern_index]
    gates = workload(pattern, groups, count, wanted, generator)
    weights = []
    for first, second in edges:
        if pattern == "moving_hotspot":
            expensive = regions[first] == regions[second] and regions[first] % 2 == 0
        else:
            expensive = regions[first] != regions[second]
        weights.append(round(generator.uniform(2.60, 2.8) if expensive else
                             generator.uniform(0.45, 0.65), 4))
    relabel = list(range(count))
    generator.shuffle(relabel)
    initial = [relabel[physical] for physical in initial_unlabeled]
    shuffled_weights = weights[:]
    random.Random(seed + 65537).shuffle(shuffled_weights)
    cases = []
    for calibration, selected in (("correlated", weights), ("scrambled_control", shuffled_weights)):
        identifier = f"fuzz1_{family}_{pattern}_{calibration}"
        case = {"id": identifier, "family": family, "n": count,
                "edges": [[relabel[first], relabel[second], weight]
                          for (first, second), weight in zip(edges, selected)],
                "initial": initial, "gates": gates}
        metadata = {"id": identifier, "family": family, "pattern": pattern,
                    "calibration": calibration, "seed": seed,
                    "pair_id": f"{family}_{pattern}", "n": count, "gates": len(gates),
                    "expensive_edges": sum(weight >= 2.6 for weight in selected),
                    "edge_count": len(edges), "calibration_min": min(selected),
                    "calibration_max": max(selected), "weight_multiset": sorted(selected),
                    "phase_length": {"phase_switch": wanted // 4, "moving_hotspot": 24,
                                     "alternating_cut": 8}[pattern]}
        cases.append((case, metadata))
    return cases


def check_input(case):
    count = case["n"]
    if not 12 <= count <= 28 or not 96 <= len(case["gates"]) <= 240:
        raise ValueError("input outside disclosed size bounds")
    if sorted(case["initial"]) != list(range(count)):
        raise ValueError("initial placement must be a fixed permutation")
    adjacency = [set() for _ in range(count)]
    for first, second, weight in case["edges"]:
        if not (0 <= first < count and 0 <= second < count and first != second and
                math.isfinite(weight) and 0.45 <= weight <= 2.8):
            raise ValueError("invalid calibrated architecture edge")
        if second in adjacency[first]:
            raise ValueError("duplicate architecture edge")
        adjacency[first].add(second)
        adjacency[second].add(first)
    visited = {0}
    pending = [0]
    while pending:
        for neighbor in adjacency[pending.pop()]:
            if neighbor not in visited:
                visited.add(neighbor)
                pending.append(neighbor)
    if len(visited) != count:
        raise ValueError("architecture must be connected")
    active = set()
    for first, second in case["gates"]:
        if not (0 <= first < count and 0 <= second < count and first != second):
            raise ValueError("invalid gate")
        active.update((first, second))
    if len(active) != count:
        raise ValueError("structured suite must exercise every logical qubit")


def quality(records):
    if not records or not all(record["valid"] for record in records):
        return None
    return 1 - math.exp(statistics.mean(math.log(record["ratio"]) for record in records))


def summarize(records, provenance, started, expected):
    families = {family: quality([record for record in records if record["family"] == family])
                for family in sorted({record["family"] for record in records})}
    patterns = {pattern: quality([record for record in records if record["pattern"] == pattern])
                for pattern in sorted({record["pattern"] for record in records})}
    calibrations = {calibration: quality([record for record in records if record["calibration"] == calibration])
                    for calibration in sorted({record["calibration"] for record in records})}
    pairs = {}
    for record in records:
        pairs.setdefault(record["pair_id"], {})[record["calibration"]] = record
    comparisons = []
    for pair_id, members in sorted(pairs.items()):
        if len(members) == 2 and all(record["valid"] for record in members.values()):
            correlated, control = members["correlated"], members["scrambled_control"]
            comparisons.append({"pair_id": pair_id, "correlated_improvement": correlated["improvement"],
                                "scrambled_improvement": control["improvement"],
                                "correlated_minus_scrambled": correlated["improvement"] - control["improvement"]})
    valid = len(records) == expected and all(record["valid"] for record in records)
    core = quality(records)
    worst = min(families.values()) if families and all(value is not None for value in families.values()) else None
    return {"status": "complete" if len(records) == expected else "partial", "provenance": provenance,
            "case_count": len(records), "expected_cases": expected,
            "valid_cases": sum(record["valid"] for record in records), "valid": valid,
            "core_score": core, "worst_family_score": worst, "family_scores": families,
            "pattern_scores": patterns, "calibration_scores": calibrations,
            "quality_targets_met_on_this_structured_suite": valid and core >= 0.15 and worst >= 0.08,
            "regressions": sum(record.get("ratio", 0) > 1 for record in records),
            "misses_15pct": sum(record.get("ratio", 0) > 0.85 for record in records),
            "sandbox_seconds_sum": sum(record.get("seconds", 0) for record in records),
            "wall_seconds": time.monotonic() - started, "paired_comparisons": comparisons,
            "worst_cases": sorted([record for record in records if record["valid"]],
                                  key=lambda record: record["ratio"], reverse=True)[:12],
            "records": records,
            "interpretation": ["Private distribution-shift diagnostic, not a revision of generation-1 scoring",
                               "Per-case 15% misses alone do not falsify the aggregate task target",
                               "Matched controls preserve topology, initial placement, traffic, and weight multiset",
                               "No standard-generator cases or other attempts are read"]}


def evaluate_case(champion, case, metadata, timeout):
    reference_answer = BASELINE.solve(case)
    reference = CHECKER.validate(case, reference_answer)
    (DESTINATION / "baseline_routes" / f"{case['id']}.json").write_text(json.dumps(reference_answer) + "\n")
    weights = {tuple(sorted((first, second))): weight for first, second, weight in case["edges"]}
    swap_work = sum(3 * weights[tuple(sorted(operation[1:]))]
                    for operation in reference_answer["operations"] if operation[0] == "swap")
    record = {**metadata, "baseline": reference, "baseline_cost": reference["cost"],
              "baseline_swap_work_fraction": swap_work / reference["calibrated_work"], "valid": False}
    execution = SANDBOX.run_python(champion, "solve.py", case, timeout)
    record.update(seconds=execution["seconds"], returncode=execution["returncode"],
                  timed_out=execution["timed_out"])
    (DESTINATION / "executions" / f"{case['id']}.json").write_text(json.dumps(execution) + "\n")
    if execution["returncode"] or execution["timed_out"]:
        record["reason"] = "execution failure: " + execution["stderr"][-1200:]
        return record
    try:
        answer = json.loads(execution["stdout"])
        metrics = CHECKER.validate(case, answer)
        (DESTINATION / "champion_routes" / f"{case['id']}.json").write_text(json.dumps(answer) + "\n")
        record.update(metrics)
        record["ratio"] = metrics["cost"] / reference["cost"]
        record["improvement"] = 1 - record["ratio"]
    except (ValueError, TypeError, KeyError) as error:
        record["reason"] = "route validation failure: " + str(error)
    return record


def main(arguments):
    started = time.monotonic()
    champion = Path(arguments.champion).resolve(strict=True)
    authorized = {(ROOT / "champions/generation_1").resolve(),
                  (ROOT / "attempts/v_1.frozen").resolve(), (ROOT / "attempts/v1.frozen").resolve()}
    if champion not in authorized:
        raise ValueError("only the authorized generation-1 A champion may be read or run")
    baseline_hash = source_hash(ROOT / "participant/baseline/solve.py")
    if baseline_hash != ORIGINAL_BASELINE_SHA256:
        raise ValueError("original supplied baseline has changed")
    for directory in (DESTINATION, DESTINATION / "cases", DESTINATION / "baseline_routes",
                      DESTINATION / "champion_routes", DESTINATION / "executions"):
        directory.mkdir(exist_ok=True)
    selected = []
    for family_index, family in enumerate(("chain", "ring", "grid", "ladder", "tree", "modular")):
        for pattern_index, pattern in enumerate(("phase_switch", "moving_hotspot", "alternating_cut")):
            selected.extend(make_pair(family, family_index, pattern, pattern_index))
    selected = selected[:arguments.limit]
    for case, metadata in selected:
        check_input(case)
        (DESTINATION / "cases" / f"{case['id']}.json").write_text(json.dumps(case) + "\n")
    cases = [case for case, _ in selected]
    provenance = {"champion": str(champion), "champion_sha256": {
        filename: source_hash(champion / filename) for filename in ("solve.py", "router.cpp", "router.so")},
        "baseline_sha256": baseline_hash,
        "checker_sha256": source_hash(ROOT / "participant/workspace/routing.py"),
        "sandbox_sha256": source_hash(ROOT.parent / "authoring/sandbox.py"),
        "fuzzer_sha256": source_hash(Path(__file__)),
        "cases_canonical_sha256": hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest(),
        "sandbox": "unchanged Landlock+seccomp run_python, default champion environment",
        "case_timeout": arguments.case_seconds, "memory_mb": 2048, "cores_per_invocation": 1}
    (DESTINATION / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")
    (DESTINATION / "design.json").write_text(json.dumps({"provenance": provenance,
        "candidate_count": len(selected), "metadata": [metadata for _, metadata in selected],
        "design": "18 matched pairs: phase switching, moving hotspots, alternating cuts; spatially correlated versus shuffled identical calibration multisets; all cases frozen before execution"}, indent=2) + "\n")
    records = []
    for case, metadata in selected:
        record = evaluate_case(champion, case, metadata, arguments.case_seconds)
        records.append(record)
        summary = summarize(records, provenance, started, len(selected))
        (DESTINATION / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps({key: record.get(key) for key in
                          ("id", "valid", "improvement", "ratio", "seconds", "baseline_swap_work_fraction", "reason")}), flush=True)
        if not record["valid"]:
            raise RuntimeError("stop for invalid route or harness failure; inspect own execution artifact before attributing failure")
    if any(source_hash(champion / filename) != digest for filename, digest in provenance["champion_sha256"].items()):
        raise RuntimeError("champion source or binary changed during audit")
    print(json.dumps({key: summary[key] for key in
                      ("case_count", "valid_cases", "core_score", "worst_family_score", "family_scores", "pattern_scores", "calibration_scores", "regressions", "misses_15pct", "wall_seconds")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--champion", default=str(ROOT / "champions/generation_1"))
    parser.add_argument("--limit", type=int, default=36)
    parser.add_argument("--case-seconds", type=float, default=8)
    main(parser.parse_args())
