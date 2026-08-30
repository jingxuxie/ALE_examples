import json
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
ASSETS = ROOT.parent.parent / "participant"
sys.path.insert(0, str(ASSETS / "workspace"))
from channel import risk


def main():
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    baselines = {item["name"]: item["baseline"]["worst_risk"]
                 for item in json.loads((ASSETS / "baseline" / "scores.json").read_text())}
    results = []
    for source in sorted((ASSETS / "input").glob("*.json")):
        destination = ROOT / (source.stem + "_answer.json")
        started = time.monotonic()
        subprocess.run([sys.executable, str(ROOT / "solve.py"), "--input", str(source),
                        "--output", str(destination), "--seconds", str(seconds)], check=True)
        elapsed = time.monotonic() - started
        answer = json.loads(destination.read_text())
        instance = json.loads(source.read_text())
        selected = answer["selected"]
        assert selected == sorted(set(selected))
        assert len(selected) <= instance["budget"]
        assert len(answer["correction"]) == 1 << len(selected)
        assert all(bit in [0, 1] for bit in answer["correction"])
        risks = risk(instance, answer)
        score = max(risks)
        result = {"name": source.stem, "seconds": elapsed, "risks": risks,
                  "worst": score, "reduction": 1 - score / baselines[source.stem],
                  "selected": selected}
        results.append(result)
        print(json.dumps(result), flush=True)
    (ROOT / "benchmark_results.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
