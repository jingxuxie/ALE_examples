import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from contract import volume


def root_lower_bound(case, term):
    inputs = term["inputs"]
    complete = (1 << len(inputs)) - 1
    boundaries = {}
    for mask in range(1, complete + 1):
        inside = set().union(*(set(reference[1]) for position, reference in enumerate(inputs) if mask >> position & 1))
        outside = set(term["output"]).union(*(set(reference[1]) for position, reference in enumerate(inputs) if not mask >> position & 1))
        boundaries[mask] = inside & outside
    options = []
    for mask in range(1, complete):
        first = boundaries[mask]
        second = boundaries[complete ^ mask]
        first_size = volume(first, case["index_types"], case["dimensions"]) if mask & (mask - 1) else 0
        complement = complete ^ mask
        second_size = volume(second, case["index_types"], case["dimensions"]) if complement & (complement - 1) else 0
        output_size = volume(term["output"], case["index_types"], case["dimensions"])
        if first_size + second_size + output_size <= case["memory_cap"]:
            axes = first | second
            options.append(volume(axes, case["index_types"], case["dimensions"]) * (2 if axes - set(term["output"]) else 1))
    return min(options)


def main():
    manifest = json.loads((ROOT / "evaluator/hidden/manifest.json").read_text())
    records = []
    for entry in manifest["cases"]:
        case = json.loads((ROOT / "evaluator/hidden" / entry["file"]).read_text())
        lower = sum(root_lower_bound(case, term) for term in case["terms"])
        records.append({"case": entry["file"], "family": entry["family"],
                        "distinct_root_work_lower_bound": lower,
                        "speedup_upper_bound": entry["baseline"]["flops"] / lower})
    core = math.exp(sum(math.log(record["speedup_upper_bound"]) for record in records) / len(records))
    result = {"geomean_speedup_upper_bound": core, "cases": records,
              "qualification": "Bound assumes conventional subset contractions with early elimination, as in supplied source networks; no achievability is implied."}
    (ROOT / "adversary/root_bound.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"geomean_speedup_upper_bound": core, "minimum_case_upper_bound": min(record["speedup_upper_bound"] for record in records)}))


if __name__ == "__main__":
    main()
