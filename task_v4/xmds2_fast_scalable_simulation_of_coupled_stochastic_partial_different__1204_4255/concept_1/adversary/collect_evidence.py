import hashlib
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
from privileged_planner import ROOT, check, score
from audit_checker import independent_semantics


def main():
    started = time.perf_counter()
    here = Path(__file__).resolve().parent
    cases = json.loads((ROOT / "evaluator" / "hidden" / "cases.json").read_text())
    by_id = {case["id"]: case for case in cases}
    selected = {}
    summaries = []
    for path in sorted(list(here.glob("search_*.json")) + list(here.glob("runtime_*.json"))):
        report = json.loads(path.read_text())
        if not report.get("complete", report.get("valid", False)):
            continue
        plans_path = path.with_suffix(".plans.jsonl")
        if not plans_path.exists():
            continue
        answers = [json.loads(line) for line in plans_path.read_text().splitlines()]
        if len(answers) != len(report["cases"]) or len(answers) != len(cases):
            raise AssertionError("Incomplete evidence file")
        for row, answer in zip(report["cases"], answers):
            case = by_id[row["id"]]
            exact = check(case["instance"], answer)
            if exact["cost"] != row["cost"]:
                raise AssertionError("Stored score differs from exact checker")
            previous = selected.get(row["id"])
            if previous is None or exact["cost"] < previous["cost"]:
                selected[row["id"]] = {"cost": exact["cost"], "answer": answer, "source": path.name}
        summaries.append({key: report[key] for key in ["cost", "core_score", "worst_family_score", "family_scores", "elapsed_seconds", "cpu_seconds", "maxrss_kib"] if key in report} | {"source": path.name})
    if len(selected) != len(cases):
        raise AssertionError("Missing hidden cases")
    rows = []
    answers = []
    for case in cases:
        chosen = selected[case["id"]]
        result = check(case["instance"], chosen["answer"])
        independent = independent_semantics(case["instance"], chosen["answer"])
        if any(result[key] != independent[key] for key in ["cost", "peak_memory", "reads"]):
            raise AssertionError("Independent hidden replay mismatch")
        rows.append({"id": case["id"], "family": case["family"], "source": chosen["source"], "baseline_cost": case["baseline"]["cost"], "ratio": result["cost"] / case["baseline"]["cost"], "max_fourier_error": independent["max_fourier_error"], **result})
        answers.append(chosen["answer"])
    plans_path = here / "best_privileged.plans.jsonl"
    plans_path.write_text("".join(json.dumps(answer, separators=(",", ":")) + "\n" for answer in answers))
    audit = json.loads((here / "audit_results.json").read_text())
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in audit["hashes"]}
    result = {**score(rows), "valid": True, "cases": rows, "runs": summaries, "plan_sha256": hashlib.sha256(plans_path.read_bytes()).hexdigest(), "frozen_hashes": hashes, "protected_hashes_unchanged_since_audit": hashes == audit["hashes"], "independent_fourier_reads": sum(row["reads"] for row in rows), "max_fourier_error": max(row["max_fourier_error"] for row in rows), "verification_elapsed_seconds": time.perf_counter() - started, "classification": "Privileged generation-only best-of validated schedules. Not a 120-second participant submission; no achievability or impossibility inference beyond measured schedules.", "completed_search_cpu_seconds": sum(item["cpu_seconds"] for item in summaries if item["source"].startswith("search_"))}
    (here / "best_privileged.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ["cases", "frozen_hashes"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
