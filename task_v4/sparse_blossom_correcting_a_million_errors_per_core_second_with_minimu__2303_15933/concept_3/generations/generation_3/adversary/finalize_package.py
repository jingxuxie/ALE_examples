import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT.parents[1]
PREPARATION = CONCEPT / "adversary/final_scaling_preparation"
MANIFEST = ROOT / "evaluator/hidden/package_manifest.json"
NUMERICAL_RULES = (
    "mean_family_log_rmse_max", "worst_regime_family_log_rmse_max", "shot_budget",
    "max_queries", "max_shots_per_query", "cpu_seconds_per_episode",
    "wall_seconds_per_episode", "initialization_allowance_seconds",
    "address_space_bytes", "episodes_per_regime", "regimes", "metric",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative):
    return json.loads((ROOT / relative).read_text())


def write(relative, data):
    destination = ROOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2) + "\n")


def check_originals():
    frozen = json.loads((PREPARATION / "frozen_snapshot.json").read_text())
    for absolute, expected in frozen.items():
        assert digest(Path(absolute)) == expected, absolute
    return len(frozen)


def check_selected_source():
    selection = load("adversary/selected_champion_manifest.json")
    assert selection["provisional_selection"] is False
    assert selection["selected_by_main"] == "generation_2_v1"
    original = Path(selection["source"])
    supplied = ROOT / "participant/baseline/previous_champion"
    expected = selection["files"]
    assert len(expected) == 88
    assert {str(path.relative_to(supplied)) for path in supplied.rglob("*") if path.is_file()} == set(expected)
    for relative, expected_hash in expected.items():
        assert digest(original / relative) == expected_hash, relative
        assert digest(supplied / relative) == expected_hash, relative
    return expected["solution.py"]


def check_qualification(targets):
    reports = {}
    for name in ("robust", "uniform", "weak_bounded"):
        report = load(f"adversary/validation/{name}_report.json")
        assert report["valid"] and report["complete_qualification"]
        assert report["passed"] == (name == "robust")
        assert len(report["episodes"]) == 12
        assert not report["fresh_agent"] and not report["official_suite"]
        for key in NUMERICAL_RULES:
            assert report["targets"][key] == targets[key], (name, key)
        source = ROOT / ("participant/baseline/solution.py" if name == "weak_bounded" else "adversary/portfolio/solution.py")
        assert report["source_sha256"] == digest(source)
        for result in report["episodes"]:
            assert result["valid"]
            assert result["shots_used"] <= targets["shot_budget"]
            assert result["queries"] <= targets["max_queries"]
            assert result["cpu_seconds"] <= targets["cpu_seconds_per_episode"]
            leaf = ROOT / "adversary/runtime" / name / result["id"] / "submission"
            assert digest(leaf / "solution.py") == digest(source)
            if name != "weak_bounded":
                assert digest(leaf / "local_model.py") == digest(ROOT / "adversary/portfolio/local_model.py")
        reports[name] = {key: report[key] for key in ("valid", "passed", "mean_family_log_rmse", "worst_regime_family_log_rmse", "source_sha256")}
        reports[name]["maximum_cpu_seconds"] = max(result["cpu_seconds"] for result in report["episodes"])
    return reports


def verify():
    manifest = json.loads(MANIFEST.read_text())
    for relative, expected in manifest["files"].items():
        assert digest(ROOT / relative) == expected, relative
    assert load("participant/input/targets.json") == load("evaluator/hidden/targets.json")
    check_originals()
    check_selected_source()
    print(json.dumps({"verified": True, "protected_files": len(manifest["files"]), "selected_source_files": 88}))


