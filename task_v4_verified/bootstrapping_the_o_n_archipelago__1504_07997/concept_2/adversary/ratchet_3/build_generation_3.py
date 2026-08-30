import copy
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import uuid

import search


ROOT = search.ROOT
HERE = search.HERE
FAMILIES = ("spin_aliases", "mixed_cancellation", "weak_residues", "joint_alias_cancellation")


def main():
    cases, witnesses = {}, {}
    for prefix in ("", "joint_"):
        cases.update({instance["id"]: instance for instance in json.loads((HERE / (prefix + "candidates.json")).read_text())["instances"]})
        witnesses.update({case["id"]: case for case in json.loads((HERE / (prefix + "witnesses.json")).read_text())["cases"]})
    records = [json.loads(path.read_text()) for path in (HERE / "confirmation").glob("*/record.json")]
    replay_hashes = {path.name: search.digest(path) for path in (HERE / "replay").glob("*.py")}
    selected = []
    for family in FAMILIES:
        eligible = [record for record in records if record["family"] == family and not record["valid"]
                    and record["reason"] == "moment residual" and record["exit_code"] == 0
                    and not record["timed_out"] and record["continuous_attempted"] and not record["stage_errors"]
                    and record["budget_seconds"] == 300 and record["residual"] > 4e-8
                    and record["source_hashes"] == replay_hashes]
        eligible.sort(key=lambda record: record["residual"], reverse=True)
        if len(eligible) < 2:
            raise RuntimeError("need two confirmed numerical failures for " + family)
        selected.extend(eligible[:2])
    instances = [copy.deepcopy(cases[record["id"]]) for record in selected]
    planted = {"cases": [copy.deepcopy(witnesses[record["id"]]) for record in selected]}
    answer = {"cases": [json.loads((HERE / "confirmation" / record["id"] / "answer.json").read_text())["cases"][0] for record in selected]}
    mapping_path = HERE / "id_map.json"
    mapping = json.loads(mapping_path.read_text()) if mapping_path.exists() else {}
    for instance in instances:
        mapping.setdefault(instance["id"], "case_" + uuid.uuid4().hex[:20])
    search.write(mapping_path, mapping)
    audits = []
    for instance, witness, result in zip(instances, planted["cases"], answer["cases"]):
        rows, count = len(instance["probes"]), instance["max_atoms"]
        assert 12 <= rows <= 26 and 10 <= count <= 18 and 3 * rows >= 2 * count - 1
        assert len(instance["candidates"]) == 96
        audit = search.validate(instance, witness)
        independent = search.previous.independent_check(instance, result)
        assert not independent["valid"]
        audit.update({"source_id": instance["id"], "baseline_independent": independent,
                      "rows": rows, "max_atoms": count, "coupled_equations": 3 * rows,
                      "fixed_support_parameters": 2 * count - 1})
        identifier = mapping[instance["id"]]
        instance["id"] = witness["id"] = result["id"] = identifier
        audit["public_id"] = identifier
        audits.append(audit)
    baseline_score = search.checker.score(instances, answer)
    planted_score = search.checker.score(instances, planted)
    assert baseline_score["core_score"] == 0 and planted_score["passed"]
    old_instances = json.loads((ROOT / "adversary/generation_2/participant/input/instances.json").read_text())["instances"]
    old_answer = json.loads((ROOT / "champions/generation_2/answer.json").read_text())
    original_score = search.checker.score(old_instances, old_answer)
    assert original_score["passed"]
    assert search.digest(ROOT / "evaluator/hidden/checker.py") == search.digest(ROOT / "adversary/generation_2/evaluator/hidden/checker.py")
    assert search.digest(ROOT / "participant/workspace/check.py") == search.digest(ROOT / "evaluator/hidden/checker.py")
    controls = {}
    for name in ("empty", "omission", "duplicate", "nan", "shared_violation"):
        altered = copy.deepcopy(planted)
        if name == "empty":
            altered["cases"] = []
        elif name == "omission":
            altered["cases"].pop()
        elif name == "duplicate":
            altered["cases"][0]["atoms"][1] = copy.deepcopy(altered["cases"][0]["atoms"][0])
        elif name == "nan":
            altered["cases"][0]["atoms"][0]["ope"][0] = float("nan")
        else:
            altered["cases"][0]["atoms"][0]["ope"][0] += 0.01
        controls[name] = search.checker.score(instances, altered)
        assert not controls[name]["passed"]
    search.write(ROOT / "participant/input/instances.json", {"instances": instances})
    search.write(ROOT / "evaluator/hidden/instances.json", {"instances": instances})
    for path in (HERE / "replay").glob("*.py"):
        shutil.copyfile(path, ROOT / "participant/baseline" / path.name)
    search.write(HERE / "selected_planted.json", planted)
    search.write(HERE / "baseline_answer.json", answer)
    search.write(HERE / "baseline_evaluation.json", baseline_score)
    search.write(HERE / "planted_evaluation.json", planted_score)
    search.write(HERE / "independent_validation.json", {"precision_digits": 80, "cases": audits, "negative_controls": controls})
    patch = []
    for name in ("improve.py", "seed.py", "continuous.py", "pipeline.py"):
        patch.extend(difflib.unified_diff((ROOT / "champions/generation_2" / name).read_text().splitlines(True),
                                         (HERE / "replay" / name).read_text().splitlines(True),
                                         fromfile="champions/generation_2/" + name, tofile="participant/baseline/" + name))
    (HERE / "adaptation.patch").write_text("".join(patch))
    screening = json.loads((HERE / "screening_results.json").read_text())["records"]
    joint = json.loads((HERE / "joint_screening_results.json").read_text())["records"]
    old_controls = [json.loads(path.read_text()) for path in (HERE / "generation_2_controls").glob("*/record.json")]
    report = {"generation": 3, "ratchet_generations": 2, "base_screened_cases": len(screening),
              "base_screened_valid_certificates": sum(record["valid"] for record in screening),
              "joint_screened_cases": len(joint), "joint_screened_valid_certificates": sum(record["valid"] for record in joint),
              "confirmation_records": records, "selected": selected, "public_ids": [instance["id"] for instance in instances],
              "baseline": baseline_score, "planted": planted_score, "original_champion_score": original_score,
              "cold_generation_2_controls": old_controls,
              "selected_baseline_seconds": sum(record["elapsed_seconds"] for record in selected),
              "replay_hashes": replay_hashes,
              "source_champion_hashes": {path.name: search.digest(path) for path in (ROOT / "champions/generation_2").glob("*.py")},
              "checker_unchanged": True, "public_private_data_identical": search.digest(ROOT / "participant/input/instances.json") == search.digest(ROOT / "evaluator/hidden/instances.json"),
              "claim": "measured 300-second replay resistance; not intrinsic hardness or fresh-generation success",
              "fresh_agents_launched": 0}
    search.write(HERE / "ratchet_report.json", report)
    print(json.dumps({"built_generation": 3, "baseline_core": baseline_score["core_score"], "baseline_worst": baseline_score["worst_family_score"],
                      "planted_valid": 8, "public_ids": report["public_ids"], "selected_seconds": report["selected_baseline_seconds"]}))


if __name__ == "__main__":
    main()
