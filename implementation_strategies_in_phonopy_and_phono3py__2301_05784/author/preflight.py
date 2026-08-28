"""Audit public/private separation and freeze the four initial pilot manifests."""

import ast
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent.parent
reports = {}
failures = []
for name in ("fitting", "cubic", "grid", "polar"):
    concept = ROOT / "concepts" / name
    public = concept / "participant"
    private = concept / "private"
    manifest_path = private / "challenge_pool/manifest.json"
    if not manifest_path.exists():
        failures.append(name + ": missing manifest")
        continue
    cases = json.loads(manifest_path.read_text())
    if isinstance(cases, dict):
        cases = cases["cases"]
    task = (public / "TASK.md").read_text()
    if "2301.05784" in task or "implementation strategies" in task.lower():
        failures.append(name + ": paper identity in task")
    for path in public.rglob("*"):
        if path.is_symlink() and not path.resolve().is_relative_to(public.resolve()):
            failures.append(str(path) + ": outward public symlink")
        if path.is_file() and path.suffix == ".py":
            ast.parse(path.read_text(), filename=str(path))
    if any((concept / "attempt").iterdir()):
        failures.append(name + ": nonempty attempt")
    schemas = {}
    for case in cases:
        for key in ("input", "reference", "baseline"):
            if not (private / case[key]).is_file():
                failures.append(name + ": missing " + case[key])
        with zipfile.ZipFile(private / case["input"]) as archive:
            keys = sorted(Path(member).stem for member in archive.namelist())
        schemas[case["id"]] = keys
        suspicious = [key for key in keys if key.startswith(("expected", "reference", "answer", "heldout_f"))]
        if suspicious:
            failures.append(name + ": answer-like input fields " + repr(suspicious))
        if name == "fitting" and any(key in keys for key in ("fc2", "fc3")):
            failures.append(name + ": force-constant targets exposed")
    reports[name] = {
        "cases": len(cases), "families": sorted(set(case["family"] for case in cases)),
        "splits": {split: sum(case["split"] == split for case in cases) for split in sorted(set(case["split"] for case in cases))},
        "task_words": len(task.split()), "input_schemas": schemas,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "attempt_empty": not any((concept / "attempt").iterdir()),
    }
report = {"pilots": reports, "failures": failures, "passed": not failures}
(ROOT / "author/preflight.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"passed": not failures, "failures": failures,
                  "pilots": {name: {key: value for key, value in result.items() if key != "input_schemas"}
                             for name, result in reports.items()}}, indent=2))
if failures:
    raise SystemExit(1)
