import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATUSES = {"solved", "hard_open_candidate", "hard_verified_achievable", "invalid", "rejected"}


def load(path):
    return json.loads(Path(path).read_text())


def score_text(record):
    text = f"{record['core_score']:.6f}"
    if record.get("worst_family_score") is not None:
        text += f" / family {record['worst_family_score']:.6f}"
    if record.get("worst_case_score") is not None:
        text += f" / case {record['worst_case_score']:.6f}"
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("configuration")
    arguments = parser.parse_args()
    configuration = load(arguments.configuration)
    report = {"paper": "XMDS2: Fast, scalable simulation of coupled stochastic partial differential equations", "arxiv": "1204.4255", "finalized_at": datetime.now(timezone.utc).isoformat(), "selected_concept": configuration["selected_concept"], "maximum_built_concepts": 3, "fresh_agent_model": "ultima-alpha", "fresh_agent_limit_seconds": 3600, "concepts": []}
    for specification in configuration["concepts"]:
        concept = ROOT / specification["directory"]
        status = specification["status"]
        if status not in ALLOWED_STATUSES:
            raise ValueError("invalid final status")
        attempts = []
        for record_path in sorted((concept / "attempts").glob("v_*.run.json")):
            record = load(record_path)
            if record["status"] == "running":
                raise ValueError(f"unfinished trial: {record_path}")
            name = record_path.name.removesuffix(".run.json")
            evaluation_path = concept / "attempts" / (name + ".evaluation.json")
            if not evaluation_path.exists():
                raise ValueError(f"missing evaluation: {evaluation_path}")
            evaluation = load(evaluation_path)
            attempts.append({"name": name, "generation": record["generation"], "model": record["model"], "effort": record["effort"], "elapsed_seconds": record["elapsed_seconds"], "termination": record["status"], "core_score": evaluation.get("core_score"), "worst_family_score": evaluation.get("worst_family_score"), "worst_case_score": evaluation.get("worst_case_score"), "valid": evaluation["valid"], "passed": evaluation["passed"], "reason": evaluation["reason"], "participant_unchanged_during_trial": record["participant_unchanged"], "evaluator_unchanged_during_trial": record["evaluator_unchanged"], "evaluation": str(evaluation_path.relative_to(ROOT))})
        if len(attempts) < 2:
            raise ValueError("at least two isolated trials are required by this discovery audit")
        current_generation = specification["current_generation"]
        current = [attempt for attempt in attempts if attempt["generation"] == current_generation]
        if len(current) < 2:
            raise ValueError("final generation needs two isolated trials")
        if status.startswith("hard_") and any(attempt["passed"] for attempt in current):
            raise ValueError("cannot mark a passing final generation hard")
        if status == "solved" and not any(attempt["passed"] for attempt in current):
            raise ValueError("solved status requires a passing final-generation trial")
        if status == "hard_verified_achievable":
            if specification.get("achievability_generation") != current_generation:
                raise ValueError("achievability proof must belong to the final generation")
            proof = load(ROOT / specification["achievability_evaluation"])
            if not proof["passed"] or not proof["valid"]:
                raise ValueError("achievability proof does not pass")
        baseline_records = []
        for baseline in specification["baselines"]:
            evaluation = load(ROOT / baseline["evaluation"])
            baseline_records.append({**baseline, "core_score": evaluation["core_score"], "worst_family_score": evaluation.get("worst_family_score"), "worst_case_score": evaluation.get("worst_case_score"), "valid": evaluation["valid"], "passed": evaluation["passed"]})
        result = {**specification, "fresh_attempts": attempts, "baseline_champion_scores": baseline_records, "ratchet_generations": current_generation - 1, "solvability": "demonstrated" if status in {"solved", "hard_verified_achievable"} else "unknown", "finalized_at": report["finalized_at"]}
        result.update({"hardness_finalized": True, "known_passing_solution": result["solvability"] == "demonstrated"})
        (concept / "status.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        for generation in sorted({attempt["generation"] for attempt in attempts}):
            directory = concept / "generations" / f"generation_{generation}"
            if not directory.exists():
                continue
            generation_attempts = [attempt for attempt in attempts if attempt["generation"] == generation]
            generation_status = "solved" if any(attempt["passed"] for attempt in generation_attempts) else status
            path = directory / "outcome.json"
            existing = {}
            existing.update({"generation": generation, "status": generation_status, "fresh_agents_run": len(generation_attempts), "hardness_finalized": True, "solvability": "demonstrated" if generation_status in {"solved", "hard_verified_achievable"} else "unknown", "known_passing_solution": generation_status in {"solved", "hard_verified_achievable"}, "fresh_attempts": generation_attempts})
            path.write_text(json.dumps(existing, indent=2, allow_nan=False) + "\n")
        for folder in ("attempts", "champions", "adversary"):
            path = concept / folder / "status.json"
            if path.exists():
                existing = {"status": "completed", "role": folder, "hardness_finalized": True, "concept_status": status, "current_generation": current_generation, "fresh_agents_run": len(attempts), "solvability": result["solvability"], "evidence": "../status.json"}
                path.write_text(json.dumps(existing, indent=2, allow_nan=False) + "\n")
        report["concepts"].append(result)
    if len(report["concepts"]) != 3 or len({item["verification_mode"] for item in report["concepts"]}) < 3:
        raise ValueError("discovery requires three concepts and three verification modes")
    selected = next(item for item in report["concepts"] if item["directory"] == report["selected_concept"])
    report["status"] = selected["status"]
    report["solvability"] = selected["solvability"]
    report["accepted"] = report["status"] in {"hard_open_candidate", "hard_verified_achievable"}
    report["audit_notes"] = configuration.get("audit_notes", [])
    report["source_archives"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "authoring" / "sources").glob("*") if path.is_file()}
    (ROOT / "status.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    (ROOT / "FINAL_REPORT.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    lines = ["# Hardness-discovery report", "", "| Concept | Mode | Baseline / champion core scores | Fresh scores by generation | Ratchets | Final status |", "|---|---|---|---|---:|---|"]
    for item in report["concepts"]:
        baseline_text = "; ".join(f"{baseline['label']}: {score_text(baseline)}" for baseline in item["baseline_champion_scores"])
        fresh_text = "; ".join(f"g{attempt['generation']}/{attempt['name']}: {score_text(attempt)}" for attempt in item["fresh_attempts"])
        lines.append(f"| {item['title']} | {item['verification_mode']} | {baseline_text} | {fresh_text} | {item['ratchet_generations']} | {item['status']} |")
    lines.extend(["", f"Selected: **{report['selected_concept']} — {report['status']}**. Solvability: **{report['solvability']}**.", "", "## Counterexample Searches"])
    for item in report["concepts"]:
        lines.append(f"- {item['directory']}: {item['counterexample_search_results']}")
    lines.extend(["", "## Substantive Failures"])
    for item in report["concepts"]:
        lines.append(f"- {item['directory']}: {item['capability_failure']}")
    (ROOT / "FINAL_REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": report["status"], "selected_concept": report["selected_concept"], "accepted": report["accepted"], "solvability": report["solvability"], "trials": sum(len(item["fresh_attempts"]) for item in report["concepts"])}, indent=2))


if __name__ == "__main__":
    main()
