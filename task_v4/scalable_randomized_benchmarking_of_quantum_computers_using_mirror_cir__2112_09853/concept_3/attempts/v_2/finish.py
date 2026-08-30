import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parent.parent / "participant"
sys.path.insert(0, str(PARTICIPANT))
from scorer import evaluate

parser = argparse.ArgumentParser()
parser.add_argument("--wait", type=float, default=0)
args = parser.parse_args()
deadline = time.monotonic() + args.wait
families = ("ladder16", "grid20", "bridge18")
while True:
    sources = {}
    for family in families:
        for path in sorted(ROOT.glob(family + "_*.log")):
            if "SUCCESS" in path.read_text():
                sources[family] = path.with_suffix(".json")
                break
    if len(sources) == len(families):
        circuits = [json.loads(sources[family].read_text()) for family in families]
        artifact = ROOT / "artifact.json"
        artifact.write_text(json.dumps({"schema_version": 1, "circuits": circuits}, indent=2) + "\n")
        report = evaluate(artifact, PARTICIPANT / "input/spec.json")
        (ROOT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("SOURCES", {family: path.name for family, path in sources.items()}, flush=True)
        print("RESULT", report["valid"], report["passed"], report["core_score"], flush=True)
        break
    if time.monotonic() >= deadline:
        print("Pending", [family for family in families if family not in sources], flush=True)
        break
    time.sleep(5)
