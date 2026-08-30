import importlib.util
import json
from pathlib import Path

import numpy as np


def main():
    concept = Path(__file__).resolve().parents[1]
    specification = importlib.util.spec_from_file_location(
        "trusted_channel", concept / "participant/workspace/channel.py"
    )
    channel = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(channel)
    checks = []
    for report_name in (
        "isolated_baseline.json",
        "fresh_v_1.json",
        "safe_portfolio_evaluation.json",
    ):
        report = json.loads((concept / "adversary" / report_name).read_text())
        family_scores = {}
        for result in report["instances"]:
            instance = json.loads(
                (concept / "evaluator/hidden/instances" / (result["name"] + ".json")).read_text()
            )
            independent_risks = channel.risk(instance, result["answer"])
            maximum_error = float(
                np.max(np.abs(np.asarray(independent_risks) - result["regime_risks"]))
            )
            improvement = 1 - max(independent_risks) / result["baseline_worst_risk"]
            assert maximum_error < 1e-12
            assert abs(improvement - result["relative_improvement"]) < 1e-12
            execution = result["execution"]
            assert execution.get("infrastructure_error") is None
            assert execution["returncode"] == 0 and not execution["timed_out"]
            assert execution.get("execution_seconds", execution["elapsed_seconds"]) <= 45
            assert result["valid"] and result["resources_ok"]
            family_scores.setdefault(result["family"], []).append(improvement)
            checks.append({
                "report": report_name,
                "instance": result["name"],
                "maximum_probability_difference": maximum_error,
                "relative_risk_reduction": improvement,
            })
        mean_score = float(np.mean([value for values in family_scores.values() for value in values]))
        worst_score = min(float(np.mean(values)) for values in family_scores.values())
        assert abs(mean_score - report["core_score"]) < 1e-12
        assert abs(worst_score - report["worst_family_score"]) < 1e-12
        assert report["passed"] == (mean_score >= 0.20 and worst_score >= 0.10)
    audit = {"passed": True, "method": "independent forward categorical dynamic programming", "checks": checks}
    destination = concept / "adversary/scored_answers_audit.json"
    destination.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({"passed": True, "answers_checked": len(checks), "report": str(destination)}))


if __name__ == "__main__":
    main()
