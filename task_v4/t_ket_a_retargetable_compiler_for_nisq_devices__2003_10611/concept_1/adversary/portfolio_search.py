import argparse
import concurrent.futures
import hashlib
import heapq
import importlib.util
import inspect
import itertools
import json
import math
from pathlib import Path
import random
import sys
import time


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
BASELINE_CONFIGURATIONS = [(12, 0.35, 0.0, 10), (24, 0.55, 0.015, 20),
                           (40, 0.75, 0.025, 30), (64, 1.0, 0.01, 40)]


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


BASELINE = load_module("portfolio_baseline", ROOT / "participant/baseline/solve.py")
CHECKER = load_module("portfolio_checker", ROOT / "participant/workspace/routing.py")
WEIGHTED_ROUTERS = {}


def configurations():
    grid = list(itertools.product((4, 8, 12, 24, 40, 64, 96),
                                  (0.0, 0.2, 0.4, 0.65, 1.0, 1.5), (0.0, 0.03)))
    random.Random(713981).shuffle(grid)
    selected = list(BASELINE_CONFIGURATIONS)
    selected.extend((*values, 1009 + 97 * index) for index, values in enumerate(grid))
    selected.extend([(12, 0.35, 0.0, 101), (24, 0.55, 0.015, 202),
                     (40, 0.75, 0.025, 303), (64, 1.0, 0.01, 404),
                     (128, 0.4, 0.0, 505), (256, 0.65, 0.0, 606),
                     (24, 0.8, 0.1, 707), (64, 1.2, 0.1, 808)])
    return selected


def weighted_configurations():
    selected = []
    for weight_fraction, lookahead, future_weight, edge_penalty in itertools.product(
            (0.3, 0.6, 1.0), (8, 24, 64), (0.25, 0.65, 1.2), (0.025, 0.2)):
        selected.append({"algorithm": "weighted", "weight_fraction": weight_fraction,
                         "lookahead": lookahead, "future_weight": future_weight,
                         "decay_weight": 0.0, "edge_penalty": edge_penalty,
                         "seed": 1579 + 101 * len(selected)})
    random.Random(19453).shuffle(selected)
    return selected


def beam_configurations():
    selected = []
    for fraction, lookahead, future_weight in itertools.product(
            (0.15, 0.6, 1.0), (8, 32), (0.4, 0.8)):
        selected.append({"algorithm": "beam", "weight_fraction": fraction,
                         "lookahead": lookahead, "future_weight": future_weight,
                         "decay_weight": 0.0, "edge_penalty": 0.04,
                         "beam_width": 6, "beam_depth": 3, "seed": 9929 + len(selected)})
    for fraction, future_weight in itertools.product((0.15, 0.8), (0.4, 0.8)):
        selected.append({"algorithm": "beam", "weight_fraction": fraction,
                         "lookahead": 24, "future_weight": future_weight,
                         "decay_weight": 0.0, "edge_penalty": 0.04,
                         "beam_width": 16, "beam_depth": 4, "seed": 7919 + len(selected)})
    return selected


def choose_beam_swap(positions, occupants, frontier, future, gates, distance,
                     weights, adjacency, previous_swap, future_weight,
                     beam_width, beam_depth):
    pairs = [(gates[index][0], gates[index][1], 1.0 / len(frontier), True)
             for index in frontier]
    pairs.extend((gates[index][0], gates[index][1], future_weight / max(1, len(future)), False)
                 for index in future)
    incidence = [[] for _ in positions]
    for pair_index, (logical_first, logical_second, _, _) in enumerate(pairs):
        incidence[logical_first].append(pair_index)
        incidence[logical_second].append(pair_index)

    def pair_cost(pair_index, state_positions):
        logical_first, logical_second, coefficient, current = pairs[pair_index]
        first, second = state_positions[logical_first], state_positions[logical_second]
        edge = (first, second) if first < second else (second, first)
        connected_reward = 2.0 if current and edge in weights else 0.0
        return coefficient * (distance[first][second] - connected_reward)

    initial_potential = sum(pair_cost(index, positions) for index in range(len(pairs)))
    states = [(initial_potential, tuple(positions), tuple(occupants), (), 0.0)]
    for _ in range(beam_depth):
        successors = {}
        for potential, state_positions, state_occupants, path, paid in states:
            candidates = set()
            for gate_index in frontier:
                for logical in gates[gate_index]:
                    first = state_positions[logical]
                    for second in adjacency[first]:
                        candidates.add((min(first, second), max(first, second)))
            for edge in sorted(candidates):
                if path and edge == path[-1]:
                    continue
                first, second = edge
                logical_first, logical_second = state_occupants[first], state_occupants[second]
                affected = set(incidence[logical_first]) | set(incidence[logical_second])
                child_positions = list(state_positions)
                child_positions[logical_first], child_positions[logical_second] = second, first
                child_potential = potential + sum(pair_cost(index, child_positions) -
                                                  pair_cost(index, state_positions) for index in affected)
                child_occupants = list(state_occupants)
                child_occupants[first], child_occupants[second] = logical_second, logical_first
                child_positions = tuple(child_positions)
                child_paid = paid + 0.06 * weights[edge]
                if not path and edge == previous_swap:
                    child_paid += 0.6
                child = (child_potential, child_positions, tuple(child_occupants),
                         path + (edge,), child_paid)
                existing = successors.get(child_positions)
                if existing is None or child_potential + child_paid < existing[0] + existing[4]:
                    successors[child_positions] = child
        if not successors:
            break
        states = heapq.nsmallest(beam_width, successors.values(),
                                key=lambda state: (state[0] + state[4], state[3]))
    best = min(states, key=lambda state: (state[0] + state[4], state[3]))
    return best[3][0]


