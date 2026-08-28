import datetime
import hashlib
import json
from pathlib import Path
import re

from run_fresh import digest_tree

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def verify_files(base, hashes):
    mismatches = [name for name, digest in hashes.items()
                  if hashlib.sha256((base / name).read_bytes()).hexdigest() != digest]
    if mismatches:
        raise RuntimeError("frozen artifacts changed: " + str(base) + " " + repr(mismatches))
    return {"base": str(base.relative_to(ROOT)), "files_verified": len(hashes), "mismatches": []}


def main():
    summary = read(ROOT / "tournament_summary.json")
    assert summary["concepts_built"] == 4 and len(summary["runs"]) == 5
    run_audits = []
    for run in summary["runs"]:
        metadata = read(ROOT / run["metadata"])
        assert metadata["exit_code"] == 0 and not metadata["timed_out"]
        assert metadata["elapsed_seconds"] < metadata["time_limit_seconds"] <= 3600
        assert metadata["participant_unchanged"]
        assert digest_tree(Path(metadata["participant"])) == metadata["participant_sha256_before"]
        source_hashes = {name: digest for name, digest in metadata["submission_sha256"].items()
                         if Path(name).suffix in (".py", ".cpp", ".cc", ".c", ".h", ".hpp", ".sh")}
        changed = [name for name, digest in source_hashes.items()
                   if hashlib.sha256((Path(metadata["attempt"]) / name).read_bytes()).hexdigest() != digest]
        assert not changed, changed
        mission = (Path(metadata["participant"]) / "TASK.md").read_text().lower()
        assert not re.search(r"arxiv|2001[.]00024|reliability of lattice gauge theories", mission)
        assert run["evaluations"]
        assert all(value["mean_core"] >= 0.90 and value["worst_family"] >= 0.90
                   for value in run["evaluations"].values())
        run_audits.append({"concept": run["concept"], "stage": run["stage"],
                           "participant_unchanged": True, "submission_source_files_verified": len(source_hashes),
                           "normal_exit_within_hour": True})
    freezes = []
    for concept, relative, key in (("c01_correlated_tomography", "private/reference/FROZEN.json", "files"),
                                   ("c02_multiscale_protection", "private/FROZEN.json", "hashes"),
                                   ("c04_colored_noise", "private/freeze.json", "hashes")):
        base = ROOT / "pilots" / concept
        freezes.append(verify_files(base, read(base / relative)[key]))
    ratchet = ROOT / "pilots/c04_colored_noise/ratchet1"
    freezes.append(verify_files(ratchet, read(ratchet / "private/freeze.json")["hashes"]))
    compiler = ROOT / "pilots/c03_resonance_compiler"
    compiler_hashes = {}
    for entries in read(compiler / "private/manifest.json")["splits"].values():
        for entry in entries:
            for key, value in entry.items():
                digest_key = key.removesuffix("_path") + "_file_sha256"
                if key.endswith("_path") and digest_key in entry:
                    compiler_hashes[value] = entry[digest_key]
    assert len(compiler_hashes) == 81
    freezes.append(verify_files(compiler, compiler_hashes))
    probes = []
    probe_root = ROOT / "authoring/c02_weakspin_probe"
    for path in sorted((probe_root / "references").glob("*/convergence_coarse_fine.json")):
        record = read(path)
        assert not record["accepted"] and not record["physical_checks"]
        assert record["normalized_convergence_score"] < 0.97
        probes.append({"id": record["id"], "reference_valid": False,
                       "convergence_diagnostic": record["normalized_convergence_score"],
                       "participant_score": None, "artifact": str(path.relative_to(ROOT))})
    assert len(probes) == 2
    physical = read(ROOT / "pilots/c02_multiscale_protection/private/reference/all_initial_physical_checks.json")
    assert physical["all_physical_checks_pass"] and len(physical["cases"]) == 21
    audit = {"created_at": datetime.datetime.now().astimezone().isoformat(),
             "runs": run_audits, "frozen_artifacts": freezes,
             "initial_many_body_physical_checks": True, "invalid_transfer_probes_not_scored": probes}
    (ROOT / "integrity_audit.json").write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")
    selection = {"status": "rejected", "accepted_concept": None, "production_release_created": False,
                 "reason": "All validated fresh tasks are robustly solved. The valid late-time counterexample is solved in fresh confirmation; harder transfer probes lack validated private references.",
                 "acceptance_gates": {"reference_mean_core_above": 0.90,
                                      "fresh_confirmation_mean_core_below": 0.70,
                                      "substantive_unsolved_component_required": True,
                                      "worst_family_review_required": True},
                 "concepts_built": 4, "fresh_attempts": 5, "model": "ultima-alpha",
                 "ratchets_built": {"c04_colored_noise": 1},
                 "runs": summary["runs"], "invalid_transfer_probes": probes,
                 "evidence": ["REPORT.md", "authoring/CANDIDATES.md", "tournament_summary.json",
                              "integrity_audit.json", "authoring/c01_pilot_audit.md",
                              "authoring/c02_pilot_audit.md", "authoring/c03_pilot_audit.md",
                              "authoring/c04_ratchet1_pilot_audit.md"],
                 "scope": "Rejection of the four tested concepts, not a claim about every possible task derived from this paper."}
    (ROOT / "selection.json").write_text(json.dumps(selection, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": selection["status"], "fresh_attempts": 5,
                      "frozen_files_verified": sum(item["files_verified"] for item in freezes),
                      "all_public_and_submission_source_hashes_match": True}), flush=True)


if __name__ == "__main__":
    main()
