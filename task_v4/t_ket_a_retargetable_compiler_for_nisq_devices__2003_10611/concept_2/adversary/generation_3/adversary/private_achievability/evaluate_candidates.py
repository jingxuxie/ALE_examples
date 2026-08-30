import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent
GENERATION = OUTPUT.parents[1]
CONCEPT = GENERATION.parents[1]
EXPECTED_TARGET = {"swap_ratio": 2.5, "native_ratio": 1.35, "swap_gap": 16}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def source_hashes():
    paths = list((GENERATION / "participant/input").glob("*.py"))
    paths.append(GENERATION / "evaluator/evaluate.py")
    return {str(path.relative_to(GENERATION)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def evaluate_candidate(source):
    name = source.parent.name
    directory = OUTPUT / "candidates" / name
    directory.mkdir(parents=True, exist_ok=True)
    contents = source.read_bytes()
    digest = hashlib.sha256(contents).hexdigest()
    (directory / "witness.json").write_bytes(contents)
    started = time.monotonic()
    command = [sys.executable, "-I", "-B", str(GENERATION / "evaluator/evaluate.py"),
               "--solution-dir", str(directory)]
    try:
        process = subprocess.run(command, cwd=OUTPUT, capture_output=True, text=True, timeout=240)
        seconds = time.monotonic() - started
        (directory / "stdout.json").write_text(process.stdout)
        (directory / "stderr.txt").write_text(process.stderr)
        if process.returncode != 0:
            raise RuntimeError(f"trusted evaluator return code {process.returncode}: {process.stderr}")
        result = json.loads(process.stdout)
        full_replays = 0
        if result["valid"]:
            assert result["target"] == EXPECTED_TARGET
            assert len(result["families"]) == 6
            assert len({family["name"] for family in result["families"]}) == 6
            for family in result["families"]:
                assert len(family["settings"]) == 62
                assert len({setting["setting"] for setting in family["settings"]}) == 62
                assert min(setting["swaps"] for setting in family["settings"]) == family["portfolio_swaps"]
                full_replays += len(family["settings"])
            recomputed_pass = all(family["swap_ratio"] >= 2.5 and family["native_ratio"] >= 1.35
                                  and family["swap_gap"] >= 16 for family in result["families"])
            assert result["passed"] == recomputed_pass
        write_json(directory / "exact_result.json", result)
        record = {"candidate": name, "source": str(source.relative_to(CONCEPT)),
                  "artifact": str((directory / "witness.json").relative_to(GENERATION)),
                  "sha256": digest, "seconds": seconds, "completed": True,
                  "portfolio_routes_replayed": full_replays, "result": result}
    except subprocess.TimeoutExpired:
        record = {"candidate": name, "source": str(source.relative_to(CONCEPT)),
                  "sha256": digest, "completed": False, "timed_out": True,
                  "seconds": time.monotonic() - started, "portfolio_routes_replayed": 0}
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    write_json(directory / "evaluation_record.json", record)
    result = record.get("result", {})
    print(json.dumps({"candidate": name, "completed": record["completed"],
                      "valid": result.get("valid"), "passed": result.get("passed"),
                      "core_score": result.get("core_score"),
                      "worst_family_score": result.get("worst_family_score"),
                      "seconds": record["seconds"]}), flush=True)
    return record


def ranking(record):
    result = record.get("result", {})
    margin = min((min(family["swap_ratio"] / 2.5, family["native_ratio"] / 1.35,
                      family["swap_gap"] / 16) for family in result.get("families", [])), default=0)
    return (result.get("passed", False), result.get("valid", False),
            result.get("worst_family_score", 0), result.get("core_score", 0), margin)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    arguments = parser.parse_args()
    started = time.monotonic()
    before = source_hashes()
    sources = sorted((CONCEPT / "adversary/private_candidates").glob("island_*/witness.json"))
    assert len(sources) == 12, "expected twelve preserved private island candidates"
    with concurrent.futures.ThreadPoolExecutor(max_workers=arguments.workers) as pool:
        records = list(pool.map(evaluate_candidate, sources))
    after = source_hashes()
    assert before == after, "frozen G3 sources changed during evaluation"
    ranked = sorted(records, key=ranking, reverse=True)
    passing = [record for record in records if record.get("result", {}).get("passed")]
    best = ranked[0]
    if best.get("result", {}).get("valid"):
        original = GENERATION / best["artifact"]
        destination = OUTPUT / "best" / "witness.json"
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes(original.read_bytes())
        write_json(destination.parent / "exact_result.json", best["result"])
        best = {**best, "best_artifact": str(destination.relative_to(GENERATION))}
    summary = {"generation": 3, "achievability": "proven" if passing else "unknown",
               "candidates_requested": len(sources),
               "candidates_completed": sum(record["completed"] for record in records),
               "candidates_valid": sum(record.get("result", {}).get("valid", False) for record in records),
               "candidates_passed": len(passing), "passing_candidates": [record["candidate"] for record in passing],
               "policies_per_family": 62, "relabeling_families": 6,
               "portfolio_routes_replayed": sum(record["portfolio_routes_replayed"] for record in records),
               "additional_search_trials": 0, "proxy_evaluations_used": 0,
               "source_hashes_before": before, "source_hashes_after": after,
               "frozen_sources_unchanged": before == after, "targets": EXPECTED_TARGET,
               "inspected_v3_attempts": False, "fresh_agents_launched": 0,
               "seconds": time.monotonic() - started, "best": best, "candidates": records}
    write_json(OUTPUT / "summary.json", summary)
    lines = ["# Frozen G3 private achievability", "", f"Result: **{summary['achievability']}**.", "",
             "All reported scores come from the frozen G3 exact checker; no proxy scores are used.",
             "No v_3 attempts were inspected. No policies, targets, or frozen files were changed.", "",
             "| Candidate | Valid | Passed | Core | Worst family | Min SWAP ratio | Min native ratio | Min gap |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for record in records:
        result = record.get("result", {})
        families = result.get("families", [])
        minimum_ratio = min((family["swap_ratio"] for family in families), default=0)
        minimum_native = min((family["native_ratio"] for family in families), default=0)
        minimum_gap = min((family["swap_gap"] for family in families), default=0)
        lines.append(f"| {record['candidate']} | {result.get('valid', False)} | {result.get('passed', False)} | "
                     f"{result.get('core_score', 0):.8f} | {result.get('worst_family_score', 0):.8f} | "
                     f"{minimum_ratio:.8f} | {minimum_native:.8f} | {minimum_gap} |")
    lines.extend(["", f"Completed candidates: {summary['candidates_completed']}/{len(sources)}.",
                  f"Exactly replayed portfolio routes: {summary['portfolio_routes_replayed']}.",
                  f"Passing candidates: {', '.join(summary['passing_candidates']) or 'none'}.",
                  f"Best artifact: `{best.get('best_artifact', 'none')}` (relative to generation_3).",
                  "Detailed counts, all 62 policy results in every family, source hashes, and certificates are in summary.json and candidates/.",
                  ""])
    (OUTPUT / "REPORT.md").write_text("\n".join(lines))
    print(json.dumps({"achievability": summary["achievability"], "passed": len(passing),
                      "completed": summary["candidates_completed"],
                      "routes_replayed": summary["portfolio_routes_replayed"],
                      "best_candidate": best["candidate"],
                      "best_artifact": best.get("best_artifact"),
                      "best_core_score": best.get("result", {}).get("core_score"),
                      "best_worst_family_score": best.get("result", {}).get("worst_family_score"),
                      "seconds": summary["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
