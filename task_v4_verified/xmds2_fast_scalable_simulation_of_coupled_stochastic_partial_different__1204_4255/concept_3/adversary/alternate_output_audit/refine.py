import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit import ROOT, TRUSTED, digest, dump, fc, rank_key


def verified_source(candidate):
    for source in candidate["sources"]:
        run_path = ROOT / "attempts" / (source["attempt"] + ".run.json")
        record = fc.read_json(run_path, 4 * 1024 * 1024)
        if record.get("status") in (None, "running"):
            raise RuntimeError("Attempt not completed")
        path = ROOT / source["path"]
        relative = str(path.relative_to(ROOT / "attempts" / source["attempt"]))
        expected = record["submission_sha256"][relative]
        assert expected == source["sha256"] == digest(path)
    copy = HERE / candidate["copy"]
    assert digest(copy) == candidate["sources"][0]["sha256"]
    artifact = fc.read_json(copy)
    canonical = hashlib.sha256(json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    assert canonical == candidate["canonical_sha256"]
    return artifact


def reference_inputs():
    protocol = fc.read_json(TRUSTED / "protocol.json")
    cases = fc.read_json(TRUSTED / "cases.json")
    policy = protocol["audit"]
    references = {}
    hashes = {}
    for shape in (tuple(policy["spatial_grid"]), tuple(policy["refined_grid"])):
        path = TRUSTED / "references" / (fc.reference_key(cases, shape) + ".npz")
        if not path.is_file():
            raise RuntimeError("Official reference cache absent; refusing any root cache write")
        with np.load(path, allow_pickle=False) as data:
            references[shape] = data["initial"].copy(), data["target"].copy(), float(data["residual"])
        hashes[str(path.relative_to(ROOT))] = digest(path)
    return protocol, cases, references, hashes


def wait_for_screen():
    while True:
        path = HERE / "screening.json"
        try:
            report = fc.read_json(path, 8 * 1024 * 1024)
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(5)
            continue
        if report["status"] == "complete":
            return report
        time.sleep(5)


def official_top(report, candidate_id=None):
    protocol, cases, references, reference_hashes = reference_inputs()
    alternatives = [row for row in report["ranking"] if not row["is_canonical_submission"]]
    alternatives.sort(key=rank_key, reverse=True)
    plausible = [row for row in alternatives if row["core_score"] >= 0.989 and row["worst_family_score"] >= 0.984 and row["worst_case_score"] >= 0.979]
    clean = [row for row in alternatives if row["maximum_diagnostics"]["boundary_mass"] <= protocol["audit"]["max_boundary_mass"] and row["maximum_diagnostics"]["norm_error"] <= protocol["audit"]["max_norm_error"]]
    strongest = (clean or alternatives)[:1]
    chosen = {row["id"]: row for row in plausible + strongest}
    selection = {"created_utc": datetime.now(timezone.utc).isoformat(), "policy": "Fully grade every surrogate within 0.001 of every target, plus the strongest noncanonical minimum-threshold-margin candidate with clean coarse boundary/norm diagnostics. All 20 alternatives separately receive A/B/C weakest-case refinement; coarse diagnostic violations are not themselves accepted as exclusion proof.", "plausible_count": len(plausible), "clean_screen_count": len(clean), "strongest_nominal": alternatives[0]["id"], "selected": list(chosen), "reference_sha256": reference_hashes, "screening_sha256": digest(HERE / "screening.json"), "source_evaluator_sha256": digest(ROOT / "evaluator/evaluate.py"), "new_optimization": False, "artifact_postprocessing": False}
    selection_name = "official/selection.json"
    if candidate_id is not None:
        chosen = {row["id"]: row for row in alternatives if row["id"] == candidate_id}
        if len(chosen) != 1:
            raise ValueError("Requested candidate is not an eligible distinct original alternative")
        selection["policy"] = "Supplemental exact full-37-case official grade of a recorded eligible original chosen from the completed all-case screen; no coarse numerical violation is treated as official proof. The explicit candidate and its original hashes are retained."
        selection["selected"] = list(chosen)
        selection_name = "official/selection__" + Path(candidate_id).stem + ".json"
    dump(selection_name, selection)
    for candidate in chosen.values():
        verified_source(candidate)
        identity = Path(candidate["id"]).stem
        output = HERE / "official" / (identity + ".evaluation.json")
        log = HERE / "official" / (identity + ".evaluation.log")
        command = ["/usr/bin/python3", "-I", "-B", str(ROOT / "evaluator/evaluate.py"), "--artifact", str(HERE / candidate["copy"]), "--output", str(output)]
        provenance = {"source": candidate["sources"], "artifact_canonical_sha256": candidate["canonical_sha256"], "artifact_bytes_unchanged": True, "original_fresh_output": True, "assessment_role": "privileged_fairness_audit", "command": command, "started_utc": datetime.now(timezone.utc).isoformat(), "reference_sha256": reference_hashes}
        dump("official/" + identity + ".provenance.json", provenance)
        print("OFFICIAL_START", identity, flush=True)
        started = time.perf_counter()
        with log.open("w") as stream:
            process = subprocess.run(command, cwd=HERE, stdout=stream, stderr=subprocess.STDOUT, timeout=1500)
        result = fc.read_json(output, 4 * 1024 * 1024)
        assert result["artifact_canonical_sha256"] == candidate["canonical_sha256"]
        verified_source(candidate)
        for name, expected in report["inputs"]["protected_sha256"].items():
            assert digest(ROOT / name) == expected
        for name, expected in reference_hashes.items():
            assert digest(ROOT / name) == expected
        provenance.update({"finished_utc": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.perf_counter() - started, "returncode": process.returncode, "evaluation_sha256": digest(output), "protected_inputs_unchanged": True, "valid": result["valid"], "passed": result["passed"], "reason": result["reason"]})
        dump("official/" + identity + ".provenance.json", provenance)
        print("OFFICIAL_RESULT", identity, json.dumps({key: result[key] for key in ("valid", "passed", "reason", "core_score", "worst_family_score", "worst_case_score", "runtime_seconds")}), flush=True)
        if result["passed"]:
            dump("ORIGINAL_PASS.json", {"original_sources": candidate["sources"], "evaluation": str(output.relative_to(HERE)), "evaluation_sha256": digest(output), "scores": {key: result[key] for key in ("core_score", "worst_family_score", "worst_case_score")}, "original_fresh_output": True, "artifact_postprocessing": False})
            print("ORIGINAL_PRE_CUTOFF_PASS", candidate["sources"], flush=True)
            return


def failure_checks(report):
    started = time.perf_counter()
    protocol, cases, references, reference_hashes = reference_inputs()
    policy = protocol["audit"]
    coarse_shape = tuple(policy["spatial_grid"])
    fine_shape = tuple(policy["refined_grid"])
    case_indices = {case["id"]: index for index, case in enumerate(cases)}
    rows = []
    alternatives = [row for row in report["ranking"] if not row["is_canonical_submission"]]
    for candidate in alternatives:
        artifact = verified_source(candidate)
        splines, certificate = fc.validate_artifact(artifact, protocol)
        selected = min(candidate["cases"], key=lambda row: row["fidelity"])
        index = case_indices[selected["id"]]
        case = cases[index]
        initial_coarse, target_coarse, residual_coarse = references[coarse_shape]
        initial_fine, target_fine, residual_fine = references[fine_shape]
        spatial, diagnostic_spatial = fc.evolve(splines, [case], coarse_shape, policy["dt"], initial_coarse[index:index + 1])
        temporal, diagnostic_temporal = fc.evolve(splines, [case], fine_shape, policy["dt"], initial_fine[index:index + 1])
        refined, diagnostic_refined = fc.evolve(splines, [case], fine_shape, policy["refined_dt"], initial_fine[index:index + 1])
        score_spatial = float(fc.fidelities(spatial, target_coarse[index:index + 1], coarse_shape)[0])
        score_temporal = float(fc.fidelities(temporal, target_fine[index:index + 1], fine_shape)[0])
        score_refined = float(fc.fidelities(refined, target_fine[index:index + 1], fine_shape)[0])
        allowance = 2.0 * (abs(score_spatial - score_temporal) + abs(score_temporal - score_refined)) + policy["fidelity_allowance"]
        diagnostic_max = {name: float(max(diagnostic_spatial[name][0], diagnostic_temporal[name][0], diagnostic_refined[name][0])) for name in diagnostic_refined}
        distance_time = float(fc.state_distance(temporal, refined, fine_shape)[0])
        distance_space = float(fc.state_distance(fc.prolong(spatial, fine_shape), temporal, fine_shape)[0])
        audits = {"max_allowance": allowance, "max_state_distance": max(distance_time, distance_space), "max_norm_error": diagnostic_max["norm_error"], "max_boundary_mass": diagnostic_max["boundary_mass"], "max_spectral_tail": diagnostic_max["spectral_tail"], "max_reference_residual": max(residual_coarse, residual_fine)}
        assert all(np.isfinite(value) for value in audits.values())
        failed_audits = [name for name, value in audits.items() if value > policy[name]]
        lower = max(0.0, score_refined - allowance)
        upper = min(1.0, score_refined + allowance)
        row = {"id": candidate["id"], "sources": candidate["sources"], "canonical_sha256": candidate["canonical_sha256"], "case": case, "selection": "lowest full-37-case surrogate fidelity; no case or coefficient creation", "spatial_fidelity": score_spatial, "temporal_fidelity": score_temporal, "refined_fidelity": score_refined, "audited_fidelity": lower, "empirical_upper_check": upper, "audits": audits, "failed_audits": failed_audits, "certified_case_audits_pass": not failed_audits, "frozen_worst_case_threshold_failed": lower < protocol["thresholds"]["worst_case_score"], "refined_fidelity_failure_with_allowance_margin": not failed_audits and upper < protocol["thresholds"]["worst_case_score"], "scope": "single necessary case only; not a full official aggregate score"}
        rows.append(row)
        dump("failure_checks/" + candidate["id"], row)
        summary = {"status": "running", "count": len(rows), "total": len(alternatives), "reference_sha256": reference_hashes, "elapsed_seconds": time.perf_counter() - started, "results": rows}
        dump("failure_checks.json", summary)
        print("CASE_CHECK", candidate["id"], case["id"], lower, upper, failed_audits, flush=True)
    summary["status"] = "complete"
    summary["all_alternatives_have_refined_failure"] = all(row["frozen_worst_case_threshold_failed"] or row["failed_audits"] for row in rows)
    for name, expected in report["inputs"]["protected_sha256"].items():
        assert digest(ROOT / name) == expected
    dump("failure_checks.json", summary)
    print("FAILURE_CHECKS_COMPLETE", summary["count"], summary["elapsed_seconds"], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("official-top", "failure-checks"), required=True)
    parser.add_argument("--candidate")
    arguments = parser.parse_args()
    report = wait_for_screen()
    if arguments.mode == "official-top":
        official_top(report, arguments.candidate)
    else:
        failure_checks(report)


if __name__ == "__main__":
    main()
