import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
pairs = [
    ("participant/workspace/simulator.py", "evaluator/hidden/simulator.py"),
    ("participant/workspace/search_api.py", "evaluator/hidden/search_api.py"),
    ("participant/input/protocol.json", "evaluator/hidden/protocol.json"),
]
sections = ["*** Begin Patch"]
for source, destination in pairs:
    sections.append("*** Add File: " + destination)
    sections.extend("+" + line for line in (ROOT / source).read_text().splitlines())
sections.append("*** End Patch")
subprocess.run(["apply_patch"], input="\n".join(sections) + "\n", text=True, cwd=ROOT, check=True)
paths = sorted(list((ROOT / "participant").rglob("*.py")) + list((ROOT / "participant").rglob("*.md")) + list((ROOT / "participant").rglob("*.json")) + list((ROOT / "evaluator").rglob("*.py")) + list((ROOT / "evaluator" / "hidden").glob("protocol.json")))
manifest = {
    "frozen_on": "2026-08-28", "protocol_id": "nonlinear_false_convergence_v1",
    "sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
}
content = json.dumps(manifest, indent=2) + "\n"
patch = "*** Begin Patch\n*** Add File: evaluator/hidden/freeze_manifest.json\n" + "\n".join("+" + line for line in content.splitlines()) + "\n*** End Patch\n"
subprocess.run(["apply_patch"], input=patch, text=True, cwd=ROOT, check=True)