def run_configuration(instance, configuration):
    if not isinstance(configuration, dict):
        return BASELINE.route(instance, *configuration)
    fraction = configuration["weight_fraction"]
    edge_penalty = configuration["edge_penalty"]
    beam_width = configuration.get("beam_width", 0)
    beam_depth = configuration.get("beam_depth", 0)
    cache_key = (fraction, edge_penalty, beam_width, beam_depth)
    if cache_key not in WEIGHTED_ROUTERS:
        source = inspect.getsource(BASELINE.route)
        source = source.replace("1 + 0.15 * weights[tuple(sorted((first, second)))]",
                                "(1 - weight_fraction) + weight_fraction * weights[tuple(sorted((first, second)))]")
        source = source.replace("0.025 * weights[(first, second)]",
                                "edge_penalty * weights[(first, second)]")
        if beam_width:
            source = source.replace("emit_swap(best[1], best[2])", "emit_swap(*choose_beam_swap(positions, occupants, frontier, future, gates, distance, weights, adjacency, previous_swap, future_weight, beam_width, beam_depth))")
        namespace = dict(BASELINE.__dict__)
        namespace.update(weight_fraction=fraction, edge_penalty=edge_penalty,
                         choose_beam_swap=choose_beam_swap, beam_width=beam_width, beam_depth=beam_depth)
        exec(compile(source, "<portfolio-weighted-route>", "exec"), namespace)
        WEIGHTED_ROUTERS[cache_key] = namespace["route"]
    return WEIGHTED_ROUTERS[cache_key](instance, configuration["lookahead"],
                                     configuration["future_weight"],
                                     configuration["decay_weight"], configuration["seed"])


def select_configurations(mode):
    creators = {"baseline": configurations, "weighted": weighted_configurations,
                "beam": beam_configurations,
                "combined": lambda: configurations() + weighted_configurations() + beam_configurations()}
    return creators[mode]()


def solve(instance, selected=None):
    selected = configurations() if selected is None else selected
    return min((run_configuration(instance, configuration) for configuration in selected),
               key=lambda result: result[1])[0]


def worker(case, configuration_index, configuration):
    started = time.monotonic()
    answer, claimed_cost = run_configuration(case, configuration)
    metrics = CHECKER.validate(case, answer)
    if not math.isclose(metrics["cost"], claimed_cost, abs_tol=1e-8):
        raise ValueError("baseline cost differs from independent checker")
    return {"id": case["id"], "family": case["family"],
            "configuration_index": configuration_index,
            "configuration": configuration, "seconds": time.monotonic() - started,
            "metrics": metrics, "answer": answer}


