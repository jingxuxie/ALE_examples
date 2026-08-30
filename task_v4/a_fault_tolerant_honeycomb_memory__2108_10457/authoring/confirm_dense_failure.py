import hashlib
import json
import math
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "concept_2/evaluator"))
from design_common import ambiguity, generate_supports, load_case, read_design, selected_columns


def binary_rank(vectors):
    rows = list(vectors)
    rank = 0
    while rows:
        pivot = max(rows)
        if not pivot:
            return rank
        leading = 1 << (pivot.bit_length() - 1)
        rows.remove(pivot)
        rows = [row ^ pivot if row & leading else row for row in rows]
        rank += 1
    return rank


def wilson_interval(successes, count, normal_quantile=2.5758293035489004):
    estimate = successes / count
    variance_term = normal_quantile ** 2 / count
    center = (estimate + variance_term / 2) / (1 + variance_term)
    half_width = normal_quantile * math.sqrt(
        estimate * (1 - estimate) / count + normal_quantile ** 2 / (4 * count ** 2)
    ) / (1 + variance_term)
    return [center - half_width, center + half_width]


def main():
    started = time.monotonic()
    concept = ROOT / "concept_2"
    case = load_case(concept / "participant/input/scale_1.json.gz")
    seed = 906130527
    records = generate_supports(case, seed, 32768, {"dense_iid": [0.32]})
    candidates = {
        "supplied_champion": concept / "participant/baseline/design.json",
        "fresh_dense_attempt_v2": concept / "attempts/v_2/design.json",
    }
    reports = {}
    for name, path in candidates.items():
        axes = read_design(path)
        columns = selected_columns(case, axes)
        successes = 0
        cross_checks = 0
        for index, record in enumerate(records):
            vectors = [columns[slot] for slot in record["support"]]
            logical_rank = ambiguity(vectors)
            successes += logical_rank == 0
            if index < 256:
                difference = binary_rank(vectors) - binary_rank(vector >> 4 for vector in vectors)
                assert difference == logical_rank
                cross_checks += 1
        interval = wilson_interval(successes, len(records))
        reports[name] = {
            "artifact": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "correct": successes,
            "count": len(records),
            "fraction": successes / len(records),
            "wilson_99_percent_interval": interval,
            "upper_endpoint_below_required_group_floor": interval[1] < 0.60,
            "independent_rank_difference_cross_checks": cross_checks,
        }
    result = {
        "purpose": "Post-submission uncertainty audit, not an extra hidden pass criterion or an achievability proof.",
        "scale": 1,
        "data_qubits": 24,
        "density": 0.32,
        "seed": seed,
        "supports": len(records),
        "required_group_floor": 0.60,
        "candidates": reports,
        "seconds": time.monotonic() - started,
    }
    destination = concept / "adversary/dense_failure_confirmation.json"
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
