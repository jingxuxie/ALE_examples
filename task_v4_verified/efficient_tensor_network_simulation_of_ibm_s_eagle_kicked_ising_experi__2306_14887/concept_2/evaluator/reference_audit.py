"""Check all new scores against pre-ratchet physics and the public baseline."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "attempts" / "ratchet_generation_1"


def main():
    records = [json.loads(line) for line in (ROOT / "adversary" / "generation_1" / "sweep.jsonl").read_text().splitlines()]
    checks = []
    def check(name, passed, detail=None):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
    for reference_name, score_name in (("fresh", "champion"), ("builder", "builder")):
        expected = {}
        for record in records:
            if record["champion"] != reference_name:
                continue
            if record["suite"] == "baseline":
                expected.update(record["families"])
            elif record["suite"] == "corners" and record["epsilon"] == 0.002:
                expected.update({record["name"] + "/" + family: item for family, item in record["families"].items()})
        actual = json.loads((OUTPUT / (score_name + "_score.json")).read_text())
        check(score_name + "_complete_325", actual["evaluation_complete"] and actual["family_count"] == 325 and len(expected) == 325)
        check(score_name + "_every_label_matches_pre_ratchet_suite", actual["families"].keys() == expected.keys())
        maximum = 0.0
        flags = True
        for family, reference in expected.items():
            current = actual["families"][family]
            maximum = max(maximum, *(abs(current[key] - reference[key]) for key in ("exact", "error", "spread")),
                          *(abs(left - right) for left, right in zip(current["estimates"], reference["estimates"])))
            flags = flags and current["passed"] == reference["passed"]
        check(score_name + "_all_independent_pre_ratchet_values_match", maximum < 2e-8, maximum)
        check(score_name + "_all_acceptance_flags_match", flags)
        check(score_name + "_core_score_is_undrifted_nominal", abs(actual["core_score"] - expected["nominal"]["score"]) < 2e-6)
        check(score_name + "_worst_score_covers_all_325", abs(actual["worst_family_score"] - min(item["score"] for item in expected.values())) < 2e-6)
        check(score_name + "_resource_depth_score_preserved", abs(actual["resource_score"] - 1200 / actual["depth"]) < 1e-12)
        check(score_name + "_remains_valid_but_fails_new_contract", actual["valid"] and not actual["passed"])
    baseline = json.loads((OUTPUT / "baseline_score.json").read_text())
    public = json.loads((OUTPUT / "baseline" / "search_report.json").read_text())
    difference = max(abs(baseline["families"][family][key] - record[key]) for family, record in public["families"].items() for key in ("exact", "error", "spread"))
    check("baseline_public_and_independent_checker_match_all_325", len(public["families"]) == 325 and difference < 2e-8, difference)
    check("weak_baseline_candidate_not_replaced_with_private_solution", json.loads((OUTPUT / "baseline" / "witness.json").read_text()) == json.loads((ROOT / "generations" / "generation_0" / "attempts" / "participant_baseline" / "witness.json").read_text()))
    check("baseline_valid_but_not_passing", baseline["valid"] and not baseline["passed"])
    report = {"passed": all(item["passed"] for item in checks), "checks": checks}
    (OUTPUT / "reference_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "checks": len(checks)}))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
