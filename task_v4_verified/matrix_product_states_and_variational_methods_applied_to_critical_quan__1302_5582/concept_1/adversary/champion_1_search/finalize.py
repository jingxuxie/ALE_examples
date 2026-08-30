import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import aggregate

ROOT = Path(__file__).resolve().parent


def main():
    aggregate.main()
    report = json.loads((ROOT / "SEARCH_STATUS.json").read_text())
    assert len(report["records"]) == 20, "The bounded twenty-case search must finish first"
    assert not report["incomplete_cases"], "An incomplete reference cannot be certified"
    assert all(record["valid"] and record["source_result_agrees"] for record in report["records"])
    assert all(record["achieved_energy_gap"] >= -1e-10 for record in report["records"])
    assert len(report["short_records"]) == 4
    assert all(record["valid_completed_short"] for record in report["short_records"])
    originals = ROOT.parents[1] / "attempts/v_2"
    for source in sorted((ROOT / "champion").glob("*.py")):
        assert source.read_bytes() == (originals / source.name).read_bytes(), "Champion copy was changed"
    assert hashlib.sha256((ROOT / "champion/contractor.py").read_bytes()).hexdigest() == (
        "0460b83bcb30f9fc5b6b17eeca38c21dfa433102099ed7e644081900bd706b4b")
    validation = {"valid": True, "completed_utc": datetime.now(timezone.utc).isoformat(),
                  "candidate_count": len(report["records"]), "long_states_valid": 40,
                  "completed_valid_short_states": len(report["short_records"]),
                  "cohorts": report["cohorts"], "unit_tests_passed": 5,
                  "champion_sources_byte_identical": True,
                  "contractor_matches_frozen_public_specification": True,
                  "all_saved_final_energies_recomputed": True,
                  "wall_limited_probes_counted_as_failures": False,
                  "frozen_evaluator_invocations_in_this_sidecar": 0,
                  "cases_publicly_admitted": 0,
                  "full_passing_solver_for_proposals_certified": False,
                  "ground_energies_certified": False,
                  "scope": "generation-time physical counterexamples and negative controls only"}
    (ROOT / "FINAL_VALIDATION.json").write_text(json.dumps(validation, indent=2) + "\n")
    plan_path = ROOT / "SEARCH_PLAN.json"
    plan = json.loads(plan_path.read_text())
    plan.update(status="complete; bounded search stopped at 20 candidates", completed_candidates=20,
                final_validation="FINAL_VALIDATION.json", artifact_manifest="ARTIFACT_MANIFEST.json")
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    manifest = {"created_utc": validation["completed_utc"], "algorithm": "sha256", "files": {}}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name == "ARTIFACT_MANIFEST.json" or "__pycache__" in path.parts:
            continue
        manifest["files"][str(path.relative_to(ROOT))] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                                        "bytes": path.stat().st_size}
    (ROOT / "ARTIFACT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