def aggregate(records, manifest, cases):
    if len(records) != len(cases):
        return {"complete": False, "case_count": len(records)}
    ratios = {case["id"]: records[case["id"]]["metrics"]["cost"] /
              manifest["baseline"][case["id"]]["cost"] for case in cases}
    family_scores = {}
    for family in sorted({case["family"] for case in cases}):
        values = [ratios[case["id"]] for case in cases if case["family"] == family]
        family_scores[family] = 1 - math.exp(sum(map(math.log, values)) / len(values))
    core = 1 - math.exp(sum(map(math.log, ratios.values())) / len(ratios))
    return {"complete": True, "case_count": len(cases), "core_score": core,
            "worst_family_score": min(family_scores.values()), "family_scores": family_scores,
            "quality_target_met": core >= manifest["core_target"] and
            min(family_scores.values()) >= manifest["worst_family_target"],
            "failed_families": [family for family, score in family_scores.items()
                                if score < manifest["worst_family_target"]]}


def make_summary(cases, manifest, selected, results, best, errors, started, complete):
    by_configuration = {}
    per_case_seconds = {case["id"]: 0.0 for case in cases}
    for record in results:
        by_configuration.setdefault(record["configuration_index"], {})[record["id"]] = record
        per_case_seconds[record["id"]] += record["seconds"]
    individual = []
    for configuration_index, records in sorted(by_configuration.items()):
        individual.append({"configuration_index": configuration_index,
                           "configuration": selected[configuration_index],
                           **aggregate(records, manifest, cases)})
    completed = [record for record in individual if record["complete"]]
    portfolio = aggregate(best, manifest, cases)
    portfolio["selection"] = "minimum checked route cost using input only; no case-ID dispatch"
    portfolio["sandbox_resource_validation"] = "not performed; main session owns sandbox timing"
    portfolio["summed_worker_seconds"] = sum(per_case_seconds.values())
    portfolio["maximum_case_summed_worker_seconds"] = max(per_case_seconds.values(), default=0)
    portfolio["sequential_resource_budget_plausible"] = (
        complete and sum(per_case_seconds.values()) <= manifest["suite_seconds"] and
        max(per_case_seconds.values(), default=0) <= manifest["case_seconds"])
    case_records = []
    for case in cases:
        if case["id"] not in best:
            continue
        record = best[case["id"]]
        baseline = manifest["baseline"][case["id"]]
        case_records.append({"id": case["id"], "family": case["family"], "n": case["n"],
                             "gates": len(case["gates"]), "baseline_cost": baseline["cost"],
                             "baseline_swaps": baseline["swaps"],
                             "configuration_index": record["configuration_index"],
                             "configuration": record["configuration"], **record["metrics"],
                             "improvement": 1 - record["metrics"]["cost"] / baseline["cost"],
                             "summed_worker_seconds": per_case_seconds[case["id"]]})
    return {"status": "complete" if complete else "partial", "case_count": len(cases),
            "configuration_count": len(selected), "evaluations_completed": len(results),
            "evaluations_expected": len(cases) * len(selected),
            "wall_seconds": time.monotonic() - started,
            "targets": {key: manifest[key] for key in
                        ("core_target", "worst_family_target", "case_seconds", "suite_seconds")},
            "baseline_source_sha256": hashlib.sha256(
                (ROOT / "participant/baseline/solve.py").read_bytes()).hexdigest(),
            "cases_sha256": hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest(),
            "portfolio": portfolio,
            "best_single_configuration": max(completed, key=lambda record: record["core_score"],
                                             default=None),
            "configurations": individual, "cases": case_records,
            "evaluations": results, "errors": errors}


