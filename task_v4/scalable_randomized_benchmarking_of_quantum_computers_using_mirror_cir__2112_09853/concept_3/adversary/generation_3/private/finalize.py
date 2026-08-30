import argparse
import datetime
import hashlib
import json
import platform
import time
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--wait", type=int, default=0)
args = parser.parse_args()
deadline = time.monotonic() + args.wait
while not (WORK / "summary.json").exists():
    if time.monotonic() >= deadline:
        raise RuntimeError("private controller has not completed; no outcome can be claimed")
    time.sleep(5)
summary = json.loads((WORK / "summary.json").read_text())
official = json.loads((WORK / "official_report.json").read_text())
selection = json.loads((WORK / "candidate_selection.json").read_text())
artifact_hash = hashlib.sha256((WORK / "artifact.json").read_bytes()).hexdigest()
assert artifact_hash == official["artifact_sha256"]
seeds = set()
configuration_paths = [WORK / "config.json", WORK / "phase2_config.json"]
configuration_paths.extend(WORK.glob("*_adaptation.json"))
for path in configuration_paths:
    configuration = json.loads(path.read_text())
    if "seed" in configuration:
        seeds.add(configuration["seed"])
    for job in configuration.get("jobs", []):
        seeds.add(job["seed"])
frozen_hashes = json.loads((WORK / "frozen_hashes_at_start.json").read_text())
unchanged = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected for path, expected in frozen_hashes.items()}
families = {}
for name, result in official["families"].items():
    faults = result["fault_robustness"]
    families[name] = {"core_score": result["core_score"], "ideal_score": result["ideal_score"], "passed": result["passed"],
                      "minimum_faulted_weight": faults["minimum"], "by_omission_count": {order: {key: entry[key] for key in ("scenarios", "failed_scenarios", "minimum")}
                                                                                           for order, entry in faults["by_omission_count"].items()},
                      "selected_raw_source": selection["selected"][name]["raw"], "resources": result["resources"]}
finished = datetime.datetime.now(datetime.timezone.utc)
started = datetime.datetime.fromisoformat("2026-08-28T16:54:22+00:00")
audit = {"generation": 3, "private_only": True, "finished_utc": finished.isoformat(),
         "wall_seconds_including_inspection_and_build": (finished - started).total_seconds(),
         "maximum_cpu_search_workers": 4, "official_valid": official["valid"], "official_passed": official["passed"],
         "core_score": official["core_score"], "worst_family": official["worst_family"],
         "solvability": "demonstrated" if official["passed"] else "unknown; bounded search found no complete passing witness",
         "artifact_sha256": artifact_hash, "spec_sha256": official["spec_sha256"],
         "official_runtime_seconds": official["runtime_seconds"], "official_peak_rss_bytes": official["peak_rss_bytes"],
         "families": families, "search_seed_sha256": {str(seed): hashlib.sha256(str(seed).encode()).hexdigest() for seed in sorted(seeds)},
         "all_frozen_files_unchanged": all(unchanged.values()), "frozen_hash_checks": unchanged,
         "configuration_files": [str(path.relative_to(WORK)) for path in configuration_paths],
         "private_code_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for pattern in ("*.py", "*.cpp") for path in sorted(WORK.glob(pattern))},
         "platform": platform.platform(), "python_version": platform.python_version(),
         "reproducibility_note": "Seeds, configurations, source/binary hashes, logs, and artifacts are retained. Wall-time annealing makes optimization trajectories timing-dependent; the static certificate and exhaustive score are exactly reproducible.",
         "verification_command": "python -B evaluator/evaluate.py --submission adversary/generation_3/private/artifact.json --output adversary/generation_3/private/official_recheck.json",
         "fresh_attempts_not_accessed": ["v_3", "v_4"], "initialization": "archived G2 champion and allowed G2 solver source"}
if official["passed"]:
    (WORK / "passing_artifact.json").write_bytes((WORK / "artifact.json").read_bytes())
(WORK / "audit.json").write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")
print(json.dumps({key: audit[key] for key in ("official_valid", "official_passed", "core_score", "solvability", "wall_seconds_including_inspection_and_build",
                                            "official_runtime_seconds", "official_peak_rss_bytes", "all_frozen_files_unchanged")}, indent=2), flush=True)
