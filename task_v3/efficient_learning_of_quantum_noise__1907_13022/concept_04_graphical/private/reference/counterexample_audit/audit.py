import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np


AUDIT_ROOT = Path(__file__).resolve().parent
REFERENCE = AUDIT_ROOT.parent
ROOT = AUDIT_ROOT.parents[2]
SUBMISSION = ROOT.parent / "private/runs/pilot/submissions/concept_04_graphical.py"
sys.path.insert(0, str(REFERENCE))

from author_tools import case, exhaustive, frontier_plan, oracle
from solver import learn
from weak_solver import solve as weak_solve


specification = importlib.util.spec_from_file_location("unchanged_evaluator", ROOT / "private/evaluator.py")
evaluator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(evaluator)

REGIONAL_CASES = (
    ("regional_01", "mediated_chain", 100, 1, 482716903),
    ("regional_02", "mediated_chain", 120, 2, 803194627),
    ("regional_03", "loop_ladder", 112, 1, 297450183),
    ("regional_04", "loop_ladder", 120, 2, 641829507),
    ("regional_05", "branch_triples", 108, 1, 950362741),
    ("regional_06", "branch_triples", 120, 2, 174836259),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_files():
    paths = []
    for directory in (ROOT / "participant", ROOT / "private"):
        paths.extend(path for path in directory.rglob("*") if path.is_file() and AUDIT_ROOT not in path.parents)
    paths.extend((SUBMISSION, ROOT.parent / "private/evaluation_sandbox.py"))
    return {str(path.resolve()): digest(path) for path in sorted(set(paths))}


def numerical_verification():
    records = []
    for family, count, region, seed in (
        ("mediated_chain", 10, 1, 6819023),
        ("loop_ladder", 10, 2, 9057319),
        ("branch_triples", 12, 1, 4728631),
    ):
        data, coefficients, order = case(family, count, seed, region, True)
        expected, probabilities = exhaustive(data, coefficients)
        reference = oracle(data, coefficients, order)
        error = float(np.max(np.abs(expected - reference)))
        assert np.all(np.isfinite(expected)) and error < 2e-10
        records.append({"family": family, "n": count, "region": region, "seed": seed,
                        "enumerated_states": len(probabilities), "oracle_max_log_error": error})
    return records


def summarize(records, name):
    families = {}
    for family in sorted({record["family"] for record in records}):
        selected = [record for record in records if record["family"] == family]
        families[family] = {
            "score": float(np.mean([record[name]["score"] for record in selected])),
            "cases": len(selected),
            "max_log_error": max(record[name]["max_log_error"] for record in selected),
        }
    return {"mean_fresh": float(np.mean([family["score"] for family in families.values()])),
            "worst_family": min(family["score"] for family in families.values()),
            "families": families,
            "runtime": sum(record[name]["runtime"] for record in records),
            "max_case_runtime": max(record[name]["runtime"] for record in records),
            "max_log_error": max(record[name]["max_log_error"] for record in records)}


def main():
    started = time.monotonic()
    before = protected_files()
    tiny = numerical_verification()
    previous_inputs = {entry["input_sha256"] for entry in json.loads((REFERENCE / "manifest.json").read_text())["cases"]}
    records = []
    old_temporary_root = tempfile.tempdir
    try:
        with tempfile.TemporaryDirectory(prefix="staged-audit-", dir=AUDIT_ROOT) as temporary:
            staged_root = Path(temporary)
            tempfile.tempdir = str(staged_root)
            for identifier, family, count, region, seed in REGIONAL_CASES:
                data, coefficients, order = case(family, count, seed, region, True)
                input_path = staged_root / f"{identifier}.npz"
                np.savez_compressed(input_path, **data)
                input_hash = digest(input_path)
                assert input_hash not in previous_inputs
                target = oracle(data, coefficients, order)
                baseline = weak_solve(data)
                recovered = learn(data)
                coefficient_error = max(abs(recovered.get(scope, 0.0) - coefficients.get(scope, 0.0)) for scope in set(recovered) | set(coefficients))
                assert coefficient_error < 1e-8
                assert np.all(np.isfinite(target)) and np.all(target < 0)
                record = {
                    "id": identifier, "family": family, "n": count, "region": region, "seed": seed,
                    "challenge_queries": True, "queries": len(target), "input_sha256": input_hash,
                    "max_frontier_bits": max((boundary - 1).bit_length() for node, boundary, transitions in frontier_plan(coefficients, order)),
                    "reference_coefficient_max_error": coefficient_error,
                    "min_log_event": float(np.min(target)), "max_log_event": float(np.max(target)),
                    "weak_score": evaluator.score(baseline, target, baseline, data["event_group"])[0],
                }
                for name, submission in (("reference", REFERENCE / "solver.py"), ("frozen", SUBMISSION)):
                    prediction, status, runtime = evaluator.execute(submission, input_path, len(target))
                    if status == "ok":
                        value, groups = evaluator.score(prediction, target, baseline, data["event_group"])
                        error = float(np.max(np.abs(prediction - target)))
                    else:
                        value, groups, error = 0.0, {}, None
                    record[name] = {"status": status, "score": value, "groups": groups, "runtime": runtime, "max_log_error": error}
                    if name == "reference":
                        assert status == "ok" and value > 0.9 and error < 2e-8, record
                records.append(record)
                print(json.dumps(record), flush=True)
    finally:
        tempfile.tempdir = old_temporary_root
    after = protected_files()
    assert before == after, "A protected file changed during the audit"
    failures = [record["id"] for record in records if record["frozen"]["status"] != "ok" or record["frozen"]["score"] <= 0.9]
    report = {
        "verdict": "reject_pilot_as_robustly_solved" if not failures else "investigate_genuine_failures",
        "selection": "Six predeclared seeds; unchanged three families; region 1/2; n=100..120; no adaptive selection",
        "submission": str(SUBMISSION), "submission_sha256": digest(SUBMISSION),
        "source_sha256": {str(path.relative_to(ROOT)): digest(path) for path in (REFERENCE / "author_tools.py", REFERENCE / "solver.py", ROOT / "private/evaluator.py")},
        "protected_file_sha256": before, "protected_files_unchanged": True,
        "independent_exhaustive_checks": tiny, "cases": records, "failure_cases": failures,
        "reference": summarize(records, "reference"), "frozen": summarize(records, "frozen"),
        "limits": {"wall_seconds_per_case": 120, "address_space_gib": 3},
        "runtime": time.monotonic() - started,
    }
    (AUDIT_ROOT / "results.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("verdict", "reference", "frozen", "protected_files_unchanged", "runtime")}))


if __name__ == "__main__":
    main()
