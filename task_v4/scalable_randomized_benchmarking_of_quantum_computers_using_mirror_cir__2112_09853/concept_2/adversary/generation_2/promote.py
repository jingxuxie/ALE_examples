import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def edit_files(changes):
    patch = "*** Begin Patch\n"
    for relative, after in changes.items():
        path = ROOT / relative
        if path.exists():
            patch += "*** Update File: " + relative + "\n@@\n"
            patch += "".join("-" + line + "\n" for line in path.read_text().splitlines())
        else:
            patch += "*** Add File: " + relative + "\n"
        patch += "".join("+" + line + "\n" for line in after.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, cwd=ROOT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, default=12000)
    arguments = parser.parse_args()
    budget = arguments.budget
    assert budget >= 32 * 82
    confirmation = json.loads((AREA / ("confirm_" + str(budget) + "_bwrap.json")).read_text())
    summary = confirmation["summaries"][0]
    assert summary["valid"] and not summary["quality_target_met"], "require a valid quality failure, not a resource or protocol failure"
    old_manifest = json.loads((ROOT / "evaluator/hidden/manifest.json").read_text())
    for relative, expected in old_manifest["files"].items():
        assert digest(ROOT / relative) == expected, relative
    old_manifest_hash = digest(ROOT / "evaluator/hidden/manifest.json")
    old_benchmark = json.loads((ROOT / "evaluator/hidden/benchmark.json").read_text())
    assert old_benchmark["benchmark_id"] == "mrb-active-v1"
    assert (ROOT / "adversary/generation_1_snapshot").is_dir()
    assert (ROOT / "champions/generation_1").is_dir()
    changes = {}
    limits = json.loads((ROOT / "participant/input/limits.json").read_text())
    limits.update(version="mrb-active-v2", generation=2, shots_budget=budget)
    changes["participant/input/limits.json"] = json.dumps(limits, indent=2) + "\n"
    for relative in ("participant/workspace/model.py", "evaluator/hidden/model.py",
                     "participant/workspace/transport.py", "evaluator/hidden/transport.py"):
        source = (ROOT / relative).read_text()
        changes[relative] = source.replace("240000", str(budget)).replace("mrb-active-v1", "mrb-active-v2")
    for relative in ("participant/TASK.md", "participant/workspace/MODEL.md", "participant/workspace/API.md"):
        source = (ROOT / relative).read_text()
        source = source.replace("240,000", format(budget, ",")).replace("240000", str(budget)).replace("mrb-active-v1", "mrb-active-v2")
        if relative.endswith("API.md"):
            source = source.replace("JSON-lines protocol v1", "JSON-lines protocol v2")
            source = source.replace("0.0010666666666666667", repr(256 / budget))
            source = source.replace('"shots_remaining":239488', '"shots_remaining":' + str(budget - 512))
            source = source.replace('"shots_used":100000', '"shots_used":' + str(budget - 2000))
        if relative.endswith("TASK.md"):
            source = source.replace("## Objective and resources", "## Objective and resources\n\nGeneration 2 fixes a " + format(budget, ",") + "-shot budget; all four physical families and the quality targets remain the same.")
        changes[relative] = source
    changes["evaluator/hidden/freeze.py"] = (ROOT / "evaluator/hidden/freeze.py").read_text().replace("mrb-active-v1", "mrb-active-v2")
    edit_files(changes)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "evaluator"))
    from hidden.model import Episode, FAMILIES, SHAPES
    excluded = {case["seed_hex"] for case in old_benchmark["episodes"]}
    for path in AREA.glob("cases_*.json"):
        excluded.update(case["seed_hex"] for case in json.loads(path.read_text()))
    episodes = []
    for family in FAMILIES:
        for shape in SHAPES:
            seed = secrets.token_hex(16)
            while seed in excluded:
                seed = secrets.token_hex(16)
            excluded.add(seed)
            episode = Episode(int(seed, 16), family, shape)
            parameters = {"idle": episode.idle, "base": episode.base.tolist(), "cross": episode.crosstalk.tolist(),
                          "spam_intercept": episode.spam_intercept, "spam_edges": episode.spam_edges.tolist(),
                          "spam_density": episode.spam_density,
                          "drift": [episode.drift_amplitude, episode.drift_frequency, episode.drift_phase, episode.drift_slope]}
            episodes.append({"id": family + "_" + "x".join(map(str, shape)), "family": family,
                             "shape": list(shape), "seed_hex": seed,
                             "targets_sha256": hashlib.sha256(json.dumps(episode.targets, separators=(",", ":")).encode()).hexdigest(),
                             "parameters_sha256": hashlib.sha256(json.dumps(parameters, sort_keys=True, separators=(",", ":")).encode()).hexdigest()})
    frozen = datetime.now(timezone.utc).isoformat()
    benchmark = {"benchmark_id": "mrb-active-v2", "generation": 2, "frozen_utc": frozen,
                 "seed_source": "independent 128-bit secrets; explicitly disjoint from generation 1 and calibration/confirmation seeds",
                 "fixed_before_fresh_attempts": True, "target": limits, "episodes": episodes}
    edit_files({"evaluator/hidden/benchmark.json": json.dumps(benchmark, indent=2) + "\n"})
    manifest = dict(old_manifest)
    manifest.update(generation=2, frozen_utc=frozen, previous_generation_manifest_sha256=old_manifest_hash,
                    generation_change="Shot budget only; normalized budget-time SPAM context and resource reporting synchronized. Quality and CPTP law unchanged.")
    manifest["files"] = {relative: digest(ROOT / relative) for relative in old_manifest["files"]}
    edit_files({"evaluator/hidden/manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n"})
    status = json.loads((ROOT / "status.json").read_text())
    history = status.setdefault("generation_history", [])
    history.append({"generation": 1, "budget": 240000, "corrected_average_score": 0.9837741181932067,
                    "corrected_worst_family_score": 0.9815645178623729,
                    "manifest_sha256": old_manifest_hash, "snapshot": "adversary/generation_1_snapshot",
                    "champion": "champions/generation_1", "runtime_bug_audit": "adversary/generation_2/environment_fix/correction_audit.json"})
    status.update(generation=2, status="generation_2_frozen_validating", package_frozen=True, package_frozen_utc=frozen,
                  target_frozen_before_attempt=True, current_generation_fresh_attempts=[], ratchet_generations=1,
                  manifest_sha256=digest(ROOT / "evaluator/hidden/manifest.json"),
                  benchmark_sha256=digest(ROOT / "evaluator/hidden/benchmark.json"),
                  participant_ready_for_main_runner=False,
                  baseline_report="evaluator/hidden/generation_2_baseline_report.json",
                  selfcheck_report="evaluator/hidden/generation_2_selfcheck_report.json",
                  private_audit="adversary/generation_2/frontier_audit.json",
                  attainability="Hard open at selected budget; no passing 12,000-shot policy claimed. Known-support/SPAM Fisher estimates are optimistic diagnostics only.",
                  minimal_budget_adapted_champion={"valid": summary["valid"], "average_score": summary["average_score"],
                                                  "worst_family_score": summary["worst_family_score"], "isolation": "bwrap",
                                                  "report": "adversary/generation_2/confirm_" + str(budget) + "_bwrap.json"})
    status["target"]["shot_budget_per_episode"] = budget
    edit_files({"status.json": json.dumps(status, indent=2) + "\n"})
    print(json.dumps({"generation": 2, "budget": budget, "frozen_utc": frozen, "manifest_sha256": status["manifest_sha256"]}))


if __name__ == "__main__":
    main()
