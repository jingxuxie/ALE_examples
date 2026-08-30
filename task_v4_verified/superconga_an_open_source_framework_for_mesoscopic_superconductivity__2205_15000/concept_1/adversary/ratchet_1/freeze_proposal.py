from common import ROOT, CONCEPT, checked_field, energy_gradient, read_case, write_json

from datetime import datetime, timezone
import hashlib
import json

import numpy as np

from analyze import compare_topology, state


def main():
    destination = ROOT / "proposal"
    if (destination / "manifest.json").exists():
        raise RuntimeError("proposal is frozen; refusing overwrite")
    groups = {
        "commensurate_half_flux": ["nf01", "nf02"],
        "disordered_pinned_fluxoid": ["nf03", "nf06"],
        "symmetry_broken_bridges": ["bc03", "nf04"],
    }
    definitions = {
        "commensurate_half_flux": "Regular arrays of 48/49 near-half-flux solenoidal holes with small material disorder and no metal pins; collective fluxoid order/domain defects.",
        "disordered_pinned_fluxoid": "54/72 holes with quenched, noncommensurate solenoidal flux disorder and dense superconductivity-suppressing material patches; coupled pin and hole allocation.",
        "symmetry_broken_bridges": "Narrow connected bridges with broken regular-loop symmetry: spatially inhomogeneous signed bulk field plus solenoids (bc03), or staggered hole geometry (nf04).",
    }
    for directory in ("cases", "baseline_fields", "witness_fields"):
        (destination / directory).mkdir(exist_ok=True)
    target = read_case(CONCEPT / "evaluator/hidden/target.json")
    target["families"] = list(groups)
    target["frozen_at"] = datetime.now(timezone.utc).isoformat()
    target["freeze_stage"] = "private ratchet proposal before any generation-2 fresh launch; requires Main approval"
    target["baseline_contract"] = "Exact provided initial field, attained by the unchanged generation-1 champion; baseline field is public in the case, lower witness stays private."
    target["family_definitions"] = definitions
    records = []
    hashes = {}
    for family, names in groups.items():
        for name in names:
            source_path = ROOT / "cases" / (name + ".json")
            case = read_case(source_path)
            baselines = [value for label in ("champion_cold", "champion_warm") if (value := state(case, label, name)) is not None]
            if len(baselines) != 2:
                raise RuntimeError("cold and warm champion validation required")
            baseline = min(baselines, key=lambda value: value["energy"])
            witnesses = [value for label in ("combined_210", "loop_joint_150") if (value := state(case, label, name)) is not None]
            witness = min(witnesses, key=lambda value: value["energy"])
            gap = baseline["energy"] - witness["energy"]
            topology = compare_topology(case, baseline["field"], witness["field"])
            if gap < 0.5 or not topology["meaningful_topology_change"]:
                raise RuntimeError("not an eligible physical counterexample: " + name)
            case["initial_real"] = baseline["field"].real.tolist()
            case["initial_imag"] = baseline["field"].imag.tolist()
            case_path = destination / "cases" / (name + ".json")
            case_path.write_text(json.dumps(case, separators=(",", ":")) + "\n")
            baseline_path = destination / "baseline_fields" / (name + ".npz")
            witness_path = destination / "witness_fields" / (name + ".npz")
            np.savez_compressed(baseline_path, psi=baseline["field"])
            np.savez_compressed(witness_path, psi=witness["field"])
            record = {"case_id": name, "family": family, "case_path": str(case_path.relative_to(ROOT)), "baseline_path": str(baseline_path.relative_to(ROOT)), "witness_path": str(witness_path.relative_to(ROOT)), "baseline_energy": baseline["energy"], "witness_energy": witness["energy"], "gap": gap, "baseline_gradient_rms": baseline["gradient_rms"], "witness_gradient_rms": witness["gradient_rms"], "baseline_source": baseline["field_path"], "witness_source": witness["field_path"], "topology": topology}
            records.append(record)
            for path in (case_path, baseline_path, witness_path):
                hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(destination / "target.json", target)
    hashes["proposal/target.json"] = hashlib.sha256((destination / "target.json").read_bytes()).hexdigest()
    baseline_hash = hashlib.sha256((ROOT / "baseline/solve.py").read_bytes()).hexdigest()
    original_hash = hashlib.sha256((CONCEPT / "champions/generation_1/solve.py").read_bytes()).hexdigest()
    if baseline_hash != original_hash:
        raise RuntimeError("champion copy changed")
    manifest = {"schema_version": 1, "status": "frozen_private_proposal_pending_main_approval", "frozen_at": target["frozen_at"], "champion_sha256": baseline_hash, "reference_kind": "attained feasible upper bounds, not true ground states", "source_cases_searched": 24, "fresh_sessions_launched": 0, "case_count": 6, "family_definitions": definitions, "family_revision_reason": "The initial broad families were largely robust under warm replay. Proposal families isolate the actual collective-loop, quenched-pin, and bridge-symmetry failure mechanisms; this refinement precedes any generation-2 fresh launch.", "baseline_repeatability": "Provided initial state exactly encodes B; returning it is valid with zero improvement independent of stochastic search timing.", "cases": records, "sha256": hashes}
    write_json(destination / "manifest.json", manifest)
    print({"status": manifest["status"], "case_count": 6, "minimum_gap": min(record["gap"] for record in records)})


if __name__ == "__main__":
    main()
