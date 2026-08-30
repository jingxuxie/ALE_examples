import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load(path):
    return json.loads(path.read_text())


def hashes(directory):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def main():
    checks = []

    def require(condition, description):
        if not condition:
            raise RuntimeError(description)
        checks.append(description)

    summary = load(ROOT / "status.json")
    for number in (1, 2, 3):
        concept = ROOT / f"concept_{number}"
        status = load(concept / "status.json")
        for name in ("participant/input", "participant/workspace", "participant/baseline",
                     "evaluator/hidden", "attempts", "champions", "adversary"):
            require((concept / name).is_dir(), f"concept {number}: required directory {name}")
        require((concept / "participant/TASK.md").is_file(), f"concept {number}: participant task exists")
        require(not any(path.is_symlink() for path in (concept / "participant").rglob("*")),
                f"concept {number}: participant contains no symlinks")
        ast.parse((concept / "evaluator/evaluate.py").read_text())
        checks.append(f"concept {number}: evaluator parses")
        for attempt in range(1, status["current_attempt"] + 1):
            run = load(concept / "attempts" / f"v_{attempt}_run.json")
            result = load(concept / "attempts" / f"v_{attempt}_score.json")
            prefix = f"concept {number} attempt {attempt}"
            require(run["status"] == "finished" and run["model"] == "ultima-alpha",
                    f"{prefix}: correct model and completed run")
            require(run["wall_limit_seconds"] == 3600 and run["elapsed_seconds"] <= 3616,
                    f"{prefix}: one-hour runner limit enforced")
            require(run["output_initially_empty"] and run["fresh_context"] and run["participant_read_only"],
                    f"{prefix}: fresh allowlisted launch")
            require(run["participant_unchanged"] and run["participant_hashes_before"] == run["participant_hashes_after"],
                    f"{prefix}: public assets unchanged during attempt")
            participant = concept / ("participant" if attempt == status["current_attempt"]
                                     else f"generations/generation_{attempt - 1}/participant")
            require(hashes(participant) == run["participant_hashes_before"],
                    f"{prefix}: retained public assets match launch manifest")
            require(hashes(concept / "attempts" / f"frozen_v_{attempt}") == run["output_files"],
                    f"{prefix}: scored snapshot matches completed submission")
            require(result["valid"], f"{prefix}: evaluator accepts artifact and execution")
        require(hashes(concept / "participant") == status["final_participant_manifest"],
                f"concept {number}: final participant manifest matches")
    counterexample = ROOT / "concept_2"
    status = load(counterexample / "status.json")
    proof = load(counterexample / status["passing_private_witness"]["independent_main_recheck"])
    require(proof["valid"] and proof["passed"] and proof["evaluation_complete"] and proof["family_count"] == 325,
            "counterexample: independently regraded private proof passes all 325 waveforms")
    require(proof["target_sha256"] == status["target_sha256"],
            "counterexample: proof uses the frozen challenger target")
    require(not status["reference_grades"]["champion"]["passed"] and not status["final_fresh_scores"]["passed"],
            "counterexample: both fresh submissions fail the retained target")
    control = ROOT / "concept_3"
    require(hashes(control / "champions/generation_2") == hashes(control / "attempts/frozen_v_2"),
            "control: privately stress-tested champion is the exact second fresh submission")
    require(summary["selected_concept"] == "concept_2" and summary["status"] == "hard_verified_achievable",
            "session: verified achievable counterexample selected")
    require([record["status"] for record in summary["concepts"]] ==
            ["hard_open_candidate", "hard_verified_achievable", "solved"],
            "session: all three decisions match empirical results")
    report = {"passed": True, "check_count": len(checks), "checks": checks,
              "numerical_validation_scope": "Previously recorded independent evaluator audits and actual scorer runs; this audit verifies package, isolation, snapshot and decision provenance."}
    (ROOT / "authoring/final_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "check_count": len(checks)}, indent=2))


if __name__ == "__main__":
    main()
