import collections
import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import time


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
POOL = ROOT.parent
CONCEPT = POOL.parents[1]
G2 = CONCEPT / "adversary/generation_2"
CHAMPION = CONCEPT / "attempts/v_2.frozen"
CONTRACT = {"core_target": 0.40, "worst_family_target": 0.30, "case_seconds": 12,
            "suite_seconds": 360, "memory_mb": 2048, "cpu_cores": 1, "submission_mb": 128}


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


EVALUATOR = load_module("phase_champion_g2_evaluator", G2 / "evaluator/evaluate.py")
GENERATOR = load_module("phase_champion_stress_validator", POOL / "generate.py")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def read_inputs():
    manifest = json.loads((POOL / "manifest.json").read_text())
    cases = json.loads((POOL / "cases.json").read_text())
    certificates = json.loads((POOL / "certificates.json").read_text())
    frozen = json.loads((POOL / "freeze.json").read_text())
    assert manifest["complete"] and len(cases) == 24
    assert collections.Counter(case["family"] for case in cases) == dict.fromkeys(GENERATOR.FAMILIES, 4)
    assert manifest["quality_targets_unchanged"] == {"core": 0.40, "worst_family": 0.30}
    assert manifest["resource_contract_unchanged"] == {"case_seconds": 12, "suite_seconds": 360}
    for relative, expected in frozen["sha256"].items():
        assert digest(POOL / relative) == expected
    for filename, expected in manifest["source_sha256"].items():
        assert digest(Path(filename)) == expected
    g2_frozen = json.loads((G2 / "freeze.json").read_text())
    for relative in ("evaluator/evaluate.py", "evaluator/routing.py"):
        assert digest(G2 / relative) == g2_frozen["sha256"][relative]
    GENERATOR.validate_records(list(certificates.values()))
    for case in cases:
        certificate = certificates[case["id"]]
        assert case == certificate["case"]
        assert manifest["baseline"][case["id"]] == certificate["design"]["baseline"]
    return manifest, cases, certificates


def run_case(case, manifest, certificates, label):
    record = {"id": case["id"], "family": case["family"], "valid": False, "label": label,
              "baseline_cost": manifest["baseline"][case["id"]]["cost"],
              "certificate_cost": certificates[case["id"]]["design"]["certificate"]["cost"]}
    execution = None
    try:
        execution = EVALUATOR.run_python(CHAMPION, "solve.py", case, CONTRACT["case_seconds"], memory_mb=CONTRACT["memory_mb"])
        record.update({key: execution[key] for key in ("seconds", "returncode", "timed_out")})
        write_json(ROOT / "executions" / f"{case['id']}__{label}.json", execution)
        if execution["returncode"] != 0 or execution["timed_out"]:
            record["execution_failure"] = True
            raise ValueError("execution failure: " + execution["stderr"][-2000:])
        answer = json.loads(execution["stdout"], parse_constant=EVALUATOR.reject_constants)
        record.update(EVALUATOR.validate(case, answer))
        record["ratio"] = record["cost"] / record["baseline_cost"]
        record["improvement"] = 1 - record["ratio"]
        record["certificate_ratio"] = record["cost"] / record["certificate_cost"]
        record["certificate_cost_excess_fraction"] = record["certificate_ratio"] - 1
        record["certificate_improvement_gap"] = (record["cost"] - record["certificate_cost"]) / record["baseline_cost"]
        route_path = ROOT / "routes" / f"{case['id']}__{label}.json"
        write_json(route_path, answer)
        record["route_artifact"] = str(route_path.relative_to(ROOT))
    except Exception as error:
        record["reason"] = str(error)
        if execution is None:
            record.update(seconds=CONTRACT["case_seconds"] + 1.0, execution_failure=True)
    print(json.dumps({key: record.get(key) for key in ("id", "label", "valid", "improvement", "certificate_ratio", "seconds", "reason")}), flush=True)
    return record


