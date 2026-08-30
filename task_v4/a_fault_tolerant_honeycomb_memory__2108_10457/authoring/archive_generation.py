import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("concept")
parser.add_argument("generation", type=int)
arguments = parser.parse_args()
concept = ROOT / arguments.concept
destination = concept / "generations" / f"generation_{arguments.generation}"
destination.mkdir(parents=True, exist_ok=False)
for directory in ["participant", "evaluator"]:
    shutil.copytree(concept / directory, destination / directory)
for filename in ["status.json", "FILE_MANIFEST.json"]:
    if (concept / filename).exists():
        shutil.copy2(concept / filename, destination / filename)
score = json.loads((concept / "attempts" / f"v_{arguments.generation}_score.json").read_text())
snapshot = {"concept": arguments.concept, "generation": arguments.generation,
            "archived_utc": datetime.now(timezone.utc).isoformat(), "fresh_agent_score": score,
            "status": "solved" if score.get("passed") else "not_solved",
            "note": "Frozen pre-ratchet task. Use authoring/replay_generation.py for evaluator replay with the shared isolated launcher."}
(destination / "snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n")
print(destination)
