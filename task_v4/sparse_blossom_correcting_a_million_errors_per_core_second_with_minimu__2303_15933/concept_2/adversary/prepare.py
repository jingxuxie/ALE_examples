import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write_json(path, data):
    (ROOT / path).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def main():
    source = ROOT / "participant/workspace/check.py"
    specification = importlib.util.spec_from_file_location("public_checker", source)
    checker = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(checker)
    data = checker.load_submission(ROOT / "adversary/discovery_best.json")
    write_json("adversary/known_witness.json", data)
    write_json("adversary/known_public_metrics.json", checker.check(data))
    baseline = {"version": 1, "probabilities": [0.03 + 0.08 * ((17 * edge + 11) % 39) / 38 for edge in range(39)], "syndrome": [1, 6, 11, 16]}
    write_json("participant/baseline/weak.json", baseline)
    write_json("participant/baseline/metrics.json", checker.check(baseline))
    edges = []
    for cut in range(6):
        for row in range(4):
            if cut == 0:
                detectors, boundary = [row], "left"
            elif cut == 5:
                detectors, boundary = [16 + row], "right"
            else:
                detectors, boundary = [4 * (cut - 1) + row, 4 * cut + row], None
            edges.append({"id": len(edges), "detectors": detectors, "boundary": boundary, "logical": int(cut == 0)})
    for column in range(5):
        for row in range(3):
            edges.append({"id": len(edges), "detectors": [4 * column + row, 4 * column + row + 1], "boundary": None, "logical": 0})
    write_json("participant/input/graph.json", {"columns": 5, "rows": 4, "logical_distance": 6,
               "detectors": [{"id": 4 * column + row, "column": column, "row": row} for column in range(5) for row in range(4)], "edges": edges})
    metrics = json.loads((ROOT / "participant/baseline/metrics.json").read_text())
    (ROOT / "participant/baseline/README.md").write_text(
        "# Deterministic weak baseline\n\n`weak.json` is a valid, unoptimized fixture, not a claimed inversion.\n"
        "It uses `p[edge]=0.03+0.08*((17*edge+11)%39)/38` and syndrome\n"
        "`[1,6,11,16]`. No private search output is used. Regenerate the data with\n"
        "`/usr/bin/python3 -B baseline/make_baseline.py`.\n\n"
        f"- Progress score: {metrics['core_score']:.12g}\n"
        f"- Certified gap: {metrics['certified_gap']:.12g} nats\n"
        f"- Certified opposite posterior: {metrics['certified_opposite_posterior']:.12g}\n"
        f"- Certified syndrome probability: {metrics['certified_syndrome_probability']:.12g}\n"
        f"- Passed: {str(metrics['passed']).lower()}\n\n"
        "Full per-anchor values are in `metrics.json`; regenerate with\n"
        "`/usr/bin/python3 -B workspace/check.py baseline/weak.json`.\n")


if __name__ == "__main__":
    main()
