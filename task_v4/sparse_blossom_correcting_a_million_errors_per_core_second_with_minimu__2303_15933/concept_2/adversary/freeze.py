from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def write(relative, data):
    (ROOT / relative).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    known = load("adversary/known_independent_metrics.json")
    baseline = load("adversary/baseline_independent_metrics.json")
    audit = load("adversary/audit_report.json")
    spec = load("participant/input/spec.json")
    assert known["valid"] and known["passed"] and known["core_score"] >= 1
    assert baseline["valid"] and not baseline["passed"]
    assert audit["passed"]
    assert "resources" in known and "resources" in baseline
    public_baseline = load("participant/baseline/metrics.json")
    assert math.isclose(baseline["certified_gap"], public_baseline["certified_gap"], abs_tol=1e-12)
    log = (ROOT / "adversary/discovery.log").read_text()
    completion = re.search(r"DONE seed=(\d+) evaluations=(\d+) restarts=(\d+)", log)
    assert completion
    frozen_at = datetime.now(timezone.utc).isoformat()
    hashes = {}
    for directory in ("participant", "evaluator"):
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_file() and path.name != "frozen_manifest.json":
                assert not path.is_symlink()
                hashes[str(path.relative_to(ROOT))] = digest(path)
    manifest = {"frozen_at_utc": frozen_at, "generation": 1, "fresh_agents_launched_at_freeze": 0,
                "targets": spec["targets"], "scale_interval": spec["scale_interval"],
                "files_sha256": hashes, "known_private_witness_sha256": digest(ROOT / "adversary/known_witness.json"),
                "baseline_provenance": "deterministic formula, no private search output", "threshold_changes_after_launch": "forbidden within generation"}
    write("evaluator/hidden/frozen_manifest.json", manifest)
    metrics_fields = ("core_score", "worst_scale_score", "certified_gap", "certified_opposite_posterior", "certified_syndrome_probability", "reason")
    status = {"concept_id": "concept_2", "concept": "robust_entropy_inversion_of_logical_confidence",
              "paper": "2303.15933", "paper_sections": ["2.1", "2.2", "2.3"], "verification_mode": "B",
              "task_type": "COUNTEREXAMPLE_FALSIFICATION", "generation": 1,
              "status": "frozen_ready_for_independent_main_audit", "solvability": "known_feasible",
              "known_passing_solution": True, "known_solution_is_privileged": True,
              "evaluator_valid": True, "builder_audit_passed": True, "retained": True,
              "fresh_agents_launched": 0, "participant_attempts": 0, "participant_champions": 0,
              "planned_independent_attempts": 2, "planned_model": "ultima-alpha",
              "fresh_agent_wall_seconds": 3600, "fresh_runner_launched_by_builder": False,
              "fresh_difficulty_status": "unmeasured; neither-fresh-agent criterion not established",
              "targets": spec["targets"], "scale_interval": spec["scale_interval"], "continuous_interval_certificate": True,
              "topology": audit["topology"], "frozen_at_utc": frozen_at,
              "manifest": "evaluator/hidden/frozen_manifest.json", "manifest_sha256": digest(ROOT / "evaluator/hidden/frozen_manifest.json"),
              "participant_exposure_allowlist": ["participant/"],
              "known_witness": {"artifact": "adversary/known_witness.json", "report": "adversary/known_independent_metrics.json", **{field: known[field] for field in metrics_fields}},
              "baseline": {"artifact": "participant/baseline/weak.json", "report": "adversary/baseline_independent_metrics.json", "provenance": "deterministic_unoptimized", **{field: baseline[field] for field in metrics_fields}},
              "private_search": {"seed": int(completion[1]), "proposal_evaluations": int(completion[2]), "restarts": int(completion[3]), "requested_wall_seconds": 240, "report": "adversary/SEARCH_REPORT.md"},
              "audit_report": "adversary/audit_report.json", "evaluation_resources": known["resources"],
              "scope": "Only this concept_2 was built; no fresh runner launched."}
    write("status.json", status)
    (ROOT / "adversary/SEARCH_REPORT.md").write_text(
        "# Privileged search and feasibility report\n\n"
        "DO NOT EXPOSE this directory, native code, logs, witness, or report to participants.\n\n"
        "## Research and interpretation\n\n"
        "Primary sources were inspected on August 28, 2026: Sparse Blossom\n"
        "arXiv:2303.15933v2 sections 2.1–2.3; Bravyi–Suchara–Vargo arXiv:1405.4883;\n"
        "Smith–Brown–Bartlett, DOI 10.1038/s42005-024-01883-4; and Lin arXiv:2510.06531.\n"
        "The target falsifies a universal logical-confidence surrogate inference, not\n"
        "Sparse Blossom's matching correctness or any cited paper's theorem.\n\n"
        "## Private calibration\n\n"
        "The fixed 5-column by 4-row graph was selected before search. Independent\n"
        "bounded Bernoulli rates and a spatially spread syndrome were optimized in\n"
        "the native `search.cpp` frontier oracle. It uses 32 frontier states, sums\n"
        "nonnegative probabilities, and minimizes physical costs. Private annealed\n"
        "coordinate/syndrome proposals optimize contrary log odds while penalizing\n"
        "small weight gap, small syndrome mass, and excessive mean rate, initially\n"
        "at scales 0.95, 1, and 1.05. This is a private generation technique, not a\n"
        "participant asset. The final 21-anchor certificate is stricter and is\n"
        "verified separately. No best witness was placed in participant files.\n\n"
        f"Seed {completion[1]}; {int(completion[2]):,} evaluated mutation proposals;\n"
        f"{int(completion[3]):,} restarts. Requested wall budget: 240 seconds, checked\n"
        "between restart batches; exact CPU time was not instrumented. The log ends\n"
        "with a completion record. Native trials are not fresh model attempts.\n\n"
        "## Frozen feasible targets\n\n"
        f"Frozen at {frozen_at}, before any fresh launch. Final targets are gap\n"
        "1.08 nats, opposite posterior 0.85, and syndrome mass 0.0000175 over the\n"
        "whole interval [0.95,1.05]. The generic 2**21-state oracle independently\n"
        "recomputes every anchor; it never imports the frontier checker or witness.\n\n"
        f"Known private core score: {known['core_score']:.15g}. Certified gap:\n"
        f"{known['certified_gap']:.15g}; opposite posterior:\n"
        f"{known['certified_opposite_posterior']:.15g}; syndrome probability:\n"
        f"{known['certified_syndrome_probability']:.15g}. Passed: true.\n\n"
        "This demonstrates actual feasibility, not a conjectured open target. It\n"
        "does not establish optimality or fresh-agent difficulty. Strong entropy\n"
        "inversion survives a continuous 10%-wide global probability-scale range.\n"
        f"The certified effective-multiplicity ratio exceeds {math.exp(known['certified_gap'] + known['certified_opposite_log_odds']):.6g}.\n\n"
        "## Audit and asymmetry\n\n"
        "The audit checks all anchors against the independent oracle for known and\n"
        "baseline artifacts, random graphs' rate vectors on the fixed topology,\n"
        "extended precision, exhaustive small-graph enumeration, mass normalization,\n"
        "logical distance, incidence ranks, 1,001 interior scales, and malformed\n"
        "artifacts. See `audit_report.json`. The public baseline is now a completely\n"
        "deterministic fixture, not the early optimized `discovery_weak.json`; that\n"
        "early hit remains private and is never copied into the final public set.\n\n"
        "Reproduction, from the concept root, with all outputs local:\n\n"
        "```bash\nTMPDIR=\"$PWD/adversary\" g++ -O3 -std=c++17 adversary/search.cpp -o adversary/search\n"
        "./adversary/search 240 230315933 adversary/reproduction > adversary/reproduction.log\n"
        "/usr/bin/python3 -B evaluator/evaluate.py adversary/known_witness.json --output adversary/recheck.json\n"
        "/usr/bin/python3 -B adversary/audit.py\n```\n\n"
        "Do not overwrite or ratchet the frozen contract after launch. Two fully\n"
        "independent one-hour model attempts are planned by the operator, not run.\n")
    (ROOT / "adversary/BASELINE_REPORT.md").write_text(
        "# Deterministic baseline audit\n\n"
        "The public fixture uses p[edge]=0.03+0.08*((17*edge+11)%39)/38 and\n"
        "syndrome [1,6,11,16]. It is not derived from any optimized private artifact.\n"
        "`participant/baseline/make_baseline.py` reconstructs it without a search.\n\n"
        f"Structural validity: true. Passed: false. Core score: {baseline['core_score']:.15g}.\n"
        f"Certified gap: {baseline['certified_gap']:.15g}; opposite posterior:\n"
        f"{baseline['certified_opposite_posterior']:.15g}; syndrome probability:\n"
        f"{baseline['certified_syndrome_probability']:.15g}.\n\n"
        "The full independent result is `baseline_independent_metrics.json`; the\n"
        "public frontier result is `participant/baseline/metrics.json`. The oracle\n"
        "audit compares all 21 anchors. This is a format/calculation starting point,\n"
        "not a warm-start optimizer or a near-target witness.\n")
    print(json.dumps({"frozen_at_utc": frozen_at, "files_hashed": len(hashes), "known_core_score": known["core_score"], "baseline_core_score": baseline["core_score"], "audit_passed": audit["passed"], "fresh_agents_launched": 0}, indent=2))


if __name__ == "__main__":
    main()
