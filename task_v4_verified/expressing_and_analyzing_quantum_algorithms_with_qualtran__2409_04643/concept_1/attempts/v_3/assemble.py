import json
import os
from pathlib import Path
import sys


participant = Path(os.environ["P"])
sys.path.insert(0, str(participant / "workspace"))
from model import baseline_order, improvement, metrics


cases = json.loads((participant / "input/workloads.json").read_text())["cases"]
schedules = {}
records = []
for case_index, case in enumerate(cases):
    baseline_metrics = metrics(case, baseline_order(case))
    candidates = []
    for prefix in ["best", "hot", "guided", "beam"]:
        path = Path(f"{prefix}{case_index}.txt")
        if not path.is_file():
            continue
        order = [int(value) for value in path.read_text().split()]
        try:
            result = metrics(case, order)
        except ValueError:
            continue
        if result["peak"] * 20 > baseline_metrics["peak"] * 21:
            continue
        ratio = improvement(baseline_metrics, result)
        candidates.append((ratio, order, result, path.name))
    ratio, order, result, source = max(candidates, key=lambda candidate: candidate[0])
    schedules[case["id"]] = order
    records.append({"id": case["id"], "source": source, "ratio": ratio, **result})
Path("schedules.json").write_text(json.dumps({"schedules": schedules}, separators=(",", ":")) + "\n")
Path("selected_metrics.json").write_text(json.dumps(records, indent=2) + "\n")
print(json.dumps(records, indent=2))
