import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "pilots" / "c03_resonance_compiler"
sys.path.insert(0, str(PILOT / "private"))
spec = importlib.util.spec_from_file_location("compiler_evaluator", PILOT / "private" / "evaluator.py")
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


def repair(split):
    logs = ROOT / "authoring" / "runs" / PILOT.name / "screening"
    path = logs / (split + "_evaluation.json")
    original_path = logs / (split + "_pre_startup_grace.json")
    if not original_path.exists():
        original_path.write_bytes(path.read_bytes())
    original = json.loads(original_path.read_text())
    metadata = json.loads((logs / "result.json").read_text())
    manifest = json.loads((PILOT / "private" / "manifest.json").read_text())
    entries = {evaluator.read_frozen(entry["case_path"], entry["case_file_sha256"])["id"]: entry
               for entry in manifest["splits"][split]}
    cases = []
    retries = []
    for report in original["cases"]:
        if report.get("runner_error") != "case wall-time limit exceeded":
            cases.append(report)
            continue
        entry = entries[report["id"]]
        case = evaluator.read_frozen(entry["case_path"], entry["case_file_sha256"])
        truth = evaluator.read_frozen(entry["reference_path"], entry["reference_file_sha256"])
        execution = evaluator.run_solver(metadata["attempt"], metadata["participant"], case,
                                         timeout=60, memory_gib=6, startup_grace=30)
        answer = execution.get("result") if execution.get("ok") else {}
        replacement = evaluator.score_answer(case, truth["answer"]["certificate"], answer, entry["anchors"])
        replacement.update({"id": case["id"], "family": case["family"], "length": case["length"],
                            "seconds": execution.get("seconds"), "wall_seconds": execution.get("wall_seconds"),
                            "cpu_seconds": execution.get("cpu_seconds"),
                            "max_rss_kib": execution.get("max_rss_kib"),
                            "runner_ok": bool(execution.get("ok")), "runner_error": execution.get("error")})
        cases.append(replacement)
        retries.append({"id": case["id"], "original": report, "corrected": replacement})
        print(json.dumps({"split": split, "id": case["id"], "score": replacement["score"],
                          "worker_seconds": execution.get("seconds"), "ok": execution.get("ok")}), flush=True)
    result = evaluator.summarize(cases)
    result.update({"split": split, "case_count": len(cases), "manifest_version": manifest["version"],
                   "timing_audit": {"worker_budget_seconds": 60, "namespace_startup_grace_seconds": 30,
                                    "preserved_original": original_path.name,
                                    "unchanged_submission": metadata["submission_sha256"], "retries": retries}})
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"split": split, "mean_core": result["mean_core"],
                      "worst_family": result["worst_family"], "retries": len(retries)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("screening", "challenge"), required=True)
    repair(parser.parse_args().split)
