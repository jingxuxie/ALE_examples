import argparse
import hashlib
import json
from pathlib import Path


SETTINGS = {
    "max_fault_weight": 36,
    "max_edge_degree": 112,
    "max_intermediate_detector_weight": 104,
    "beam_width": 64,
    "nonincreasing_after_seed": True,
}


def search(model):
    columns = [int(column, 16) for column in model["columns"]]
    degrees = [column.bit_count() for column in columns]
    frontier = [((), 0, 0)]
    layers = []
    found = []
    for depth in range(1, SETTINGS["max_fault_weight"] + 1):
        counters = {
            "depth": depth, "parents": len(frontier), "extensions": 0,
            "edge_pruned": 0, "syndrome_pruned": 0, "monotone_pruned": 0,
            "beam_pruned": 0, "retained": 0, "minimum_retained_syndrome": None,
        }
        candidates = []
        for support, syndrome, logical in frontier:
            start = support[-1] + 1 if support else 0
            for fault in range(start, model["num_faults"]):
                counters["extensions"] += 1
                if degrees[fault] > SETTINGS["max_edge_degree"]:
                    counters["edge_pruned"] += 1
                    continue
                next_syndrome = syndrome ^ columns[fault]
                if next_syndrome.bit_count() > SETTINGS["max_intermediate_detector_weight"]:
                    counters["syndrome_pruned"] += 1
                    continue
                if support and next_syndrome.bit_count() > syndrome.bit_count():
                    counters["monotone_pruned"] += 1
                    continue
                next_support = support + (fault,)
                next_logical = logical ^ model["observable"][fault]
                if next_syndrome == 0 and next_logical == 1:
                    found = list(next_support)
                    break
                candidates.append((next_support, next_syndrome, next_logical))
            if found:
                break
        if found:
            layers.append(counters)
            break
        candidates.sort(key=lambda state: (state[1].bit_count(), 1 - state[2], state[0]))
        frontier = candidates[:SETTINGS["beam_width"]]
        counters["beam_pruned"] = max(0, len(candidates) - len(frontier))
        counters["retained"] = len(frontier)
        if frontier:
            counters["minimum_retained_syndrome"] = frontier[0][1].bit_count()
        layers.append(counters)
        if not frontier:
            break
    return {
        "implementation": "supplied_overconfident_wrapper_v1_not_stim",
        "settings": dict(SETTINGS), "faults": found,
        "status": "counterexample_found" if found else "claimed_distance_above_bound",
        "claimed_certified": not bool(found),
        "claimed_distance_lower_bound": None if found else SETTINGS["max_fault_weight"] + 1,
        "search_exhaustive": False,
        "stopping_reason": "witness" if found else (
            "retained_frontier_empty" if not frontier else "weight_cutoff"
        ),
        "total_extensions": sum(layer["extensions"] for layer in layers),
        "layers": layers,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the deliberately overconfident baseline.")
    parser.add_argument("--output", type=Path, default=Path("witness.json"))
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    model_path = Path(__file__).with_name("model.json")
    model_bytes = model_path.read_bytes()
    result = search(json.loads(model_bytes))
    result["model_sha256"] = hashlib.sha256(model_bytes).hexdigest()
    arguments.output.write_text(json.dumps({"faults": result["faults"]}) + "\n")
    if arguments.report:
        arguments.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
