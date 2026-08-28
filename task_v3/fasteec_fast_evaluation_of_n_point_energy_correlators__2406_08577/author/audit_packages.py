import hashlib
import json
from pathlib import Path


root = Path(__file__).resolve().parent.parent
forbidden = {"eec_nu_point.h", "eec_higher_weight.h", "eec_fast_kt.cc", "eec_fast_weight.cc", "eec_fast_kt_weight.cc", "eec_angles.cc", "new_enc_3particle.cc", "new_enc_4particle.cc", "ewocs.cc"}
records = []
for kind in ["weighted", "fractional", "resolved", "ewoc"]:
    participant = root / "pilots" / kind / "participant"
    files = [path for path in participant.rglob("*") if path.is_file()]
    run_path = root / "author" / "runs" / (kind + "_pilot.running.json")
    record = json.loads(run_path.read_text())
    hashes = {str(path.relative_to(participant)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    task = (participant / "TASK.md").read_text()
    sample = json.loads((participant / "input" / "sample.json").read_text())
    checks = {
        "public_snapshot_unchanged": hashes == record["public_hashes"],
        "no_solution_module": not any(path.name in forbidden for path in files),
        "no_git_history": not any(".git" in path.relative_to(participant).parts for path in files),
        "mission_does_not_name_paper": not any(term in task.lower() for term in ["fasteec", "arxiv", "2406.08577", "paper"]),
        "sample_unlabeled": "histograms" not in sample and "expected" not in sample,
        "sample_is_small": sample["nevents"] == 3,
        "no_symlinks": not any(path.is_symlink() for path in files),
    }
    records.append({"kind": kind, "checks": checks, "mission_words": len(task.split()), "public_files": len(files), "model": record["model"], "effort": record["effort"], "time_limit_seconds": record["time_limit_seconds"]})
result = {"passed": all(all(record["checks"].values()) for record in records), "pilots": records, "model_attempts": 4}
(root / "author" / "package_audit.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
if not result["passed"]:
    raise RuntimeError("Participant package integrity audit failed")