def summarize(records, wall_seconds):
    summary = EVALUATOR.summarize(records, CONTRACT, wall_seconds)
    comparison = {}
    for family in sorted({record["family"] for record in records}):
        selected = [record for record in records if record["family"] == family]
        certificate_score = 1 - math.exp(sum(math.log(record["certificate_cost"] / record["baseline_cost"]) for record in selected) / len(selected))
        comparison[family] = {"cases": len(selected), "champion_improvement": summary["family_scores"][family],
                              "certificate_improvement": certificate_score,
                              "champion_to_certificate_cost_ratio": math.exp(sum(math.log(record["certificate_ratio"]) for record in selected) / len(selected)) if all(record["valid"] for record in selected) else None}
    summary["family_comparison"] = comparison
    summary["certificate_core"] = 1 - math.exp(sum(math.log(record["certificate_cost"] / record["baseline_cost"]) for record in records) / len(records))
    summary["maximum_case_seconds"] = max(record.get("seconds", 0) for record in records)
    summary["median_case_seconds"] = statistics.median(record.get("seconds", 0) for record in records)
    summary["baseline_regressions"] = [record["id"] for record in records if record["valid"] and record["ratio"] > 1 + 1e-9]
    summary["substantial_certificate_gaps"] = [record["id"] for record in records if record["valid"] and record["certificate_cost_excess_fraction"] >= 0.15 and record["certificate_improvement_gap"] >= 0.05]
    summary["quality_passed"] = summary["valid"] and summary["core_score"] >= 0.40 and summary["worst_family_score"] >= 0.30
    return summary


def main():
    if (ROOT / "report.json").exists():
        raise SystemExit("Audit already completed; refusing duplicate execution")
    started = time.monotonic()
    manifest, cases, certificates = read_inputs()
    assert (CHAMPION / "solve.py").is_file()
    source_files = {str(path): digest(path) for path in sorted(CHAMPION.rglob("*")) if path.is_file()}
    source_files.update({str(G2 / relative): digest(G2 / relative) for relative in ("evaluator/evaluate.py", "evaluator/routing.py")})
    source_files[str(EVALUATOR.AUTHORING / "sandbox.py")] = digest(EVALUATOR.AUTHORING / "sandbox.py")
    write_json(ROOT / "provenance.json", {"started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "immutable_submission": str(CHAMPION), "source_sha256": source_files,
               "pool_manifest_sha256": digest(POOL / "manifest.json"), "pool_freeze_sha256": digest(POOL / "freeze.json"),
               "contract": CONTRACT, "shared_authoring": str(EVALUATOR.AUTHORING),
               "main_reported_canonical_g2": {"core": 0.6796939800214302, "worst_family": 0.5719491375909949,
                                              "valid_cases": 36, "resources_passed": True, "suite_seconds": 124.60,
                                              "fresh_trial_seconds": 2643.669, "independently_rerun_here": False},
               "baseline_and_certificates_frozen": True, "fresh_agents_launched": 0,
               "certificate_gap_diagnostic_thresholds": {"relative_cost_excess": 0.15, "baseline_normalized_gap": 0.05},
               "timing_policy": "Repeat each failed execution or over-12-second case three times, preserving primary results; timing-only failures never justify G3."})
    records = []
    for case in cases:
        records.append(run_case(case, manifest, certificates, "primary"))
        write_json(ROOT / "progress.json", summarize(records, time.monotonic() - started))
    primary = summarize(records, time.monotonic() - started)
    case_by_id = {case["id"]: case for case in cases}
    rechecks = {}
    resolved = []
    for record in records:
        if record.get("execution_failure") or record.get("timed_out") or record.get("seconds", float("inf")) > 12:
            repeated = [run_case(case_by_id[record["id"]], manifest, certificates, f"timing_recheck_{index + 1}") for index in range(3)]
            rechecks[record["id"]] = repeated
            if not record["valid"]:
                record = next((repeated_record for repeated_record in repeated if repeated_record["valid"]), record)
        resolved.append(record)
    resolved_summary = summarize(resolved, time.monotonic() - started)
    substantial = sorted((record for record in resolved if record["valid"]), key=lambda record: record["certificate_cost_excess_fraction"], reverse=True)
    report = {"status": "complete", "finished_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "primary": primary, "resolved_quality_after_timing_rechecks": resolved_summary,
              "timing_rechecks": rechecks, "certificate_gap_ranking": substantial,
              "genuine_aggregate_quality_failure": resolved_summary["valid"] and not resolved_summary["quality_passed"],
              "audit_passed_without_rechecks": primary["passed"], "generation_3_built": False,
              "quality_targets_not_retuned": True, "fresh_agents_launched": 0}
    for filename, expected in source_files.items():
        assert digest(Path(filename)) == expected
    read_inputs()
    write_json(ROOT / "report.json", report)
    print(json.dumps({"audit_passed": primary["passed"], "valid_cases": primary["valid_cases"],
                      "case_count": primary["case_count"], "core_score": primary["core_score"],
                      "worst_family_score": primary["worst_family_score"], "family_comparison": primary["family_comparison"],
                      "resources_passed": primary["resources_passed"], "runtime_seconds": primary["runtime_seconds"],
                      "maximum_case_seconds": primary["maximum_case_seconds"],
                      "substantial_certificate_gaps": primary["substantial_certificate_gaps"],
                      "timing_recheck_cases": len(rechecks)}, indent=2), flush=True)


