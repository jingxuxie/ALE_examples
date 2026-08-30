import argparse
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import resource
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PARTICIPANT = ROOT / "participant" if (ROOT / "participant").exists() else Path("/task")
sys.path.insert(0, str(PARTICIPANT / "workspace"))
from model import check, reverse_distances


def load_baseline():
    spec = importlib.util.spec_from_file_location("frozen_baseline", PARTICIPANT / "baseline" / "solve.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.plan


class Planner:
    def __init__(self, instance):
        self.instance = instance
        self.dimensions = instance["dimensions"]
        self.sizes = instance["sizes"]
        self.capacity = instance["capacity"]
        self.requests = instance["requests"]
        self.tables = {}
        self.targets = []
        for request in self.requests:
            target = request["mask"] * self.dimensions + request["layout"]
            self.targets.append((request["field"], target))
            if target not in self.tables:
                self.tables[target] = reverse_distances(instance, (request["mask"], request["layout"]))
        self.future = []
        for position, request in enumerate(self.requests):
            by_field = [[] for size in self.sizes]
            invalidated = set(request["updates"])
            for future in range(position + 1, len(self.requests)):
                field, target = self.targets[future]
                if field not in invalidated:
                    by_field[field].append((future - position, target))
                invalidated.update(self.requests[future]["updates"])
            self.future.append(by_field)

    def action(self, field, source, destination, keep):
        source_mask, source_layout = divmod(source, self.dimensions)
        mask, layout = divmod(destination, self.dimensions)
        if source_layout == layout:
            return ["axis", field, source_mask, source_layout, (source_mask ^ mask).bit_length() - 1, keep]
        return ["transpose", field, source_mask, source_layout, layout, keep]

    def weighted_future(self, scale, power, duplicates):
        output = []
        for position in range(len(self.requests)):
            by_field = []
            for field, future in enumerate(self.future[position]):
                weights = {}
                for delta, target in future:
                    weight = math.exp(-delta / scale) if power == 0 else (delta + scale) ** -power
                    if target not in weights:
                        weights[target] = weight
                    else:
                        weights[target] += duplicates * weight
                by_field.append([(self.tables[target][0], weight * self.sizes[field]) for target, weight in weights.items()])
            output.append(by_field)
        return output

    def solve(self, scale=8.0, power=1.0, duplicates=0.0, size_power=1.0, marginal=1.0):
        cache = set()
        actions = []
        memory = 0
        weighted = self.weighted_future(scale, power, duplicates)
        for position, request in enumerate(self.requests):
            field, target = self.targets[position]
            wanted = (field, target)
            if target and wanted not in cache:
                distance, successor = self.tables[target]
                sources = [0] + sorted(node for cached_field, node in cache if cached_field == field)
                source = min(sources, key=lambda node: (distance[node], node))
                while source != target:
                    destination = successor[source]
                    destination_key = (field, destination)
                    source_key = (field, source)
                    virtual = cache | {destination_key}
                    total = memory + self.sizes[field]
                    removed = []
                    while total > self.capacity:
                        values = []
                        for candidate in sorted(virtual - {destination_key}):
                            candidate_field, candidate_node = candidate
                            others = [0] + [node for cached_field, node in virtual if cached_field == candidate_field and node != candidate_node]
                            value = 0.0
                            for distances, weight in weighted[position][candidate_field]:
                                reference = min(distances[node] for node in others)
                                improvement = max(0, reference - distances[candidate_node])
                                absolute = max(0, distances[0] - distances[candidate_node])
                                value += weight * (marginal * improvement + (1 - marginal) * absolute)
                            values.append((value / self.sizes[candidate_field] ** size_power, candidate))
                        victim = min(values)[1]
                        virtual.remove(victim)
                        removed.append(victim)
                        total -= self.sizes[victim[0]]
                    keep = source_key not in removed
                    for victim_field, victim_node in removed:
                        if (victim_field, victim_node) != source_key:
                            mask, layout = divmod(victim_node, self.dimensions)
                            actions.append(["drop", victim_field, mask, layout])
                    actions.append(self.action(field, source, destination, keep))
                    cache = virtual
                    memory = total
                    source = destination
            actions.append(["read"])
            updates = set(request["updates"])
            cache = {key for key in cache if key[0] not in updates}
            memory = sum(self.sizes[cached_field] for cached_field, node in cache)
        return {"actions": actions}

    def beam(self, width=64, local_width=6, scale=3.0, source_count=2, heuristic_weight=1.0, waypoints=0, anchors=False):
        weighted = self.weighted_future(scale, 0.0, 0.0)
        frontier = {(): (0, None)}
        for position, request in enumerate(self.requests):
            field, target = self.targets[position]
            distance, successor = self.tables[target]
            anchor_nodes = []
            if anchors:
                target_mask, target_layout = divmod(target, self.dimensions)
                seen = set()
                for delta, future_target in self.future[position][field]:
                    if future_target in seen:
                        continue
                    seen.add(future_target)
                    future_mask, future_layout = divmod(future_target, self.dimensions)
                    for mask in [target_mask & future_mask, target_mask | future_mask]:
                        for layout in sorted({target_layout, future_layout}):
                            node = mask * self.dimensions + layout
                            if node and node != target and node not in anchor_nodes:
                                anchor_nodes.append(node)
                                if node not in self.tables:
                                    self.tables[node] = reverse_distances(self.instance, (mask, layout))
                    if len(seen) >= 2:
                        break
            potential_cache = {}
            release_cache = {}

            def potential(cache):
                if cache not in potential_cache:
                    by_field = [[] for size in self.sizes]
                    for cached_field, node in cache:
                        by_field[cached_field].append(node)
                    value = 0.0
                    for cached_field, nodes in enumerate(by_field):
                        if nodes:
                            for distances, weight in weighted[position][cached_field]:
                                value += weight * max(0, distances[0] - min(distances[node] for node in nodes))
                    potential_cache[cache] = value * heuristic_weight * math.exp(1.0 / scale)
                return potential_cache[cache]

            def releases(cache):
                if cache not in release_cache:
                    needed = sum(self.sizes[cached_field] for cached_field, node in cache) + self.sizes[field] - self.capacity
                    choices = []
                    if needed <= 0:
                        choices = [()]
                    else:
                        for count in range(1, len(cache) + 1):
                            for subset in itertools.combinations(cache, count):
                                weights = [self.sizes[cached_field] for cached_field, node in subset]
                                total = sum(weights)
                                if total >= needed and total - min(weights) < needed:
                                    choices.append(subset)
                    release_cache[cache] = choices
                return release_cache[cache]

            expanded = {}

            def finish(cache, cost, trace, chunk):
                updated = tuple(key for key in cache if key[0] not in request["updates"])
                previous = expanded.get(updated)
                if previous is None or cost < previous[0]:
                    expanded[updated] = (cost, (trace, chunk + [["read"]]))

            for cache, (cost, trace) in frontier.items():
                if target == 0 or (field, target) in cache:
                    finish(cache, cost, trace, [])
                    continue
                sources = sorted([0] + [node for cached_field, node in cache if cached_field == field], key=lambda node: (distance[node], node))[:source_count]
                for original in sources:
                    middle_nodes = [target]
                    for delta, candidate in self.future[position][field]:
                        if len(middle_nodes) >= waypoints + 1:
                            break
                        if candidate and candidate not in middle_nodes and (field, candidate) not in cache:
                            middle_nodes.append(candidate)
                    if anchors:
                        candidates = [node for node in anchor_nodes if node not in middle_nodes and (field, node) not in cache]
                        candidates.sort(key=lambda node: self.sizes[field] * (self.tables[node][0][original] + distance[node] - distance[original]) - potential(((field, node),)))
                        middle_nodes.extend(candidates[:3])
                    for middle in middle_nodes:
                        route = []
                        current = original
                        visited = {original}
                        conflict = False
                        for goal in [middle, target] if middle != target else [target]:
                            goal_successor = self.tables[goal][1]
                            while current != goal:
                                destination = goal_successor[current]
                                if (field, destination) in cache or destination in visited:
                                    conflict = True
                                    break
                                route.append((current, destination))
                                visited.add(destination)
                                current = destination
                            if conflict:
                                break
                        if conflict:
                            continue
                        route_cost = self.tables[middle][0][original] + (distance[middle] if middle != target else 0)
                        local = {cache: []}
                        for source, destination in route:
                            following = {}
                            for previous_cache, chunk in local.items():
                                for removed in releases(previous_cache):
                                    remaining = tuple(sorted([key for key in previous_cache if key not in removed] + [(field, destination)]))
                                    if remaining in following:
                                        continue
                                    steps = []
                                    for victim_field, victim_node in removed:
                                        if (victim_field, victim_node) != (field, source):
                                            mask, layout = divmod(victim_node, self.dimensions)
                                            steps.append(["drop", victim_field, mask, layout])
                                    steps.append(self.action(field, source, destination, (field, source) not in removed))
                                    following[remaining] = chunk + steps
                            local = dict(sorted(following.items(), key=lambda item: (-potential(item[0]), item[0]))[:local_width])
                        for result_cache, chunk in local.items():
                            finish(result_cache, cost + self.sizes[field] * route_cost, trace, chunk)
            frontier = dict(sorted(expanded.items(), key=lambda item: (item[1][0] - potential(item[0]), item[1][0], item[0]))[:width])
        cost, trace = min(frontier.values(), key=lambda item: item[0])
        chunks = []
        while trace is not None:
            trace, chunk = trace
            chunks.append(chunk)
        answer = {"actions": [action for chunk in reversed(chunks) for action in chunk]}
        if check(self.instance, answer)["cost"] != cost:
            raise AssertionError("Beam internal cost mismatch")
        return answer


def configurations(level):
    parameters = []
    for scale in [1.0, 3.0, 8.0, 20.0]:
        for power in [0.0, 1.0, 2.0]:
            parameters.append(dict(scale=scale, power=power, duplicates=0.0, size_power=1.0, marginal=1.0))
    if level >= 2:
        for scale in [1.0, 5.0, 15.0]:
            for duplicates in [0.0, 0.5, 1.0]:
                for size_power in [0.0, 1.0, 2.0]:
                    for marginal in [0.5, 1.0]:
                        parameters.append(dict(scale=scale, power=1.0, duplicates=duplicates, size_power=size_power, marginal=marginal))
    return parameters


def score(rows):
    families = {}
    for family in sorted({row["family"] for row in rows}):
        ratios = [row["ratio"] for row in rows if row["family"] == family]
        families[family] = 1 - math.exp(sum(map(math.log, ratios)) / len(ratios))
    overall = 1 - math.exp(sum(math.log(row["ratio"]) for row in rows) / len(rows))
    return {"core_score": overall, "family_scores": families, "worst_family_score": min(families.values()), "cost": sum(row["cost"] for row in rows), "baseline_cost": sum(row["baseline_cost"] for row in rows), "target_met": overall >= 0.20 and min(families.values()) >= 0.08}


def measure(level, output):
    started = time.perf_counter()
    cpu_started = time.process_time()
    cases_path = ROOT / "evaluator" / "hidden" / "cases.json"
    cases = json.loads(cases_path.read_text())
    baseline = load_baseline()
    rows = []
    trials = []
    answers = []
    configs = configurations(level)
    for case in cases:
        case_started = time.perf_counter()
        planner = Planner(case["instance"])
        best_answer = baseline(case["instance"])
        best = check(case["instance"], best_answer)
        if best["cost"] != case["baseline"]["cost"]:
            raise AssertionError("Frozen baseline cost mismatch")
        selected = "baseline"
        for config in configs:
            answer = planner.solve(**config)
            result = check(case["instance"], answer)
            trials.append({"id": case["id"], "config": config, "cost": result["cost"]})
            if result["cost"] < best["cost"]:
                best_answer, best, selected = answer, result, config
        if level >= 3:
            for scale in [1.5, 3.0, 6.0]:
                config = dict(width=96, local_width=8, scale=scale, source_count=2)
                answer = planner.beam(**config)
                result = check(case["instance"], answer)
                trials.append({"id": case["id"], "beam": config, "cost": result["cost"]})
                if result["cost"] < best["cost"]:
                    best_answer, best, selected = answer, result, {"beam": config}
        row = {"id": case["id"], "family": case["family"], "baseline_cost": case["baseline"]["cost"], "ratio": best["cost"] / case["baseline"]["cost"], "selected": selected, "elapsed_seconds": time.perf_counter() - case_started, **best}
        rows.append(row)
        answers.append(best_answer)
        print(json.dumps(row, separators=(",", ":")), flush=True)
        partial = {**score(rows), "cases": rows, "trials": trials, "complete": len(rows) == len(cases), "elapsed_seconds": time.perf_counter() - started, "cpu_seconds": time.process_time() - cpu_started, "maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "level": level, "hidden_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest()}
        output.write_text(json.dumps(partial, indent=2) + "\n")
        output.with_suffix(".plans.jsonl").write_text("".join(json.dumps(answer, separators=(",", ":")) + "\n" for answer in answers))
    print(json.dumps({key: value for key, value in partial.items() if key not in ("cases", "trials")}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--measure", action="store_true")
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("search_level1.json"))
    args = parser.parse_args()
    if args.measure:
        measure(args.level, args.output)
    else:
        baseline = load_baseline()
        for line in sys.stdin:
            if not line.strip():
                continue
            instance = json.loads(line)
            planner = Planner(instance)
            best_answer = baseline(instance)
            best_cost = check(instance, best_answer)["cost"]
            for config in configurations(args.level):
                answer = planner.solve(**config)
                cost = check(instance, answer)["cost"]
                if cost < best_cost:
                    best_answer, best_cost = answer, cost
            if args.level >= 3:
                for scale in [1.5, 3.0, 6.0]:
                    answer = planner.beam(width=96, local_width=8, scale=scale, source_count=2)
                    cost = check(instance, answer)["cost"]
                    if cost < best_cost:
                        best_answer, best_cost = answer, cost
            print(json.dumps(best_answer, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
