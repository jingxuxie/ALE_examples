import ast
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tokenize

sys.dont_write_bytecode = True

import challenge
import numpy as np
import scipy


HERE = Path(__file__).resolve().parent


def main():
    target = json.loads((HERE / "inputs/target.json").read_text())
    engine = challenge.IndependentEngine(target)
    center = challenge.champion_parameters(target)
    checked_examples = []
    for filename in ("confirmation_full_coefficients_0p001_pass.json", "confirmation_full_coefficients_0p001_parents_ratio.json", "confirmation_full_coefficients_0p001_parents.json"):
        path = HERE / "examples" / filename
        example = json.loads(path.read_text())
        generated = challenge.perturb(center, example["family"], example["radius_eh"], np.array(example["uniform_coordinates"]), target)
        if generated != example["parameters"]:
            raise AssertionError("example parameters do not reproduce")
        report = engine.evaluate(generated, complete=True)
        saved = example["report"]
        difference = max(abs(report["metrics"][field] - saved["metrics"][field]) for field in saved["metrics"])
        if difference > 5e-10 or report["cluster"] != saved["cluster"] or not report["numerical_valid"]:
            raise AssertionError("example verification failed")
        checked_examples.append(dict(example=str(path.relative_to(HERE)), sample_index=example["sample_index"],
                                     cluster=report["cluster"], repeat_error=difference,
                                     max_numerical_error_eh=report["metrics"]["max_numerical_error_eh"]))
    archive_manifest = json.loads((HERE / "archive/manifest.json").read_text())
    archived_files = 0
    with tarfile.open(HERE / "archive/portfolio_evidence.tar.gz", "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            payload = archive.extractfile(member).read()
            expected = archive_manifest["portfolio_report_sha256"] if member.name == "portfolio_report.json" else archive_manifest["portfolio_files"][member.name.removeprefix("portfolio/")]
            if hashlib.sha256(payload).hexdigest() != expected:
                raise AssertionError("archive member mismatch")
            archived_files += 1
    if challenge.digest(HERE / "archive/portfolio_evidence.tar.gz") != archive_manifest["archive_sha256"]:
        raise AssertionError("archive checksum mismatch")
    for source in HERE.glob("*.py"):
        tree = ast.parse(source.read_text())
        if any(isinstance(node, ast.Name) and len(node.id) == 1 for node in ast.walk(tree)):
            raise AssertionError("one-letter identifier")
        with source.open("rb") as stream:
            if any(token.type == tokenize.COMMENT for token in tokenize.tokenize(stream.readline)):
                raise AssertionError("inline or source comments")
    summary = json.loads((HERE / "summary.json").read_text())
    diagnostics = json.loads((HERE / "diagnostics.json").read_text())
    proposal = json.loads((HERE / "target_proposal.json").read_text())
    if "PROPOSAL ONLY" not in proposal["status"] or proposal["proposed_assay"]["radius_eh"] != 0.001:
        raise AssertionError("unexpected target proposal")
    record_count = 0
    for path in (HERE / "results").glob("*.json"):
        result = json.loads(path.read_text())
        if challenge.aggregate(result["cases"]) != result["summary"]:
            raise AssertionError("saved aggregate does not match cases")
        record_count += len(result["cases"])
    if record_count != summary["assay_cases"] or record_count != 6656:
        raise AssertionError("case count mismatch")
    for auxiliary in diagnostics["auxiliary"].values():
        if challenge.aggregate(auxiliary["cases"]) != auxiliary["summary"]:
            raise AssertionError("auxiliary aggregate mismatch")
    archive_champion = challenge.CONCEPT / "champions/generation_2/submission/witness.json"
    if challenge.digest(archive_champion) != challenge.digest(HERE / "inputs/champion_witness.json"):
        raise AssertionError("archived champion differs from challenged artifact")
    report = dict(passed=True, frozen_audit=challenge.frozen_audit(),
                  archived_champion_sha256=challenge.digest(archive_champion), portfolio_archive_members_verified=archived_files,
                  main_cases_verified=record_count, auxiliary_cases_verified=sum(len(entry["cases"]) for entry in diagnostics["auxiliary"].values()),
                  saved_examples=checked_examples, source_style_checks=True,
                  numpy_version=np.__version__, scipy_version=scipy.__version__,
                  generation3_built=False, generation3_frozen=False, proposal_awaits_approval=True,
                  evidence_sha256={filename: challenge.digest(HERE / filename) for filename in
                      ("challenge.py", "diagnose.py", "challenge_spec.json", "summary.json", "diagnostics.json", "target_proposal.json", "REPORT.md")})
    challenge.write_json(HERE / "final_audit.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
