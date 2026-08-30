from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def replace(path, text):
    if path.exists():
        patch = "*** Begin Patch\n*** Update File: " + str(path) + "\n@@\n"
        patch += "".join("-" + line + "\n" for line in path.read_text().splitlines())
    else:
        patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n"
    patch += "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)


def main():
    archive = ROOT / "generations" / "generation_0"
    archive_manifest = json.loads((archive / "archive_manifest.json").read_text())
    archive_mismatches = [name for name, expected in archive_manifest["files"].items()
                          if hashlib.sha256((archive / name).read_bytes()).hexdigest() != expected]
    relocations = json.loads((HERE / "raw_attempt_relocations.json").read_text())
    score_hashes = json.loads((HERE / "original_score_hashes.json").read_text())
    score_mismatches = []
    for name, expected in score_hashes.items():
        destination = name
        for source, target in relocations.items():
            if name == source or name.startswith(source + "/"):
                destination = target + name[len(source):]
                break
        if hashlib.sha256((ROOT / destination).read_bytes()).hexdigest() != expected:
            score_mismatches.append(name)
    champion_manifest = json.loads((HERE.parent / "archive_manifest.json").read_text())
    champion_mismatches = [name for name, expected in champion_manifest["files"].items()
                           if hashlib.sha256((ROOT / "champions" / "generation_1" / name).read_bytes()).hexdigest() != expected]
    assert not archive_mismatches and not score_mismatches and not champion_mismatches
    audit = json.loads((HERE / "audit_report.json").read_text())
    assert audit["passed"] and not audit["private_artifact_leaks"]
    grades = json.loads((HERE / "grade_summary.json").read_text())
    assert len(grades) == 7 and all(result["valid"] for result in grades.values())
    private = {name: result for name, result in grades.items()
               if name not in ("original_weak_baseline", "generation_0_fresh_champion")}
    best_name = max(private, key=lambda name: private[name]["score"])
    passing = [name for name, result in grades.items() if result["passed"]]
    assert not passing, "A pass was discovered: review solvability before finalizing UNKNOWN."
    now = datetime.now(timezone.utc).isoformat()
    files = sorted(path for directory in ("participant", "evaluator")
                   for path in (ROOT / directory).rglob("*")
                   if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
    manifest = {"schema_version": 1, "ratchet_generation": 1, "predecessor_generation": 0,
                "predecessor_archive": "generations/generation_0", "frozen_at_utc": now,
                "threshold": 0.95, "static_z_bound_radians_per_site_per_layer": 0.01,
                "scenario_count": 223, "zero_drift_scenarios": 63,
                "classification": "hard_open_candidate", "solvability": "UNKNOWN",
                "fresh_attempt_started": False, "participant_allowlist": ["participant/", "attempts/v_2/"],
                "sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}}
    baseline = grades["original_weak_baseline"]
    fresh = grades["generation_0_fresh_champion"]
    status = {"schema_version": 1, "mode": "C_WITNESS_DESIGN_CONSTRUCTION", "ratchet_generation": 1,
              "builder_phase": "frozen_generation_1_ready_for_main_v2_launch", "launch_ready": True,
              "classification": "hard_open_candidate", "solvability": "UNKNOWN",
              "known_passing_witness": False, "threshold": 0.95,
              "static_z_bound_radians_per_site_per_layer": 0.01,
              "scenario_count": 223, "zero_drift_scenarios": 63, "public_scenarios": 31,
              "baseline_min_fidelity": baseline["score"],
              "generation_0_fresh_champion_current_min_fidelity": fresh["score"],
              "best_tested_private_candidate": best_name,
              "best_tested_private_min_fidelity": private[best_name]["score"],
              "private_0005_witness_passes_current_strength": False,
              "private_witness_passed": False, "physics_audit_passed": True,
              "package_audit_passed": True, "privacy_audit_passed": True,
              "fresh_agent_run_current_generation": False, "empirical_hardness": "untested_at_current_strength",
              "fresh_launch_and_final_status_owner": "main",
              "participant_allowlist": ["participant/", "attempts/v_2/"],
              "participant_task": "participant/TASK.md", "baseline_submission": "participant/baseline",
              "hidden_scenarios": "evaluator/hidden/scenarios.json", "freeze_manifest": "freeze_manifest.json",
              "package_frozen_at_utc": now, "generation_0_archive": "generations/generation_0",
              "original_first_tournament_score": "attempts/v_1_score.json",
              "original_first_tournament_scores_preserved": True,
              "prior_raw_attempts_private": "adversary/generation_1/tournament_0_raw",
              "current_grade_summary": "adversary/generation_1/ratchet_build/grade_summary.json",
              "audit_report": "adversary/generation_1/ratchet_build/audit_report.json",
              "current_candidate_scores": {name: {key: result[key] for key in
                  ("score", "core_score", "worst_family_score", "resource_score", "runtime", "valid", "passed", "reason")}
                  for name, result in grades.items()}}
    table = "\n".join(f"| {name} | {result['score']:.10f} | {result['core_score']:.10f} | {result['worst_family_score']:.10f} | No |"
                      for name, result in grades.items())
    report = f'''# Generation-1 ratchet build report

## Launch-ready open candidate

The authorized current bound is **static Z drift +/-0.01 radians/site/layer**,
with unchanged **minimum fidelity target 0.95**. This is a
**hard_open_candidate; solvability UNKNOWN**. None of seven graded artifacts
passes. The former +/-0.005 witness is NOT a passing witness at this strength.
No fresh agent was launched for this ratchet; main owns v2 launch and status.

The circuit remains a 12-cycle, initially `|+>^12`, with 24 alternating
fixed-ZZ matching layers and bounded two-group RX angles. A static local
RZ interval follows every kick layer, including the last. Group gains remain
+/-2.5%, common ZZ gains +/-1.5%, and edge residuals +/-0.5%.

## Fixed suite and scores

There are **223 scenarios**: the exact original 63 zero-drift cases, 16
nominal structured/local Z cases, 64 coherent joint stress cases, 16 concrete
adversarial joint cases, and 64 held-out local-disorder cases. Core/worst/
held-out counts are 31/104/88. The participant gets 31 public examples.

| Artifact | Overall minimum | Core minimum | Worst-family minimum | Pass |
|---|---:|---:|---:|---|
{table}

The actual new-suite fresh-champion minimum is slightly below the earlier
0.911183 sidecar result because the frozen natural joint-stress family also
includes additional coherent endpoint combinations. Scores are computed
independently by the trusted full-state checker; all norms pass. Runtime
is approximately 10–13 seconds per 223-case grade on this host.

## Independent audits

- 24 full-state comparisons: maximum public/trusted difference
  {audit['max_public_trusted_state_error']:.3e}.
- Independent compiled state-vector/trusted fidelity difference:
  {audit['max_compiled_trusted_fidelity_error']:.3e}.
- 12 dense Kronecker RX/RZ/ZZ gate checks: max error
  {audit['max_dense_gate_error']:.3e}; norm deviation max {audit['max_norm_error']:.3e}.
- Zero-drift evolution matches generation 0 exactly in the audit; all 63
  original scenario coordinates are preserved.
- Nonzero drift produces global-X expectation {audit['nonzero_drift_global_x_expectation']:.6f}
  in a tested case and is correctly accepted. Parity is asserted only for
  the 63 zero-drift cases; norm remains an invariant for all 223 cases.
- 18 malformed/missing/symlink artifacts rejected, including NaN, infinity,
  booleans, strings, invalid dimensions and oversized files; three invalid
  CLI outputs checked for all required result fields.
- The isolated public baseline runner smoke test passes. The original weak
  baseline pulse bytes are unchanged, and no private artifact/code hash
  occurs in participant assets.

## Archive, privacy, freeze

`generations/generation_0/` contains the exact original participant,
evaluator, status, freeze and builder documents. All {len(archive_manifest['files'])}
archived file hashes verify. All {len(score_hashes)} first-tournament score
records retain their original bytes, resolving relocated private paths.
The original champion's {len(champion_manifest['files'])} files are unchanged.

Prior raw attempts and the raw model log are quarantined under
`adversary/generation_1/tournament_0_raw/`; only the independently authored
weak baseline remains public. Do not expose prior fresh/private pulses or
solver source to v2. Main should expose only `participant/` and `attempts/v_2/`.

The current manifest freezes {len(files)} public/trusted files before v2.
Verify with `python adversary/verify_freeze.py`. The hidden scenario digest
is `{audit['scenario_sha256']}`. Candidate scores/audit detail reside in
`adversary/generation_1/ratchet_build/`. No private search diagnosis or
optimized artifact is placed in participant material.
'''
    replace(ROOT / "BUILD_REPORT.md", report)
    replace(ROOT / "freeze_manifest.json", json.dumps(manifest, indent=2) + "\n")
    integrity = {"generation_0_archive_mismatches": archive_mismatches,
                 "first_tournament_score_mismatches": score_mismatches,
                 "original_champion_mismatches": champion_mismatches,
                 "private_artifact_leaks": audit["private_artifact_leaks"], "passed": True}
    replace(HERE / "final_integrity.json", json.dumps(integrity, indent=2) + "\n")
    replace(ROOT / "status.json", json.dumps(status, indent=2) + "\n")
    print(json.dumps({"launch_ready": True, "generation": 1, "solvability": "UNKNOWN",
                      "frozen_files": len(files), "baseline": baseline["score"],
                      "prior_fresh": fresh["score"], "best_private": private[best_name]["score"]}), flush=True)


if __name__ == "__main__":
    main()
