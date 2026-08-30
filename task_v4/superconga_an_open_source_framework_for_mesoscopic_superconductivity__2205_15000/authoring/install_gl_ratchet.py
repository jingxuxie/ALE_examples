import datetime
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "concept_1"
SEARCH = ROOT / "adversary" / "ratchet_1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    proposal = json.loads((SEARCH / "focused_proposal" / "manifest.json").read_text())
    for relative, expected in proposal["sha256"].items():
        if digest(SEARCH / relative) != expected:
            raise RuntimeError("proposal changed: " + relative)
    records = []
    for source_record in proposal["cases"]:
        record = dict(source_record)
        for key, directory in (("case_path", "cases"), ("baseline_path", "baseline_fields"), ("witness_path", "witness_fields")):
            source = SEARCH / source_record[key]
            destination = ROOT / "evaluator" / "hidden" / "generation_2" / directory / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            record[key] = str(destination.relative_to(ROOT))
        records.append(record)
    target = json.loads((SEARCH / "focused_proposal" / "target.json").read_text())
    target.update({"generation": 2, "ratchet_generations": 1,
                   "release_frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    (ROOT / "evaluator" / "hidden" / "target.json").write_text(json.dumps(target, indent=2) + "\n")
    public_input = SEARCH / "candidate_public" / "input"
    if digest(public_input / "gl_model.py") != digest(ROOT / "participant" / "input" / "gl_model.py"):
        raise RuntimeError("public physics API changed unexpectedly")
    for name in ("API.md", "MODEL.md", "SOURCES.md", "development_targets.json"):
        shutil.copy2(public_input / name, ROOT / "participant" / "input" / name)
    for source in sorted((public_input / "cases").glob("*.json")):
        shutil.copy2(source, ROOT / "participant" / "input" / "cases" / source.name)
    champion = ROOT / "champions" / "generation_1" / "solve.py"
    if digest(champion) != proposal["champion_sha256"]:
        raise RuntimeError("champion hash mismatch")
    shutil.copy2(champion, ROOT / "participant" / "baseline" / "champion.py")
    qualified = ROOT / "champions" / "in_budget_generation_2"
    qualified.mkdir(exist_ok=True)
    for name in ("solve.py", "engine.py"):
        shutil.copy2(SEARCH / "challenger" / name, qualified / name)
    immutable = ["evaluator/hidden/target.json"]
    for record in records:
        immutable.extend(record[key] for key in ("case_path", "baseline_path", "witness_path"))
    manifest = {"schema_version": 1, "generation": 2, "cases": records,
                "proposal_sha256": digest(SEARCH / "focused_proposal" / "manifest.json"),
                "immutable_sha256": {relative: digest(ROOT / relative) for relative in immutable}}
    (ROOT / "evaluator" / "hidden" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    release = {"schema_version": 1, "generation": 2, "target_unchanged": False,
               "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    for group in ("participant", "evaluator"):
        files = {str(path.relative_to(ROOT)): digest(path) for path in sorted((ROOT / group).rglob("*"))
                 if path.is_file() and "__pycache__" not in path.parts and path.name != "release_manifest.json"}
        release[group] = {"files": files, "tree_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}
    (ROOT / "evaluator" / "release_manifest.json").write_text(json.dumps(release, indent=2) + "\n")
    print(json.dumps({"generation": 2, "cases": [(record["case_id"], record["baseline_energy"] - record["witness_energy"]) for record in records]}, indent=2))


if __name__ == "__main__":
    main()
