import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    concept = ROOT / "concept_2"
    attempts = []
    for number in (1, 2):
        stem = concept / "attempts" / f"v_{number}"
        launch = json.loads(Path(str(stem) + ".launch.json").read_text())
        cutoff = json.loads(Path(str(stem) + ".cutoff.json").read_text())
        report = json.loads(Path(str(stem) + ".evaluation.json").read_text())
        artifact = Path(cutoff["artifact_directory"]) / "solution.json"
        attempts.append({"number": number, "launch": launch, "cutoff": cutoff, "report": report, "artifact": json.loads(artifact.read_text()), "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()})
    directory = concept / "adversary" / "fresh_portfolio"
    directory.mkdir(exist_ok=True)
    circuits = []
    selection = {}
    for instance in attempts[0]["report"]["instances"]:
        identifier = instance["id"]
        ranked = []
        for attempt in attempts:
            score = next(item for item in attempt["report"]["instances"] if item["id"] == identifier)
            ranked.append((score["certified"], score["resource_score"], -score["gates"], attempt["number"]))
        chosen = max(ranked)[-1]
        source = attempts[chosen - 1]
        circuits.append(next(item for item in source["artifact"]["circuits"] if item["id"] == identifier))
        selection[identifier] = f"v_{chosen}"
    (directory / "solution.json").write_text(json.dumps({"version": 1, "circuits": circuits}))
    command = [sys.executable, str(ROOT / "private/affinity.py"), str(concept / "evaluator/evaluate.py"), str(directory), "--report", str(directory / "report.json")]
    result = subprocess.run(command, capture_output=True, text=True, timeout=240)
    (directory / "evaluation.log").write_text(result.stdout + result.stderr)
    if not (directory / "report.json").exists():
        raise RuntimeError("portfolio evaluation did not produce a report")
    portfolio = json.loads((directory / "report.json").read_text())
    summary = {
        "status": "hard_verified_achievable",
        "fresh_attempt_count": 2,
        "model": "ultima-alpha",
        "limit_seconds": 3600,
        "fresh_complete_witnesses": 0,
        "private_complete_witnesses": 1,
        "all_submitted_circuits_accurate": all(instance["accurate"] for attempt in attempts for instance in attempt["report"]["instances"]),
        "common_uncertified_targets": sorted(set.intersection(*[{instance["id"] for instance in attempt["report"]["instances"] if not instance["certified"]} for attempt in attempts])),
        "privileged_cross_attempt_portfolio": {"not_a_fresh_submission": True, "selection": selection, "core_score": portfolio["core_score"], "passed": portfolio["passed"], "report": "adversary/fresh_portfolio/report.json"},
        "cutoff_artifact_sha256": {f"v_{attempt['number']}": attempt["sha256"] for attempt in attempts},
        "substantive_failure": "Accurate continuous rotations were found, but graph-constrained sparsity and simultaneous layer/gate limits remained unsatisfied. Even a privileged per-target union of both attempts fails irregular_16.",
        "ratchet_generations": 0,
    }
    (concept / "adversary/empirical_decision.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