def seal():
    assert not MANIFEST.exists(), "Package is already sealed; use --verify."
    assert not (ROOT / "evaluator/hidden/freeze.json").exists()
    targets = load("evaluator/hidden/targets.json")
    assert targets == load("participant/input/targets.json")
    proposal = load("adversary/target_proposal.json")["targets"]
    for key in NUMERICAL_RULES:
        assert proposal[key] == targets[key], key
    original_count = check_originals()
    champion_hash = check_selected_source()
    reports = check_qualification(targets)
    episodes_hash = digest(ROOT / "evaluator/hidden/episodes.json")
    snapshot = load("adversary/draft_snapshot.json")["files"]
    assert episodes_hash == snapshot["evaluator/hidden/episodes.json"]
    science = load("adversary/validation/science.json")
    assert science["validation_passed"] and science["episodes_checked"] == 12
    assert science["episodes_sha256"] == episodes_hash
    for relative in ("adversary/validation/width_audit.json", "adversary/validation/runtime_audit.json"):
        assert load(relative)["passed"]
    public_report = load("adversary/public_allowlist/submission/training_report.json")
    assert public_report["valid"] and public_report["episode"] == "training_triangular_D44"
    syntax_count = 0
    for directory in (ROOT / "participant", ROOT / "evaluator"):
        for path in directory.rglob("*"):
            assert not path.is_symlink(), path
            if path.suffix == ".py":
                ast.parse(path.read_text(), filename=str(path))
                syntax_count += 1
    evidence = ROOT / "adversary/validation/selected_champion_controls"
    evidence.mkdir(parents=True, exist_ok=True)
    control_count = 0
    for topology in ("ladder", "patch", "triangular"):
        source = PREPARATION / f"runs/selected_v1_{topology}.json"
        data = json.loads(source.read_text())
        assert len(data["cases"]) == 4
        for result in data["cases"]:
            assert not result["valid"]
            assert result["reason"] == "memory_error_under_3GiB_cap"
            assert result["shots_used"] == 0
            assert result["complete_source_files_unchanged"]
            assert result["source_sha256"] == champion_hash
            control_count += 1
        shutil.copyfile(source, evidence / source.name)
    for name in ("selected_projection_information.json", "selected_projection_information.py"):
        shutil.copyfile(PREPARATION / name, ROOT / "adversary/validation" / name)
    stamp = datetime.now(timezone.utc).isoformat()
    freeze = {
        "version": "connected-calibration-generation-3", "generation": 3,
        "frozen_utc": stamp, "targets_declared_utc": targets["proposal_utc"],
        "targets_sha256": digest(ROOT / "evaluator/hidden/targets.json"),
        "episodes_sha256": episodes_hash,
        "target_proposal_sha256": digest(ROOT / "adversary/target_proposal.json"),
        "numerical_rules_unchanged_since_proposal": True,
        "hidden_episodes_unchanged_since_proposal": True,
        "selected_champion": "generation_2_v1", "selected_champion_solution_sha256": champion_hash,
        "frozen_before_any_generation_3_fresh_launch": True,
    }
    write("evaluator/hidden/freeze.json", freeze)
    for directory in ("attempts", "champions", "adversary"):
        (ROOT / directory).mkdir(exist_ok=True)
    protected = {}
    for directory in (ROOT / "participant", ROOT / "evaluator"):
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path != MANIFEST:
                protected[str(path.relative_to(ROOT))] = digest(path)
    write("evaluator/hidden/package_manifest.json", {
        "frozen_utc": stamp, "files": protected,
        "scope": "Generation-3 participant and evaluator; excludes this manifest itself.",
        "selected_champion_file_count": 88, "selected_champion_solution_sha256": champion_hash,
    })
    write("adversary/validation/package_audit.json", {
        "passed": True, "utc": stamp, "original_and_generation_2_protected_files_unchanged": original_count,
        "selected_champion_files_exact": 88, "selected_champion_stress_failures": control_count,
        "parsed_python_files": syntax_count, "protected_files": len(protected),
        "numerical_targets_unchanged": True, "hidden_episodes_unchanged": True,
        "public_allowlist_largest_episode_valid": True, "policies": reports,
        "private_policies_are_not_fresh_agents": True,
    })
    write("status.json", {
        "generation": 3, "status": "ready_for_main_audit", "frozen": True,
        "fresh_launches": 0, "selected_previous_champion": "generation_2_v1",
        "classification": "qualified_latent_blind_achievable_fresh_untested",
        "mean_target": targets["mean_family_log_rmse_max"],
        "worst_target": targets["worst_regime_family_log_rmse_max"],
        "final_generation": True, "main_owns_fresh_launch_and_root_status": True,
    })
    verify()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    arguments = parser.parse_args()
    if arguments.verify:
        verify()
    else:
        seal()


if __name__ == "__main__":
    main()
