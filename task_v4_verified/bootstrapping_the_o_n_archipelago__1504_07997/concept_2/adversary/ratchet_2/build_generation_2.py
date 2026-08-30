import copy
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import uuid

import mpmath as mp
import numpy as np

from confirm import checker, independent_check


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FAMILIES = ("crowded_singlets", "spin_aliases", "mixed_cancellation", "weak_residues")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kernel_audit(instance, witness):
    with mp.workdps(80):
        maximum = mp.mpf(0)
        for row, probe in enumerate(instance["probes"]):
            position, angle = mp.mpf(str(probe["t"])), mp.mpf(str(probe["eta"]))
            for column, candidate in enumerate(instance["candidates"]):
                dimension = mp.mpf(str(candidate["dimension"]))
                value = (mp.exp(-position * dimension) * mp.legendre(candidate["spin"], angle)
                         * (dimension / 8) ** probe["order"] / mp.mpf(str(candidate["column_scale"])))
                error = abs(value - mp.mpf(str(instance["design"][row][column]))) / max(1, abs(value))
                maximum = max(maximum, error)
        assert maximum < mp.mpf("1e-12")
        amplitudes = [mp.fsum(mp.mpf(str(value)) ** 2 for value in atom["ope"]) for atom in witness["atoms"]]
    matrix = np.asarray(instance["design"], dtype=float)
    normalized = matrix / np.linalg.norm(matrix, axis=0)
    correlation = np.abs(normalized.T @ normalized)
    np.fill_diagonal(correlation, 0)
    return {"max_normalized_radial_kernel_error_80_digit": str(maximum),
            "maximum_distinct_column_correlation": float(np.max(correlation)),
            "planted_min_max_residue_ratio": str(min(amplitudes) / max(amplitudes))}


