import json
from pathlib import Path

from harness import ROOT, load_mps, measure, sha256, write_json


def main():
    cases = []
    cpu_total = 0.0
    for path in sorted((ROOT / "requests").glob("*.json")):
        if path.name.endswith(".provenance.json"):
            continue
        request = json.loads(path.read_text())
        records = {}
        for result_path in sorted((ROOT / "runs" / request["case_id"]).glob("*/result.json")):
            result = json.loads(result_path.read_text())
            cpu_total += result["cpu_seconds"]
            state = result_path.with_name("state.npz")
            if result.get("physical_validity") and result["returncode"] == 0:
                assert sha256(state) == result["state_sha256"]
                checked = measure(load_mps(state, request), request)
                assert abs(checked["energy"] - result["measurement"]["energy"]) < 1e-9
                records[result_path.parent.name] = {
                    "energy": checked["energy"], "parity": checked["parity"],
                    "max_bond": checked["max_bond"], "cpu_seconds": result["cpu_seconds"],
                    "wall_seconds": result["wall_seconds"], "state": str(state.relative_to(ROOT)),
                    "state_sha256": sha256(state), "resource_observation_valid": result["resource_observation_valid"],
                    "entropy": result["diagnostics"]["center_entropy"],
                    "max_entropy": result["diagnostics"]["max_entropy"],
                    "cutoff": result["diagnostics"]["max_cutoff_edge_population"],
                }
        if not records:
            continue
        best_label = min(records, key=lambda label: records[label]["energy"])
        entry = {"case_id": request["case_id"], "records": records,
                 "attainable_reference": best_label, "screen": 1e-7 * request["n_sites"],
                 "ground_energy_certified": False}
        if "v4_40" in records:
            gap = records["v4_40"]["energy"] - records[best_label]["energy"]
            entry.update(v4_energy_gap=gap, v4_gap_per_site=gap / request["n_sites"],
                         v4_above_screen=gap > entry["screen"])
        if "v3_40" in records:
            gap = records["v3_40"]["energy"] - records[best_label]["energy"]
            entry.update(v3_energy_gap=gap, v3_gap_per_site=gap / request["n_sites"])
        cases.append(entry)
        print(request["case_id"], " ".join(label + "=" + format(record["energy"], ".12f")
                                           for label, record in records.items()),
              "v4_gap/site=", entry.get("v4_gap_per_site"), flush=True)
    summary = {"cases": cases, "completed_child_cpu_seconds": cpu_total,
               "completed_cases": len(cases), "scientific_screen_per_site": 1e-7,
               "frozen_evaluator_invoked": False, "timing_failure_is_scientific_failure": False}
    write_json(ROOT / "SUMMARY.json", summary)
    print("completed_child_cpu_seconds", cpu_total)


if __name__ == "__main__":
    main()