def search(arguments):
    started = time.monotonic()
    manifest = json.loads((ROOT / "evaluator/hidden/manifest.json").read_text())
    cases = json.loads((ROOT / "evaluator/hidden/cases.json").read_text())
    if len(cases) != 36:
        raise ValueError("expected all 36 private cases")
    selected = select_configurations(arguments.mode)[:arguments.configurations]
    route_directory = ROOT / "adversary/portfolio_routes"
    route_directory.mkdir(exist_ok=True)
    output = ROOT / "adversary" / arguments.output
    if not output.name.startswith("portfolio_results") or output.suffix != ".json":
        raise ValueError("output must be an owned portfolio_results*.json file")
    results = []
    best = {}
    errors = []
    first_index = 0
    if arguments.resume:
        previous = json.loads((ROOT / "adversary" / arguments.resume).read_text())
        previous_configurations = [record["configuration"] for record in previous["configurations"]]
        first_index = len(previous_configurations)
        selected = previous_configurations + selected
        results = previous["evaluations"]
        for record in results:
            case_id = record["id"]
            if case_id not in best or record["metrics"]["cost"] < best[case_id]["metrics"]["cost"]:
                best[case_id] = record
    jobs = iter((case, index, selected[index]) for index in range(first_index, len(selected))
                for case in cases)
    pending = {}
    exhausted = False
    last_report = started
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=arguments.workers)
    print(json.dumps({"event": "started", "cases": len(cases), "configurations": len(selected),
                      "workers": arguments.workers, "wall_limit": arguments.seconds}), flush=True)
    try:
        while time.monotonic() - started < arguments.seconds:
            while len(pending) < arguments.workers * 2 and not exhausted:
                try:
                    case, index, configuration = next(jobs)
                except StopIteration:
                    exhausted = True
                    break
                pending[executor.submit(worker, case, index, configuration)] = (case["id"], index)
            if not pending:
                break
            finished, _ = concurrent.futures.wait(pending, timeout=1,
                                                  return_when=concurrent.futures.FIRST_COMPLETED)
            for future in finished:
                case_id, index = pending.pop(future)
                try:
                    record = future.result()
                    answer = record.pop("answer")
                    results.append(record)
                    if case_id not in best or record["metrics"]["cost"] < best[case_id]["metrics"]["cost"]:
                        best[case_id] = record
                        (route_directory / f"{case_id}.json").write_text(json.dumps(answer) + "\n")
                except Exception as error:
                    errors.append({"id": case_id, "configuration_index": index, "error": repr(error)})
            if time.monotonic() - last_report >= 20:
                summary = make_summary(cases, manifest, selected, results, best, errors, started, False)
                output.write_text(json.dumps(summary, indent=2) + "\n")
                print(json.dumps({"event": "progress", "evaluations": len(results),
                                  "wall_seconds": summary["wall_seconds"],
                                  "portfolio": summary["portfolio"]}), flush=True)
                last_report = time.monotonic()
    finally:
        for process in list(executor._processes.values()):
            if process.is_alive():
                process.terminate()
        executor.shutdown(wait=True, cancel_futures=True)
    complete = exhausted and not pending and not errors
    summary = make_summary(cases, manifest, selected, results, best, errors, started, complete)
    output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"event": "finished", "status": summary["status"],
                      "evaluations": len(results), "portfolio": summary["portfolio"],
                      "best_single_configuration": summary["best_single_configuration"]}), flush=True)


def prune_route(case, answer, seconds):
    started = time.monotonic()
    operations = answer["operations"]
    metrics = CHECKER.validate(case, answer)
    original_cost = metrics["cost"]
    checks = 0
    deletions = 0
    for _ in range(12):
        changed = False
        for index in range(len(operations) - 1, -1, -1):
            if time.monotonic() - started >= seconds:
                break
            if operations[index][0] != "swap":
                continue
            choices = [None]
            choices.extend(following for following in range(index + 1, min(len(operations), index + 20))
                           if operations[following][0] == "swap")
            for following in choices:
                if time.monotonic() - started >= seconds:
                    break
                candidate = operations[:index] + operations[index + 1:]
                if following is not None:
                    del candidate[following - 1]
                checks += 1
                try:
                    candidate_metrics = CHECKER.validate(case, {"operations": candidate})
                except ValueError:
                    continue
                if candidate_metrics["cost"] + 1e-8 < metrics["cost"]:
                    operations = candidate
                    metrics = candidate_metrics
                    deletions += 1 if following is None else 2
                    changed = True
                    break
        if not changed or time.monotonic() - started >= seconds:
            break
    return {"id": case["id"], "family": case["family"], "metrics": metrics,
            "answer": {"operations": operations}, "original_cost": original_cost,
            "checks": checks, "deleted_swaps": deletions, "seconds": time.monotonic() - started}


def cleanup(arguments):
    started = time.monotonic()
    cases = json.loads((ROOT / "evaluator/hidden/cases.json").read_text())
    manifest = json.loads((ROOT / "evaluator/hidden/manifest.json").read_text())
    results = {}
    output_directory = ROOT / "adversary/portfolio_routes/cleaned"
    output_directory.mkdir(exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        pending = []
        for case in cases:
            answer = json.loads((ROOT / "adversary/portfolio_routes" / f"{case['id']}.json").read_text())
            pending.append(executor.submit(prune_route, case, answer, arguments.per_case_seconds))
        for future in concurrent.futures.as_completed(pending):
            record = future.result()
            answer = record.pop("answer")
            (output_directory / f"{record['id']}.json").write_text(json.dumps(answer) + "\n")
            results[record["id"]] = record
    summary = {"status": "complete", "kind": "generation-only postprocessed best route witnesses",
               "sandbox_resource_validation": "not performed", "wall_seconds": time.monotonic() - started,
               "portfolio": aggregate(results, manifest, cases), "cases": list(results.values())}
    (ROOT / "adversary" / arguments.output).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"event": "cleanup_finished", "portfolio": summary["portfolio"],
                      "deleted_swaps": sum(record["deleted_swaps"] for record in results.values()),
                      "wall_seconds": summary["wall_seconds"]}), flush=True)