def main():
    candidates = {case["id"]: case for case in json.loads((ROOT / "adversary/sweep_1/candidates.json").read_text())["instances"]}
    witnesses = {case["id"]: case for case in json.loads((ROOT / "adversary/sweep_1/witnesses.json").read_text())["cases"]}
    records = [json.loads(path.read_text()) for path in (HERE / "confirmations").glob("*/record.json")]
    source_hashes = {path.name: digest(path) for path in (HERE / "replay").glob("*.py")}
    selected = []
    for family in FAMILIES:
        resistant = [record for record in records if record["family"] == family and not record["valid"]
                     and not record["independent"]["valid"] and record["planted"]["valid"]
                     and record["reason"] == "moment residual" and record["exit_code"] == 0
                     and not record["timed_out"] and record["budget_seconds"] == 300
                     and record["residual"] > 4e-8 and record["source_sha256"] == source_hashes]
        resistant.sort(key=lambda record: record["residual"], reverse=True)
        if len(resistant) < 2:
            raise RuntimeError("need two completed numerical failures for " + family)
        selected.extend(resistant[:2])
    instances = [copy.deepcopy(candidates[record["id"]]) for record in selected]
    planted = {"cases": [copy.deepcopy(witnesses[instance["id"]]) for instance in instances]}
    answers = {"cases": [json.loads((HERE / "confirmations" / instance["id"] / "answer.json").read_text())["cases"][0]
                         for instance in instances]}
    mapping_path = HERE / "id_map.json"
    mapping = json.loads(mapping_path.read_text()) if mapping_path.exists() else {}
    for instance in instances:
        mapping.setdefault(instance["id"], "case_" + uuid.uuid4().hex[:20])
    assert len(set(mapping.values())) == len(mapping)
    write(mapping_path, mapping)
    for instance, witness, answer in zip(instances, planted["cases"], answers["cases"]):
        identifier = mapping[instance["id"]]
        instance["id"] = witness["id"] = answer["id"] = identifier
    planted_score = checker.score(instances, planted)
    baseline_score = checker.score(instances, answers)
    assert planted_score["passed"] and not baseline_score["passed"]
    audits = []
    for instance, witness in zip(instances, planted["cases"]):
        check = independent_check(instance, witness)
        assert check["valid"]
        audits.append(dict(kernel_audit(instance, witness), id=instance["id"], family=instance["family"], certificate=check))
    negatives = {}
    for name in ("empty", "omitted_case", "duplicate_atom", "nan_ope", "shared_violation", "over_atom_budget"):
        altered = copy.deepcopy(planted)
        if name == "empty":
            altered["cases"] = []
        elif name == "omitted_case":
            altered["cases"].pop()
        elif name == "duplicate_atom":
            altered["cases"][0]["atoms"][1] = copy.deepcopy(altered["cases"][0]["atoms"][0])
        elif name == "nan_ope":
            altered["cases"][0]["atoms"][0]["ope"][0] = float("nan")
        elif name == "shared_violation":
            altered["cases"][0]["atoms"][0]["ope"][0] += 0.01
        else:
            altered["cases"][0]["atoms"] *= 2
        negatives[name] = checker.score(instances, altered)
        assert not negatives[name]["passed"]
    original_instances = json.loads((ROOT / "adversary/generation_1/participant/input/instances.json").read_text())["instances"]
    original_answer = json.loads((ROOT / "champions/generation_1/answer.json").read_text())
    original_score = checker.score(original_instances, original_answer)
    assert original_score["passed"]
    assert digest(ROOT / "evaluator/hidden/checker.py") == digest(ROOT / "adversary/generation_1/evaluator/hidden/checker.py")
    assert digest(ROOT / "participant/workspace/check.py") == digest(ROOT / "evaluator/hidden/checker.py")
    payload = {"instances": instances}
    write(ROOT / "participant/input/instances.json", payload)
    write(ROOT / "evaluator/hidden/instances.json", payload)
    for path in (HERE / "replay").glob("*.py"):
        shutil.copyfile(path, ROOT / "participant/baseline" / path.name)
    write(HERE / "selected_planted.json", planted)
    write(HERE / "baseline_answer.json", answers)
    write(HERE / "baseline_evaluation.json", baseline_score)
    write(HERE / "planted_evaluation.json", planted_score)
    write(HERE / "independent_validation.json", {"precision_digits": 80, "cases": audits, "negative_controls": negatives})
    adaptation = []
    mapping = {"champion_core.py": "solve.py", "search.py": "search.py", "refine.py": "refine.py", "enumerate_supports.py": "enumerate_supports.py"}
    for target, source in mapping.items():
        adaptation.extend(difflib.unified_diff((ROOT / "champions/generation_1" / source).read_text().splitlines(True),
                                              (HERE / "replay" / target).read_text().splitlines(True),
                                              fromfile="champions/generation_1/" + source, tofile="participant/baseline/" + target))
    (HERE / "adaptation.patch").write_text("".join(adaptation))
    report = {"generation": 2, "source_generation": 1, "confirmation_budget_seconds_per_case": 300,
              "selection": selected, "public_ids": [instance["id"] for instance in instances],
              "private_id_mapping": "id_map.json", "all_completed_confirmation_records": records,
              "source_champion_gen1_score": original_score,
              "baseline": baseline_score, "planted": planted_score,
              "selected_total_baseline_seconds": sum(record["elapsed_seconds"] for record in selected),
              "source_champion_hashes": {path.name: digest(path) for path in (ROOT / "champions/generation_1").glob("*.py")},
              "generalized_baseline_hashes": source_hashes,
              "public_private_input_hash_equal": digest(ROOT / "participant/input/instances.json") == digest(ROOT / "evaluator/hidden/instances.json"),
              "checker_unchanged": True,
              "claims": "empirical resistance to this generalized 300-second replay, not intrinsic hardness or an input-only achievability proof",
              "fresh_agents_launched_by_sidecar": 0}
    write(HERE / "ratchet_report.json", report)
    print(json.dumps({"generation": 2, "ids": [instance["id"] for instance in instances],
                      "baseline_core": baseline_score["core_score"], "baseline_worst": baseline_score["worst_family_score"],
                      "planted_core": planted_score["core_score"], "baseline_seconds": report["selected_total_baseline_seconds"]}))


if __name__ == "__main__":
    main()
