import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def metrics(score, mode):
    if not score:
        return "not recorded"
    if not score.get("valid", False):
        return "invalid: " + score.get("reason", "unspecified")
    if mode == 1:
        return "KL %.6g; worst-family %.6g; min ESS %.6g" % (
            score.get("mean_kl", 0), score.get("worst_family_kl", 0), score.get("minimum_ess", 0))
    values = score.get("metrics", {})
    if mode == 2:
        return "gate-score %.6g; variance %.6g; gradient %.6g" % (
            score.get("core_score", 0), values.get("reward_variance", 0), values.get("gradient_infinity", 0))
    return "KL %.6g; worst-family %.6g; max TV %.6g" % (
        values.get("mean_forward_kl", 0), values.get("worst_family_mean_kl", 0), values.get("max_tv", 0))


def main():
    overall = load(ROOT / "status.json")
    if overall["phase"] != "complete":
        raise ValueError("finish the tournament and ratchets before producing the final report")
    concepts = [load(ROOT / ("concept_" + str(number)) / "status.json") for number in (1, 2, 3)]
    lines = ["# Hardness discovery", "", "## Concepts and verification modes", "",
             "| Concept | Verification mode | Final generation | Status |",
             "|---|---|---|---|"]
    for state in concepts:
        lines.append("| " + " | ".join((state["concept"], state["verification_mode"], state["current_generation"], state["status"])) + " |")
    lines.extend(["", "## Baseline, champion, and fresh-agent scores", "",
                  "All scientific attempts use isolated ultima-alpha sessions with a 3,600-second limit.", "",
                  str(sum(len(state["history"]) for state in concepts)) + " scientific attempts are scored. One pre-session infrastructure failure is excluded from hardness evidence.", "",
                  "| Concept / generation | Baseline or incoming champion | Fresh attempt | Fresh score | Decision |",
                  "|---|---|---|---|---|"])
    for number, state in enumerate(concepts, 1):
        for item in state["history"]:
            generation = ROOT / item["generation_root"]
            candidates = [generation / "adversary/baseline_report.json", generation / "adversary/baseline_score.json"]
            baseline = next((load(path) for path in candidates if path.exists()), None)
            lines.append("| " + " | ".join((item["generation_root"], metrics(baseline, number), item["attempt"],
                                             metrics(item["fresh_score"], number), item["decision"])) + " |")
        if state.get("known_solution_score"):
            lines.append("| " + state["current_generation"] + " private control | " + metrics(state["known_solution_score"], number) + " | — | — | passing control |")
    lines.extend(["", "## Counterexample search results", ""])
    for number, state in enumerate(concepts, 1):
        lines.append("- Concept " + str(number) + ": " + state["counterexample_search"])
    lines.extend(["", "## Ratchet generations", ""])
    for number, state in enumerate(concepts, 1):
        label = " ratchet" if state["ratchet_generations"] == 1 else " ratchets"
        lines.append("- Concept " + str(number) + ": " + str(state["ratchet_generations"]) + label + " after the initial tournament.")
    lines.extend(["", "## Final status", "", "- Status: `" + overall["status"] + "`.",
                  "- Selected task: `" + str(overall["selected_task_root"]) + "`.",
                  "- Solvability: " + overall["solvability"] + ".", "",
                  "## Substantive capability", ""])
    for number, state in enumerate(concepts, 1):
        lines.append("- Concept " + str(number) + ": " + state["substantive_capability"])
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n")
    report = {"concepts_and_modes": concepts, "final_status": overall["status"],
              "selected_task": overall["selected_task_root"], "solvability": overall["solvability"],
              "fresh_attempts": {"scored": sum(len(state["history"]) for state in concepts),
                                 "excluded": overall["infrastructure_exclusions"]},
              "ratchet_generations": {"concept_" + str(number): state["ratchet_generations"] for number, state in enumerate(concepts, 1)}}
    (ROOT / "REPORT.json").write_text(json.dumps(report, indent=2))
    if overall["selected_task_root"]:
        selected = Path(overall["selected_task_root"])
        entry = {"status": overall["status"], "solvability": overall["solvability"],
                 "task_root": str(selected), "participant": str(selected / "participant"),
                 "evaluator": str(selected / "evaluator/evaluate.py"),
                 "baseline": str(selected / "participant/baseline"),
                 "evidence": str(selected / "attempts"), "report": "REPORT.md"}
        certificate = selected / "adversary/hardness_certificate.json"
        if (ROOT / certificate).is_file():
            entry["hardness_certificate"] = str(certificate)
        entry["selection_reason"] = overall.get("selection_reason")
        (ROOT / "SELECTED_TASK.json").write_text(json.dumps(entry, indent=2))
    print(json.dumps({"report": str(ROOT / "REPORT.md"), "status": overall["status"], "selected": overall["selected_task_root"]}))


if __name__ == "__main__":
    main()
