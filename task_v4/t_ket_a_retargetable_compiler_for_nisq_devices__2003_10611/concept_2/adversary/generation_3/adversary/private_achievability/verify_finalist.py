import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent
GENERATION = OUTPUT.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_hashes():
    paths = set()
    for directory in ("participant", "evaluator"):
        paths.update(path for path in (GENERATION / directory).rglob("*") if path.is_file())
    paths.update(GENERATION / name for name in (
        "status.json", "adversary/frozen_manifest.json", "adversary/freeze.json"))
    return {str(path.relative_to(GENERATION)): digest(path) for path in sorted(paths)}


def main():
    started = time.monotonic()
    summary = json.loads((OUTPUT / "summary.json").read_text())
    manifest = json.loads((GENERATION / "adversary/frozen_manifest.json").read_text())
    assert all(digest(GENERATION / name) == expected for name, expected in manifest.items())
    before = frozen_hashes()
    best = summary["best"]
    witness = GENERATION / best["best_artifact"]
    assert digest(witness) == best["sha256"]
    command = [sys.executable, "-I", "-B", str(GENERATION / "evaluator/evaluate.py"),
               "--solution-dir", str(witness.parent)]
    process = subprocess.run(command, cwd=OUTPUT, capture_output=True, text=True, timeout=180)
    (OUTPUT / "best/recheck_stdout.json").write_text(process.stdout)
    (OUTPUT / "best/recheck_stderr.txt").write_text(process.stderr)
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result == best["result"]
    assert result["valid"]
    assert result["target"] == {"swap_ratio": 2.5, "native_ratio": 1.35, "swap_gap": 16}
    assert len(result["families"]) == 6
    assert all(len(family["settings"]) == 62 for family in result["families"])
    after = frozen_hashes()
    assert before == after
    assert summary["frozen_sources_unchanged"]
    report = {
        "generation": 3,
        "achievability": "proven" if result["passed"] else "unknown",
        "candidate_artifact": str(witness.relative_to(GENERATION)),
        "candidate_sha256": digest(witness),
        "corpus_candidates_requested": summary["candidates_requested"],
        "corpus_candidates_completed": summary["candidates_completed"],
        "corpus_candidates_valid": summary["candidates_valid"],
        "corpus_candidates_passed": summary["candidates_passed"],
        "passing_candidates": summary["passing_candidates"],
        "additional_generated_trials": 0,
        "proxy_evaluations": 0,
        "best_exact_rechecks": 1,
        "portfolio_routes_replayed_in_corpus": summary["portfolio_routes_replayed"],
        "portfolio_routes_replayed_in_recheck": 372,
        "portfolio_routes_replayed_total": summary["portfolio_routes_replayed"] + 372,
        "best_exact_result": result,
        "frozen_manifest_entries_matched": len(manifest),
        "frozen_hashes_before": before,
        "frozen_hashes_after": after,
        "frozen_artifacts_unchanged": True,
        "fresh_attempts_inspected": False,
        "fresh_agents_launched": 0,
        "corpus_seconds": summary["seconds"],
        "final_recheck_seconds": time.monotonic() - started,
        "search_stopped_after_preserved_candidate_pass": True,
    }
    (OUTPUT / "final_verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("best_exact_result", "frozen_hashes_before", "frozen_hashes_after")},
                     indent=2))


if __name__ == "__main__":
    main()
