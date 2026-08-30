import ast
import datetime
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = ROOT / "evaluator/hidden/package_manifest.json"
    if manifest_path.exists():
        raise RuntimeError("Package already finalized; do not silently refreeze")
    freeze = json.loads((ROOT / "evaluator/hidden/freeze.json").read_text())
    for relative, key in (("evaluator/hidden/targets.json", "targets_sha256"),
                          ("evaluator/hidden/episodes.json", "episodes_sha256")):
        assert digest(ROOT / relative) == freeze[key]
    private_targets = json.loads((ROOT / "evaluator/hidden/targets.json").read_text())
    public_targets = json.loads((ROOT / "participant/input/targets.json").read_text())
    assert all(private_targets[key] == value for key, value in public_targets.items())
    assert digest(ROOT / "participant/baseline/previous_champion.py") == freeze["source_champion_sha256"]
    for path in ROOT.rglob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    results = {}
    for policy in ("weak", "uniform", "static", "adaptive", "robust"):
        report = json.loads((ROOT / "adversary/validation" / (policy + "_report.json")).read_text())
        assert report["valid"] and len(report["episodes"]) == 12
        assert report["passed"] == (policy not in ("weak", "uniform"))
        results[policy] = {key: report[key] for key in ("valid", "passed", "core_score", "worst_family_score", "runtime_score",
                                                      "mean_family_log_rmse", "worst_regime_family_log_rmse")}
    science = json.loads((ROOT / "adversary/validation/science.json").read_text())
    assert science["validation_passed"] and science["episodes_checked"] == 12
    assert json.loads((ROOT / "adversary/validation/runtime_audit.json").read_text())["passed"]
    assert json.loads((ROOT / "adversary/validation/public_allowlist_final.log").read_text())["valid"]
    original = ROOT.parents[1]
    expected = json.loads((original / "adversary/scaling_stress/frozen_snapshot.json").read_text())
    actual = {str(path.relative_to(original)): digest(path) for directory in ("participant", "evaluator")
              for path in (original / directory).rglob("*") if path.is_file()}
    assert expected == actual
    files = {str(path.relative_to(ROOT)): digest(path) for directory in ("participant", "evaluator")
             for path in (ROOT / directory).rglob("*") if path.is_file()}
    package = {"generation": 2, "sealed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "targets_sha256": freeze["targets_sha256"], "episodes_sha256": freeze["episodes_sha256"],
               "original_champion_sha256": freeze["source_champion_sha256"], "files": files,
               "original_participant_evaluator_unchanged": True, "fresh_launches": 0}
    manifest_path.write_text(json.dumps(package, indent=2) + "\n")
    status = {"generation": 2, "status": "ready_for_main_audit", "fresh_launches": 0,
              "difficulty_status": "known_achievable_no_fresh_generation_2_trial",
              "targets_frozen_before_policy_trials": True, "private_fixtures_frozen_before_qualification": True,
              "known_latent_blind_passing_policies": ["static", "adaptive", "robust"],
              "supplied_baseline": "participant/baseline/solution.py", "provided_baseline_passes": False,
              "worker_command": ["/usr/bin/python3", "/submission/solution.py"],
              "runtime_dependencies": ["/usr/bin/python3", "/usr/lib/python3/dist-packages/numpy",
                                       "/usr/lib/python3/dist-packages/scipy", "/usr/bin/bwrap"],
              "qualification": results, "main_owns_original_status_and_fresh_promotion": True,
              "package_manifest_sha256": digest(manifest_path),
              "limitations": ["Static nonuniform design also passes; data-dependent adaptivity is not proved necessary.",
                              "One ordinary adaptive supplementary tape narrowly fails worst-cell accuracy; its result is retained.",
                              "Local identifiability and numerical multi-start checks are not a global uniqueness theorem."]}
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"ready": True, "package_manifest_sha256": status["package_manifest_sha256"],
                      "files_sealed": len(files), "original_champion_sha256": freeze["source_champion_sha256"]}), flush=True)


if __name__ == "__main__":
    main()
