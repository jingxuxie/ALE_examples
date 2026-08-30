import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parent.parent / "participant"
sys.path.insert(0, str(PARTICIPANT))
from scorer import evaluate

circuits = []
sources = {}
for family in ("ladder16", "grid20", "bridge18"):
    ranked = []
    for path in sorted(ROOT.glob(family + "_exact*.raw")):
        result = subprocess.check_output(["./search_symmetric", family + ".cfg", "report", "0", "0", path.name],
                                         env={**os.environ, "REPORT": "1"}, text=True)
        fields = {key: float(value) for key, value in re.findall(r"(\w+)=([0-9.e+-]+)", result)}
        ranked.append((fields["score"], -fields["faults"], -fields["cost"], path))
    ranked.sort(reverse=True)
    score, failures, cost, path = ranked[0]
    print(family, path.name, "score", score, "faults", -failures, "cost", -cost, flush=True)
    circuits.append(json.loads(path.with_suffix(".json").read_text()))
    sources[family] = path.name
artifact = ROOT / "best_so_far.json"
artifact.write_text(json.dumps({"schema_version": 1, "circuits": circuits}, indent=2) + "\n")
report = evaluate(artifact, PARTICIPANT / "input/spec.json")
(ROOT / "best_so_far_report.json").write_text(json.dumps(report, indent=2) + "\n")
print("Verified", report["valid"], report["passed"], report["core_score"], flush=True)
(ROOT / "best_so_far_sources.json").write_text(json.dumps(sources, indent=2) + "\n")