def verify_and_freeze():
    manifest, cases, certificates = read_inputs()
    report = json.loads((ROOT / "report.json").read_text())
    provenance = json.loads((ROOT / "provenance.json").read_text())
    assert report["status"] == "complete" and report["primary"]["case_count"] == 24
    assert digest(POOL / "manifest.json") == provenance["pool_manifest_sha256"]
    assert digest(POOL / "freeze.json") == provenance["pool_freeze_sha256"]
    for filename, expected in provenance["source_sha256"].items():
        assert digest(Path(filename)) == expected
    by_id = {case["id"]: case for case in cases}
    all_runs = report["primary"]["cases"] + [record for repeated in report["timing_rechecks"].values() for record in repeated]
    checked = 0
    for record in all_runs:
        if record["valid"]:
            answer = json.loads((ROOT / record["route_artifact"]).read_text())
            score = EVALUATOR.validate(by_id[record["id"]], answer)
            assert abs(score["cost"] - record["cost"]) < 1e-8
            assert record["baseline_cost"] == manifest["baseline"][record["id"]]["cost"]
            assert record["certificate_cost"] == certificates[record["id"]]["design"]["certificate"]["cost"]
            checked += 1
    inventory = {str(path.relative_to(ROOT)): digest(path) for path in sorted(ROOT.rglob("*"))
                 if path.is_file() and path.name != "freeze.json" and "__pycache__" not in path.parts}
    write_json(ROOT / "freeze.json", {"frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "submission_and_inputs_unchanged": True, "replayed_valid_routes": checked,
               "audit_passed_without_rechecks": report["audit_passed_without_rechecks"],
               "genuine_aggregate_quality_failure": report["genuine_aggregate_quality_failure"], "sha256": inventory})
    print(json.dumps({"frozen": True, "exact_routes_replayed": checked, "pool_and_g2_unchanged": True,
                      "audit_passed": report["audit_passed_without_rechecks"],
                      "genuine_aggregate_quality_failure": report["genuine_aggregate_quality_failure"]}, indent=2))


if __name__ == "__main__":
    if sys.argv[1:] == ["--freeze"]:
        verify_and_freeze()
    elif sys.argv[1:]:
        raise SystemExit("Usage: audit.py [--freeze]")
    else:
        main()
