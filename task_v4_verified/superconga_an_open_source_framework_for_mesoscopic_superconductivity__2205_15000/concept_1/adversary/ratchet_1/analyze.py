from common import ROOT, CONCEPT, checked_field, energy_gradient, read_case, write_json

import argparse
from datetime import datetime, timezone
import hashlib
import sys

import numpy as np

sys.path.insert(0, str(ROOT / "challenger"))
import engine
from solve import loop_data


def state(case, label, name):
    directory = ROOT / "runs" / label / name
    if not (directory / "record.json").exists():
        return None
    record = read_case(directory / "record.json")
    if not record["valid"]:
        return None
    field = checked_field(directory / "field.npz", case)
    energy, unused, rms = energy_gradient(case, field)
    if rms > 0.002:
        return None
    return {"energy": energy, "gradient_rms": rms, "field": field, "label": label, "field_path": str((directory / "field.npz").relative_to(ROOT)), "wall_seconds": record["wall_seconds"]}


def compare_topology(case, first, second):
    model = engine.Model(case)
    topology = engine.Topology(model)
    first_loops = loop_data(model, topology, first[model.mask])
    second_loops = loop_data(model, topology, second[model.mask])
    changes = []
    for index, (source, target) in enumerate(zip(first_loops, second_loops)):
        if source["valid"] and target["valid"] and source["winding"] != target["winding"]:
            changes.append({"hole_index": index, "center": [float(topology.holes[index].real), float(topology.holes[index].imag)], "baseline_winding": source["winding"], "witness_winding": target["winding"], "applied_contour_flux_quanta": source["flux"], "baseline_contour_minimum_amplitude": source["minimum_contour_amplitude"], "witness_contour_minimum_amplitude": target["minimum_contour_amplitude"]})
    first_positions, first_charges = topology.vortices(first[model.mask])
    second_positions, second_charges = topology.vortices(second[model.mask])
    first_map = {(float(position.real), float(position.imag)): int(charge) for position, charge in zip(first_positions, first_charges)}
    second_map = {(float(position.real), float(position.imag)): int(charge) for position, charge in zip(second_positions, second_charges)}
    changed = sum(first_map.get(position, 0) != second_map.get(position, 0) for position in first_map.keys() | second_map.keys())
    return {"changed_hole_windings": changes, "reliable_hole_contours": sum(source["valid"] and target["valid"] for source, target in zip(first_loops, second_loops)), "baseline_bulk_vortices": int(np.sum(np.maximum(first_charges, 0))), "witness_bulk_vortices": int(np.sum(np.maximum(second_charges, 0))), "baseline_bulk_antivortices": int(np.sum(np.maximum(-first_charges, 0))), "witness_bulk_antivortices": int(np.sum(np.maximum(-second_charges, 0))), "changed_vortex_plaquettes": changed, "meaningful_topology_change": bool(changes or changed >= 2), "baseline_hole_windings": first_loops, "witness_hole_windings": second_loops}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--partial", action="store_true")
    args = parser.parse_args()
    records = []
    witness_labels = ["combined_210", "loop_joint_150"]
    baseline_labels = ["champion_cold", "champion_warm", "champion_warm_second"]
    for metadata in read_case(ROOT / "broad_index.json"):
        name = metadata["case_id"]
        case = read_case(ROOT / "cases" / (name + ".json"))
        baselines = [value for label in baseline_labels if (value := state(case, label, name)) is not None]
        witnesses = [value for label in witness_labels if (value := state(case, label, name)) is not None]
        if not baselines:
            continue
        baseline = min(baselines, key=lambda value: value["energy"])
        cold = next(value for value in baselines if value["label"] == "champion_cold")
        witness = min(baselines + witnesses, key=lambda value: value["energy"])
        gap = baseline["energy"] - witness["energy"]
        record = {"case_id": name, "family": metadata["family"], "shape": metadata["shape"], "active_sites": metadata["active_sites"], "holes": metadata["actual_holes"], "cold_champion_energy": cold["energy"], "baseline_energy": baseline["energy"], "baseline_source": baseline["field_path"], "baseline_gradient_rms": baseline["gradient_rms"], "witness_energy": witness["energy"], "witness_source": witness["field_path"], "witness_gradient_rms": witness["gradient_rms"], "cold_gap": cold["energy"] - witness["energy"], "persistent_gap": gap, "warm_replay_available": any(value["label"] != "champion_cold" for value in baselines), "witness_search_available": bool(witnesses), "absolute_gap_eligible": gap >= 0.5}
        if gap >= 0.49:
            record["topology"] = compare_topology(case, baseline["field"], witness["field"])
        record["meaningful_counterexample"] = gap >= 0.5 and record.get("topology", {}).get("meaningful_topology_change", False)
        if witnesses:
            history_path = ROOT / "runs" / witness["label"] / name / "history.json"
            if history_path.exists():
                history = read_case(history_path)
                accepted = [item for item in history if item.get("improvement", 0) > 1e-5]
                record["accepted_targeted_moves"] = [{key: value for key, value in item.items() if key in ("kind", "improvement", "energy", "move", "changed_holes", "elapsed")} for item in accepted]
        records.append(record)
    families = sorted({record["family"] for record in records})
    counts = {family: sum(record["meaningful_counterexample"] and record["warm_replay_available"] for record in records if record["family"] == family) for family in families}
    summary = {"created_at": datetime.now(timezone.utc).isoformat(), "searched_cases": len(records), "cold_valid_cases": len(records), "warm_replayed_cases": sum(record["warm_replay_available"] for record in records), "offline_witness_search_cases": sum(record["witness_search_available"] for record in records), "cold_gaps_at_least_0_5": sum(record["cold_gap"] >= 0.5 for record in records), "best_champion_gaps_at_least_0_5": sum(record["absolute_gap_eligible"] for record in records), "meaningful_persistent_counterexamples": sum(record["meaningful_counterexample"] and record["warm_replay_available"] for record in records), "eligible_counts_by_family": counts, "families_with_at_least_two": [family for family, count in counts.items() if count >= 2], "ready_for_balanced_six_case_proposal": sum(count >= 2 for count in counts.values()) >= 3, "records": records}
    write_json(ROOT / ("analysis_partial.json" if args.partial else "analysis.json"), summary)
    print({key: value for key, value in summary.items() if key != "records"})
    for record in records:
        print(record["case_id"], "B", "%.12f" % record["baseline_energy"], "W", "%.12f" % record["witness_energy"], "cold_gap", "%.6f" % record["cold_gap"], "remaining", "%.6f" % record["persistent_gap"], "warm", record["warm_replay_available"])


if __name__ == "__main__":
    main()
