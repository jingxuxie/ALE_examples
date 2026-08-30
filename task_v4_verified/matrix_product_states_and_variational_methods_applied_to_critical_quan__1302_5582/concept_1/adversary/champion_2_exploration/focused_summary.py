import json

from harness import ROOT, load_mps, measure, sha256, write_json


def summarize(remeasure=False):
    cases = []
    cpu = 0.0
    for path in sorted((ROOT / "requests").glob("f2_*.json")):
        if path.name.endswith(".provenance.json"):
            continue
        request = json.loads(path.read_text())
        records = {}
        for result_path in sorted((ROOT / "runs" / request["case_id"]).glob("*/result.json")):
            result = json.loads(result_path.read_text())
            cpu += result["cpu_seconds"]
            if result.get("physical_validity") and result["returncode"] == 0:
                if remeasure:
                    state_path = result_path.with_name("state.npz")
                    assert sha256(state_path) == result["state_sha256"]
                    checked = measure(load_mps(state_path, request), request)
                    assert abs(checked["energy"] - result["measurement"]["energy"]) < 1e-9
                records[result_path.parent.name] = {
                    "energy": result["measurement"]["energy"],
                    "parity": result["measurement"]["parity"],
                    "max_bond": result["measurement"]["max_bond"],
                    "cpu_seconds": result["cpu_seconds"], "wall_seconds": result["wall_seconds"],
                    "state_sha256": result["state_sha256"],
                    "state": str(result_path.with_name("state.npz").relative_to(ROOT)),
                    "resource_observation_valid": result["resource_observation_valid"],
                }
        if not records:
            continue
        best = min(records, key=lambda label: records[label]["energy"])
        entry = {"case_id": request["case_id"], "records": records, "attainable_reference": best,
                 "bond_cap": request["bond_cap"], "sector": request["sector"],
                 "ground_energy_certified": False, "screen": 6.4e-6}
        if "v4_40" in records:
            gap = records["v4_40"]["energy"] - records[best]["energy"]
            entry.update(v4_energy_gap=gap, v4_gap_per_site=gap / 64,
                         screen_multiple=gap / 6.4e-6, above_screen=gap > 6.4e-6)
        cases.append(entry)
    summary = {"cases": cases, "recorded_cpu_seconds": cpu, "cpu_limit_seconds": 1200,
               "completed_cases": len(cases), "formal_generation": False,
               "positive_cases": [entry["case_id"] for entry in cases if entry.get("above_screen")]}
    write_json(ROOT / "tranche_2/SUMMARY.json", summary)
    return summary


if __name__ == "__main__":
    summary = summarize(True)
    for entry in summary["cases"]:
        print(entry["case_id"], "screen_multiple", entry.get("screen_multiple"),
              {label: record["energy"] for label, record in entry["records"].items()})
    print("recorded_cpu_seconds", summary["recorded_cpu_seconds"])
