import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parent.parent / "participant"
sys.path.insert(0, str(PARTICIPANT))
from reference_core import circuit_weights, score_metrics, summarize
from reference_faults import omission_profile

parser = argparse.ArgumentParser()
parser.add_argument("--validate", action="store_true")
parser.add_argument("--top", type=int, default=4)
args = parser.parse_args()
spec = json.loads((PARTICIPANT / "input/spec.json").read_text())
selected = []
for family in spec["families"]:
    candidates = []
    for path in ROOT.glob(family["id"] + "_*.json"):
        try:
            circuit = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        metrics = summarize(family["n"], circuit_weights(family["n"], circuit["layers"]))
        score, failed = score_metrics(metrics, family["targets"])
        candidates.append((score, path.name, circuit, metrics, failed))
    candidates.sort(key=lambda item: (item[0], -len(item[4])), reverse=True)
    best = None
    for score, name, circuit, metrics, failed in candidates[:args.top]:
        print(name, "ideal", score, "minimum", [metrics[direction][stratum]["minimum"]
              for direction in ("forward", "inverse") for stratum in ("single", "double")],
              "mean", [round(metrics[direction][stratum]["mean"], 5)
              for direction in ("forward", "inverse") for stratum in ("single", "double")], flush=True)
        if args.validate:
            faults = omission_profile(family["n"], circuit["layers"])
            score = min(score, faults["core_score"])
            print("  faults", faults["minimum"], faults["failed_scenario_counts"], flush=True)
            report = {"source": name, "ideal": metrics, "faults": faults, "score": score}
            (ROOT / (name.removesuffix(".json") + ".check")).write_text(json.dumps(report, indent=2))
        if best is None or score > best[0]:
            best = (score, circuit)
        if args.validate and score == 1:
            break
    if best:
        selected.append(best[1])
if len(selected) == len(spec["families"]):
    (ROOT / "artifact.json").write_text(json.dumps({"schema_version": 1, "circuits": selected}, indent=2) + "\n")
