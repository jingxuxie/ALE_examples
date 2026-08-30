import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from assemble import FAMILIES, in_bounds, write_json

HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parents[1]
SEARCH = HERE.parent / "champion_1_search"
sys.path.insert(0, str(HERE / "source_snapshot/champion"))
from contractor import load_mps, measure


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    proposal = json.loads((HERE / "proposal.json").read_text())
    assert set(proposal) == {"cases", "search_summary"}
    assert len(proposal["cases"]) == 8
    assert Counter(case["family"] for case in proposal["cases"]) == Counter({family: 2 for family in FAMILIES})
    assert not proposal["search_summary"]["pending_case_ids"]
    assert not proposal["search_summary"]["invalid_comparisons"]
    provenance = json.loads((HERE / "reference_provenance.json").read_text())
    details = {entry["source_case_id"]: entry for entry in provenance["cases"]}
    measurements = []
    for case in proposal["cases"]:
        assert set(case) == {"family", "request", "reference_state", "reference_energy", "source_case_id"}
        request = case["request"]
        assert in_bounds(request)
        assert not {"budget_seconds", "wall_seconds"}.intersection(request)
        assert request["case_id"] == case["source_case_id"]
        detail_entry = details[case["source_case_id"]]
        detail_path = CONCEPT / detail_entry["file"]
        assert digest(detail_path) == detail_entry["sha256"]
        detail = json.loads(detail_path.read_text())
        original_request = detail["champion_source_result"]["request"]
        assert request == {name: value for name, value in original_request.items()
                           if name not in ("budget_seconds", "wall_seconds")}
        reference_path = CONCEPT / case["reference_state"]
        champion_path = CONCEPT / detail["champion_state"]
        assert reference_path.resolve().is_relative_to(HERE.resolve())
        assert champion_path.resolve().is_relative_to(HERE.resolve())
        assert digest(reference_path) == detail["reference_sha256"]
        assert digest(champion_path) == detail["champion_sha256"]
        reference = measure(load_mps(reference_path, request), request)
        champion = measure(load_mps(champion_path, request), request)
        assert abs(reference["energy"] - case["reference_energy"]) < 5e-11
        gap = champion["energy"] - reference["energy"]
        screen = 1e-7 * request["n_sites"]
        assert gap > screen
        measurements.append({"source_case_id": case["source_case_id"], "family": case["family"],
                             "reference": reference, "champion": champion, "gap": gap,
                             "screen_margin": gap / screen, "reference_bytes": reference_path.stat().st_size,
                             "champion_bytes": champion_path.stat().st_size})
    initial_manifest = json.loads((SEARCH / "ARTIFACT_MANIFEST.json").read_text())
    for relative, entry in initial_manifest["files"].items():
        assert digest(SEARCH / relative) == entry["sha256"], relative
    for name in ("solve.py", "optimizer.py", "mps.py", "contractor.py"):
        assert digest(HERE / "source_snapshot/champion" / name) == digest(SEARCH / "champion" / name)
    manifest = json.loads((HERE / "manifest.json").read_text())
    for relative, entry in manifest.items():
        assert digest(HERE / relative) == entry["sha256"], relative
    report = {"valid": True, "checked_utc": datetime.now(timezone.utc).isoformat(),
              "case_count": 8, "families": dict(Counter(case["family"] for case in proposal["cases"])),
              "all_16_retained_states_remeasured": True, "all_requests_budget_free": True,
              "source_parameters_and_seeds_preserved": True, "initial_20_artifact_manifest_preserved": True,
              "proposal_sha256": digest(HERE / "proposal.json"), "measurements": measurements,
              "official_resource_certificate": False, "full_passing_solution_known": False,
              "remaining_admission": "Main owns cold production baseline 6/40, target gaps, and official resource evaluation"}
    write_json(HERE / "validation.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    verify()
