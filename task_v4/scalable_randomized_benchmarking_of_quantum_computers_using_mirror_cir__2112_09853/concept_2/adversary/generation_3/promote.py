import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import subprocess


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
    subprocess.run(["apply_patch"], input=patch + "*** End Patch\n", text=True, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, default=2000)
    arguments = parser.parse_args()
    budget = arguments.budget
    confirmation = json.loads((AREA / "confirmation.json").read_text())
    summary = next(row for row in confirmation["summaries"] if row["budget"] == budget)
    assert summary["valid"] and summary["episodes"] == 24 and not summary["quality_target_met"]
    assert not confirmation["sampler_rescaled"]
    selected_records = [record for record in confirmation["records"] if record["budget"] == budget]
    prior_proxy = sum(record["diagnostics"]["known_support_spam_prior_moment_fisher_proxy"] for record in selected_records) / len(selected_records)
    assert prior_proxy < 1, "review low-shot noise headroom before freezing"
    manifest_path = ROOT / "evaluator/hidden/manifest.json"
    old_manifest = json.loads(manifest_path.read_text())
    for relative, expected in old_manifest["files"].items():
        assert digest(ROOT / relative) == expected, relative
    old_manifest_hash = digest(manifest_path)
    assert old_manifest_hash == "8f4433401c41e825d29c4643d88a65fd70fea7e9c901dd998c5d327fc3f1d24a"
    old_status = json.loads((ROOT / "status.json").read_text())
    assert old_status["current_generation"] == 2
    assert (ROOT / "champions/generation_2/sampler.so").is_file()
    assert (ROOT / "adversary/generation_2_snapshot/status.json").is_file()
    changes = {"adversary/generation_3/previous_status.json": json.dumps(old_status, indent=2) + "\n",
               "adversary/generation_3/previous_manifest.json": json.dumps(old_manifest, indent=2) + "\n"}
    limits = json.loads((ROOT / "participant/input/limits.json").read_text())
    limits.update(version="mrb-active-v3", generation=3, shots_budget=budget)
    changes["participant/input/limits.json"] = json.dumps(limits, indent=2) + "\n"
    for relative in ("participant/workspace/model.py", "evaluator/hidden/model.py",
                     "participant/workspace/transport.py", "evaluator/hidden/transport.py"):
        changes[relative] = (ROOT / relative).read_text().replace("12000", str(budget)).replace("mrb-active-v2", "mrb-active-v3")
    for relative in ("participant/TASK.md", "participant/workspace/API.md", "participant/workspace/MODEL.md"):
        source = (ROOT / relative).read_text().replace("12,000", format(budget, ",")).replace("12000", str(budget))
        source = source.replace("Generation 2 fixes", "Generation 3 fixes").replace("mrb-active-v2", "mrb-active-v3")
        source = source.replace("JSON-lines protocol v2", "JSON-lines protocol v3")
        if relative.endswith("API.md"):
            source = source.replace('"context":0.021333333333333333', '"context":' + repr(256 / budget))
            source = source.replace('"shots_remaining":11488', '"shots_remaining":' + str(budget - 512))
            source = source.replace('"shots_used":10000', '"shots_used":' + str(4 * budget // 5))
            source = source.replace("attempts/v_1/submission", "attempts/v_3/submission")
        changes[relative] = source
    baseline = (ROOT / "participant/baseline/policy.py").read_text()
    baseline = baseline.replace('    controls = [[]] + [[edge] for edge in range(edge_count)]\n    shots = min(4096, hello["limits"]["shots_budget"] // (2 * len(controls)))',
        '    budget = hello["limits"]["shots_budget"]\n    control_count = min(edge_count + 1, budget // (2 * hello["limits"]["min_shots"]))\n    measured_count = max(0, control_count - 1)\n    selected_edges = [index * edge_count // measured_count for index in range(measured_count)]\n    controls = [[]] + [[edge] for edge in selected_edges]\n    shots = min(4096, budget // (2 * len(controls)))')
    baseline = baseline.replace('    base = [max(0.0, rate - idle) for rate in rates[1:]]',
        '    measured_base = [max(0.0, rate - idle) for rate in rates[1:]]\n    average_base = sum(measured_base) / max(1, len(measured_base))\n    base = [average_base] * edge_count\n    for edge, rate in zip(selected_edges, measured_base):\n        base[edge] = rate')
    assert baseline != (ROOT / "participant/baseline/policy.py").read_text()
    changes["participant/baseline/policy.py"] = baseline
    freeze = (ROOT / "evaluator/hidden/freeze.py").read_text().replace('"mrb-active-v2", "frozen_utc"', '"mrb-active-v3", "generation": 3, "frozen_utc"')
    freeze = freeze.replace('root / "participant/workspace/API.md", root / "participant/TASK.md"]',
                            'root / "participant/workspace/API.md", root / "participant/TASK.md",\n               root / "participant/workspace/model.py", root / "participant/workspace/transport.py",\n               root / "participant/workspace/develop.py", root / "participant/baseline/policy.py"]')
    changes["evaluator/hidden/freeze.py"] = freeze
    edit_files(changes)
    specification = importlib.util.spec_from_file_location("generation_three_model", ROOT / "evaluator/hidden/model.py")
    model = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(model)
    excluded = set()
    for relative in ("evaluator/hidden/benchmark.json", "adversary/generation_1_snapshot/evaluator/hidden/benchmark.json"):
        excluded.update(row["seed_hex"] for row in json.loads((ROOT / relative).read_text())["episodes"])
    for path in AREA.glob("cases_*.json"):
        excluded.update(row["seed_hex"] for row in json.loads(path.read_text()))
    cases = []
    for family in model.FAMILIES:
        for shape in model.SHAPES:
            seed = secrets.token_hex(16)
            while seed in excluded or int(seed, 16) < 2 ** 64:
                seed = secrets.token_hex(16)
            excluded.add(seed)
            episode = model.Episode(int(seed, 16), family, shape)
            parameters = {"idle": episode.idle, "base": episode.base.tolist(), "cross": episode.crosstalk.tolist(),
                          "spam_intercept": episode.spam_intercept, "spam_edges": episode.spam_edges.tolist(),
                          "spam_density": episode.spam_density,
                          "drift": [episode.drift_amplitude, episode.drift_frequency, episode.drift_phase, episode.drift_slope]}
            cases.append({"id": family + "_" + "x".join(map(str, shape)), "family": family, "shape": list(shape),
                          "seed_hex": seed,
                          "targets_sha256": hashlib.sha256(json.dumps(episode.targets, separators=(",", ":")).encode()).hexdigest(),
                          "parameters_sha256": hashlib.sha256(json.dumps(parameters, sort_keys=True, separators=(",", ":")).encode()).hexdigest()})
    frozen = datetime.now(timezone.utc).isoformat()
    benchmark = {"benchmark_id": "mrb-active-v3", "generation": 3, "frozen_utc": frozen,
                 "seed_source": "Fresh private 128-bit seeds, disjoint from G1/G2 hidden, G3 calibration and standard public development seeds.",
                 "fixed_before_fresh_attempts": True, "target": limits, "episodes": cases}
    edit_files({"evaluator/hidden/benchmark.json": json.dumps(benchmark, indent=2) + "\n"})
    manifest = dict(old_manifest, frozen_utc=frozen, generation=3,
                    previous_generation_manifest_sha256=old_manifest_hash,
                    generation_change="Final shot-budget ratchet only; partial-calibration weak baseline repaired. CPTP law, priors, quality and runtime limits unchanged.")
    paths = set(old_manifest["files"])
    paths.update(("participant/workspace/model.py", "participant/workspace/transport.py",
                  "participant/workspace/develop.py", "participant/baseline/policy.py"))
    manifest["files"] = {relative: digest(ROOT / relative) for relative in sorted(paths)}
    edit_files({"evaluator/hidden/manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n"})
    status = dict(old_status)
    status.update(generation=3, current_generation=3, status="generation_3_frozen_validating",
                  ratchet_generations=2, remaining_ratchets=0, final_generation=True,
                  current_generation_fresh_attempts=[], current_generation_champion=None,
                  champion_generation=2, champion="champions/generation_2", participant_ready_for_main_runner=False,
                  package_frozen=True, package_frozen_utc=frozen, target_frozen_before_attempt=True,
                  manifest_sha256=digest(ROOT / "evaluator/hidden/manifest.json"),
                  benchmark_sha256=digest(ROOT / "evaluator/hidden/benchmark.json"),
                  solvability="hard_open_at_generation_3_budget",
                  attainability="No passing 2,000-shot policy claimed. Prior-aware known-support/SPAM Fisher diagnostics are optimistic only, not proof.",
                  stronger_reference="Actual archived G2 Bayesian sampler, byte-identical compiled library and full chain/runtime schedule; only budget allocation/context adapted.",
                  difficulty_claim="Independent valid full-sampler champion quality failure at 2,000 shots; G3 fresh-agent hardness remains untested.",
                  baseline_report="evaluator/hidden/generation_3_baseline_report.json",
                  selfcheck_report="evaluator/hidden/generation_3_selfcheck_report.json",
                  private_audit="adversary/generation_3/frontier_audit.json",
                  minimal_budget_adapted_champion={"valid": True, "average_score": summary["average_score"],
                                                  "worst_family_score": summary["worst_family_score"], "isolation": "bwrap",
                                                  "report": "adversary/generation_3/confirmation.json"})
    status["target"] = dict(status["target"], shot_budget_per_episode=budget)
    status.pop("additional_holdout_report", None)
    status.pop("adapted_champion_frozen_suite_report", None)
    status.pop("ready_utc", None)
    status.pop("private_audit_sha256", None)
    edit_files({"status.json": json.dumps(status, indent=2) + "\n"})
    print(json.dumps({"generation": 3, "budget": budget, "frozen_utc": frozen,
                      "prior_moment_fisher_proxy": prior_proxy, "manifest_sha256": status["manifest_sha256"]}))


if __name__ == "__main__":
    main()
