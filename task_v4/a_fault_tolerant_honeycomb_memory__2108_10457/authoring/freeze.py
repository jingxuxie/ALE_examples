import hashlib
import json
from pathlib import Path
import sys


concept = Path(sys.argv[1]).resolve()
hashes = {}
for directory in [concept / "participant", concept / "evaluator" / "hidden"]:
    for path in sorted(directory.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            hashes[str(path.relative_to(concept))] = hashlib.sha256(path.read_bytes()).hexdigest()
for path in [concept / "evaluator" / "evaluate.py", concept / "evaluator" / "protocol.json"]:
    if path.is_file():
        hashes[str(path.relative_to(concept))] = hashlib.sha256(path.read_bytes()).hexdigest()
(concept / "evaluator" / "frozen.json").write_text(json.dumps({"sha256": hashes}, indent=2) + "\n")
