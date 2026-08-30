import argparse
import datetime
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    manifest = load("freeze.json")
    mismatches = []
    for relative, expected in manifest["sha256"].items():
        path = ROOT / relative
        if not path.is_file() or digest(path) != expected:
            mismatches.append(relative)
    actual = {str(path.relative_to(ROOT)) for directory in ("participant", "evaluator")
              for path in (ROOT / directory).rglob("*")
              if path.is_file() and "__pycache__" not in path.parts}
    if actual != set(manifest["sha256"]):
        mismatches.append("primary_file_set_changed")
    if mismatches:
        raise RuntimeError("frozen files changed: " + ", ".join(mismatches))
    print(json.dumps({"frozen": True, "verified_files": len(actual), "freeze_sha256": digest(ROOT / "freeze.json")}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.check:
        verify()
        return
    if (ROOT / "freeze.json").exists():
        raise RuntimeError("already frozen; use --check, never overwrite a live task")
    protocol = load("participant/input/protocol.json")
    expected = {"core": 0.060, "worst_family": 0.050, "base": 0.055,
                "member_floor": 0.025, "members_required": 6}
    assert protocol["targets"] == expected
    assert len(protocol["families"]) == 4 and all(len(family["offsets"]) == 8 for family in protocol["families"])
    validation = load("adversary/validation.json")
    assert validation["passed"] and validation["malformed_control_count"] == 40
    assert validation["isolated_runner_with_hostile_pythonpath"]
    champion = load("adversary/champions/evaluation.json")
    assert champion["valid"] and champion["pass"]
    holdout = load("adversary/champions/holdout.json")
    selection = load("adversary/champions/selection.json")
    finalists = [json.loads(line) for line in (ROOT / "adversary" / "final_protocol_candidates.jsonl").read_text().splitlines()]
    baseline_paths = sorted((ROOT / "adversary").glob("baseline*.search.json"))
    baselines = [json.loads(path.read_text()) for path in baseline_paths]
    assert len(baselines) >= 3 and all(record["valid"] and not record["pass"] for record in baselines)
    assert not list((ROOT / "attempts").glob("*.json*"))
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifests = {}
    for directory in ("participant", "evaluator"):
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                manifests[str(path.relative_to(ROOT))] = digest(path)
    evidence = {"paper": "Arijeet Pal and David A. Huse, The many-body localization phase transition",
                "identifier": "arXiv:1010.1992v1", "date": "2010-10-11", "sections": ["II", "III"],
                "seeded_components": ["periodic spin-half Heisenberg Hamiltonian", "zero total Sz sector",
                                      "middle rank one-third", "adjacent-gap ratio"],
                "proxy_claim_is_task_authored": True, "original_paper_proxy_claim": False,
                "shared_physics_sha256": validation["root_physics_sha256"]}
    (ROOT / "adversary" / "source_provenance.json").write_text(json.dumps(evidence, indent=2) + "\n")
    family_rows = "\n".join(f"| {family['family']} | {family['mean']:.12f} | {family['above_member_floor']}/8 |"
                            for family in champion["families"])
    baseline_rows = "\n".join(f"| {baseline['seed']} | {baseline['core']:.12f} | {baseline['worst_family']:.12f} | {baseline['pass']} |"
                              for baseline in baselines)
    report = f"""# Private author calibration report

The frozen task uses three 128-level center windows at energy densities
0.49, 0.50, and 0.51, versus the exact middle rank third. Every reference
contains 306 ratios and every proxy window contains 126. Overlapping
windows are deliberately not advertised as independent samples.

## Feasibility

The author champion is refine index {selection['index']}, selected using
the public 32-probe protocol only. Its signed base discrepancy is
{champion['base']['signed_difference']:.12f}; core is {champion['core']:.12f};
worst-family mean is {champion['worst_family']:.12f}. All fixed thresholds
pass. The constraints give base signed-dihedral distance
{champion['constraints']['symmetry_distance']:.12f} and minimum complete-spectrum
gap across the base and public probes
{min([champion['base']['minimum_gap']] + [row['minimum_gap'] for row in champion['members']]):.12g}.
This is neither a symmetry-sector mixture nor an eigensolver-degeneracy trick.

| Family | Signed mean difference | Members above 0.025 |
|---|---:|---:|
{family_rows}

The profile comes from the noisy two-domain structured search, not from
an analytic formula for a passing output. This is evidence of finite-size
energy dependence in the chosen statistics. Weakly coupled domain sectors
are a possible interpretation, not a proven microscopic explanation or a
thermodynamic mobility-edge claim. The certificate is the measured spectral
discrepancy under the fully specified Hamiltonian.

## Search provenance and difficulty limits

There were 800 pilot profiles and 6,000 refinement profiles. Preliminary
robustness checks covered 46 and 166 shortlisted profiles, respectively.
Broad central-energy-density-window candidates were not retained: their
preliminary robust discrepancies were too small. Of 32 deliberately
selected final-protocol candidates, {sum(result.get('report', {{}}).get('pass', False) for result in finalists)}
passed and {sum('error' in result for result in finalists)} failed admissibility.
These selected-candidate counts are not an independent solver success rate.

The supplied unstructured baseline was run with three fixed seeds. It
screened 128 profiles and exactly evaluated eight finalists per seed.

| Seed | Core | Worst family | Pass |
|---|---:|---:|---|
{baseline_rows}

The target is demonstrably attainable and not reached by those simple
baselines. Fresh LLM difficulty remains unmeasured. No fresh agents were
launched here, and no concept_1 or concept_2 data were read. All private
records are in adversary/, not in attempts/ or participant/.

## Separate diagnostic holdout

After champion selection, a disjoint SHA namespace supplied 32 new members
per family, 128 perturbations in total. Holdout core is
{holdout['core']:.12f}; worst-family mean is {holdout['worst_family']:.12f}.
All four holdout family means exceed the claim's 0.05 bound, but the
holdout core is below the stricter 0.060 primary certificate target.
This is a diagnostic generalization check, not another grading target,
not used to select this champion, and not a claim of a passing holdout
certificate. The primary public protocol and thresholds remain unchanged.

## Numerical and static-input audits

The trusted evaluator reproduces the champion in
{champion['resource']['wall_seconds']:.3f} seconds with 33 full spectra,
one worker, one BLAS thread, and peak RSS
{champion['resource']['peak_rss_mib']:.3f} MiB. A repeated isolated run gives
identical numerical outputs. The alternative evd driver differs in core by
{validation['evr_evd_core_error']:.3g} and in any member discrepancy by at most
{validation['evr_evd_max_member_error']:.3g}. The independent shared root
Hamiltonian and reference-r comparison have zero discrepancy. The root
physics file is read only and no eigenvectors are required.

Forty malformed/static controls are rejected before any diagonalization.
Opposite orientation is valid but fails. Hostile solve.py, exact.py,
json.py, sitecustomize.py, protocol.json, and PYTHONPATH sidecars do not
affect isolated evaluation. Uniform-ladder tests verify rank boundaries,
tie-breaking, all 126/306 ratio counts, and clipping. Physical shifts,
reflection, and global field inversion preserve the full spectrum within
{max(validation['physical_spectrum_symmetry_errors']):.3g}.

NumPy {validation['numpy']}, SciPy {validation['scipy']}. Full records and
resource reports are retained in validation.json and champions/.
"""
    (ROOT / "adversary" / "REPORT.md").write_text(report)
    freeze = {"schema_version": 1, "claim_id": "C3-v1", "task_id": protocol["task_id"],
              "frozen_at_utc": timestamp, "primary_targets": expected,
              "protocol_sha256": digest(ROOT / "participant" / "input" / "protocol.json"),
              "sha256": manifests}
    (ROOT / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    status = {"schema_version": 1, "concept": "concept_3", "mode": "B",
              "task_type": "COUNTEREXAMPLE/FALSIFICATION", "status": "frozen_ready_for_independent_attempts",
              "valid_package": True, "frozen": True, "frozen_at_utc": timestamp,
              "claim_id": "C3-v1", "claim_is_original_paper_claim": False,
              "proxy": {"type": "three_energy_center_gap_windows", "energy_density_targets": [0.49, 0.50, 0.51],
                        "window_levels": 128, "reference_rank_slice": [308, 616], "length": 12, "dimension": 924},
              "primary_targets": expected, "families": 4, "members_per_family": 8,
              "freeze_manifest": "freeze.json", "freeze_sha256": digest(ROOT / "freeze.json"),
              "participant_root": "participant", "evaluator_command": "python -I -B evaluator/evaluate.py WITNESS_JSON --output REPORT_JSON",
              "resource": {"evaluator_wall_seconds": 180, "evaluator_address_space_gib": 2,
                           "evaluator_workers": 1, "blas_threads": 1, "max_generator_workers": 8,
                           "participant_allowlist_seconds": 3600},
              "author_champion": {"witness": "adversary/champions/witness.json",
                                  "evaluation": "adversary/champions/evaluation.json",
                                  "core": champion["core"], "worst_family": champion["worst_family"],
                                  "base": champion["base"]["signed_difference"], "valid": True, "pass": True},
              "baselines": baselines, "validation": {"report": "adversary/validation.json", "passed": True,
                                                     "malformed_controls": 40, "repeat_exact": True,
                                                     "isolated_runner": True, "root_hamiltonian_max_error": 0.0,
                                                     "evr_evd_max_member_error": validation["evr_evd_max_member_error"]},
              "diagnostic_holdout": {"core": holdout["core"], "worst_family": holdout["worst_family"],
                                     "perturbations": 128, "used_for_grading": False, "used_for_selection": False,
                                     "meets_primary_core_threshold": holdout["core"] >= expected["core"]},
              "private_records": "adversary", "fresh_agents_launched": 0,
              "fresh_agent_difficulty": "not_yet_measured", "intended_main_model": "ultima-alpha",
              "other_concepts_accessed": False, "writes_restricted_to_concept_3": True}
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    verify()
    print(json.dumps({"status": status["status"], "primary_targets": expected,
                      "champion": status["author_champion"], "baseline_passes": sum(record["pass"] for record in baselines)}, indent=2))


if __name__ == "__main__":
    main()