def report(arguments):
    manifest = json.loads((ROOT / "evaluator/hidden/manifest.json").read_text())
    cases = json.loads((ROOT / "evaluator/hidden/cases.json").read_text())
    stages = {}
    for filename in ("portfolio_results.json", "portfolio_results_weighted.json",
                     "portfolio_results_beam.json", "portfolio_results_cleanup.json"):
        path = ROOT / "adversary" / filename
        if path.exists():
            data = json.loads(path.read_text())
            stages[filename] = {"status": data["status"], "wall_seconds": data["wall_seconds"],
                                "configuration_count": data.get("configuration_count"),
                                "evaluations_completed": data.get("evaluations_completed"),
                                "portfolio": data["portfolio"]}
    directory = ROOT / "adversary/portfolio_routes/final"
    directory.mkdir(exist_ok=True)
    records = {}
    for case in cases:
        candidates = []
        for subdirectory in ("", "cleaned"):
            path = ROOT / "adversary/portfolio_routes" / subdirectory / f"{case['id']}.json"
            if not path.exists():
                continue
            answer = json.loads(path.read_text())
            candidates.append((CHECKER.validate(case, answer), answer, str(path.relative_to(ROOT))))
        metrics, answer, source = min(candidates, key=lambda result: result[0]["cost"])
        baseline = manifest["baseline"][case["id"]]
        records[case["id"]] = {"id": case["id"], "family": case["family"], "n": case["n"],
                               "gates": len(case["gates"]), "metrics": metrics,
                               "baseline_cost": baseline["cost"], "baseline_swaps": baseline["swaps"],
                               "improvement": 1 - metrics["cost"] / baseline["cost"], "source": source}
        (directory / f"{case['id']}.json").write_text(json.dumps(answer) + "\n")
    final_scores = aggregate(records, manifest, cases)
    failures = {family: sorted([record for record in records.values() if record["family"] == family],
                              key=lambda record: record["improvement"])
                for family in final_scores["failed_families"]}
    summary = {"status": "complete", "stages": stages, "best_verified_witness_suite": final_scores,
               "classification": "generation-only feasibility evidence, not a sandbox-qualified submission",
               "algorithm_data_access": "route constructors use instance data only; offline search reads private cases",
               "resource_status": "main session owns timing; no sandbox resource pass claimed",
               "targets_unchanged": {key: manifest[key] for key in
                                     ("core_target", "worst_family_target", "case_seconds", "suite_seconds")},
               "root_family_failures": failures, "cases": list(records.values()),
               "notes": ["96 original route parameter settings were tested on every private case",
                         "54 weighted-distance variants and 16 static-frontier beam variants were added",
                         "Beam widths/depths were 6/3 and 16/4; this is not an optimality certificate",
                         "Every saved final route was freshly revalidated with the shared gate-faithful checker",
                         "No attempts were inspected and no participant or evaluator files were modified"]}
    (ROOT / "adversary" / arguments.output).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"event": "readiness", "scores": final_scores,
                      "failures": {family: [(record["id"], record["improvement"]) for record in selected]
                                   for family, selected in failures.items()}}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--solve-input", action="store_true")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--configurations", type=int, default=96)
    parser.add_argument("--mode", choices=("baseline", "weighted", "beam", "combined", "cleanup", "report"), default="baseline")
    parser.add_argument("--resume")
    parser.add_argument("--seconds", type=float, default=660)
    parser.add_argument("--per-case-seconds", type=float, default=12)
    parser.add_argument("--output", default="portfolio_results.json")
    arguments = parser.parse_args()
    if arguments.solve_input:
        print(json.dumps(solve(json.load(sys.stdin), select_configurations(arguments.mode)[:arguments.configurations])))
    elif arguments.mode == "cleanup":
        cleanup(arguments)
    elif arguments.mode == "report":
        report(arguments)
    else:
        search(arguments)
