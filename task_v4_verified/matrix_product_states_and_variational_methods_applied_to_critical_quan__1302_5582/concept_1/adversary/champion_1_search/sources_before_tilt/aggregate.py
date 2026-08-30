import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "champion"))
from contractor import load_mps, measure
from observables import diagnostics


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    records = []
    incomplete = []
    for result_path in sorted((ROOT / "runs").glob("*/result.json")):
        directory = result_path.parent
        stored = json.loads(result_path.read_text())
        if "reference" not in stored:
            incomplete.append(directory.name)
            continue
        request_path = directory / "request.json"
        request = json.loads(request_path.read_text())
        checked = {name: measure(load_mps(directory / (name + ".npz"), request), request)
                   for name in ("champion", "reference")}
        gap = checked["champion"]["energy"] - checked["reference"]["energy"]
        wall_limited = (stored["champion"]["optimization_wall_seconds"] >= request["wall_seconds"] - 0.7
                        and stored["champion"]["optimization_cpu_seconds"] < request["budget_seconds"] - 0.5)
        record = {"case_id": request["case_id"], "request": str(request_path.relative_to(ROOT)),
                  "result": str(result_path.relative_to(ROOT)),
                  "envelope": "original" if request["n_sites"] <= 22 and request["bond_cap"] <= 12
                  else "proposed_same_physics_scaling_only",
                  "n_sites": request["n_sites"], "local_dim": request["local_dim"],
                  "bond_cap": request["bond_cap"], "mass2_center": sum(request["mass2"]) / request["n_sites"],
                  "lambda4_center": sum(request["lambda4"]) / request["n_sites"],
                  "weak_quartic_proposal": min(request["lambda4"]) < 0.5,
                  "sector": request["sector"], "valid": True, "measurements": checked,
                  "achieved_energy_gap": gap, "gap_per_site": gap / request["n_sites"],
                  "gap_above_screen": gap > 1e-7 * request["n_sites"] and not wall_limited,
                  "wall_limited_probe_excluded_from_gap_count": wall_limited,
                  "source_result_agrees": all(abs(checked[name]["energy"] - stored[name]["energy"]) < 1e-10
                                               for name in checked),
                  "champion_cpu_seconds": stored["champion"]["optimization_cpu_seconds"],
                  "champion_wall_seconds": stored["champion"]["optimization_wall_seconds"],
                  "teacher_cpu_seconds": stored["reference"]["optimization_cpu_seconds"],
                  "champion_diagnostics": {key: stored["champion"]["diagnostics"][key] for key in
                                           ("center_entropy", "energy_variance", "max_cutoff_edge_population",
                                            "center_last_two_schmidt_weight", "quarter_chain_phi_phi")},
                  "reference_diagnostics": {key: stored["reference"]["diagnostics"][key] for key in
                                            ("center_entropy", "energy_variance", "max_cutoff_edge_population",
                                             "center_last_two_schmidt_weight", "quarter_chain_phi_phi")},
                  "hashes": {path.name: digest(path) for path in
                             (request_path, directory / "champion.npz", directory / "reference.npz", result_path)}}
        records.append(record)
    short_records = []
    for path in sorted((ROOT / "runs").glob("*/short_result.json")):
        short = json.loads(path.read_text())
        if short["valid_completed_short"]:
            request = json.loads((path.parent / "short_request.json").read_text())
            tensors = load_mps(path.parent / "short.npz", request)
            short["remeasured"] = measure(tensors, request)
            short["diagnostics"] = diagnostics(tensors, request, short["remeasured"]["energy"])
        matching = next((record for record in records if record["case_id"] == short["case_id"]), None)
        if matching is not None and short["valid_completed_short"]:
            short["reference_energy"] = matching["measurements"]["reference"]["energy"]
            short["achieved_energy_gap"] = short["remeasured"]["energy"] - short["reference_energy"]
            short["gap_per_site"] = short["achieved_energy_gap"] / matching["n_sites"]
            short["gap_above_screen"] = short["gap_per_site"] > 1e-7
        short_records.append(short)
    cohorts = {}
    for label in ("original", "proposed_same_physics_scaling_only"):
        selected = [record for record in records if record["envelope"] == label]
        cohorts[label] = {"completed": len(selected),
                          "valid": sum(record["valid"] for record in selected),
                          "gaps_above_screen": sum(record["gap_above_screen"] for record in selected),
                          "maximum_gap": max((record["achieved_energy_gap"] for record in selected), default=None)}
    report = {"mode": "generation-time physical diagnostics only", "score": None,
              "timing_failures_count_as_physical_failures": False,
              "ground_energies_certified": False, "resource_feasible_passing_solver_certified": False,
              "cohorts": cohorts, "incomplete_cases": incomplete,
              "source_hashes": {str(path.relative_to(ROOT)): digest(path) for path in
                                sorted(ROOT.glob("*.py")) + sorted((ROOT / "champion").glob("*.py"))},
              "records": records, "short_records": short_records}
    (ROOT / "SEARCH_STATUS.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    lines = ["# Private physical-search results", "",
             "Generation-only reviewed-copy probes; no frozen evaluator grades or public changes.",
             "References are achieved same-cap variational states, not certified ground energies.",
             "The physical-gap screen is 1e-7 per site; wall-limited probes are excluded.", "",
             "## Long-stage comparisons", "",
             "| Cohort | Completed/valid | Gaps above screen | Largest absolute gap |",
             "|---|---:|---:|---:|"]
    for label, cohort in cohorts.items():
        lines.append("| %s | %d/%d | %d | %s |" %
                     (label, cohort["completed"], cohort["valid"], cohort["gaps_above_screen"],
                      "n/a" if cohort["maximum_gap"] is None else "%.10g" % cohort["maximum_gap"]))
    lines += ["", "| Case | E40 minus reference | Gap/site | Champion CPU | Teacher CPU |",
              "|---|---:|---:|---:|---:|"]
    for record in sorted(records, key=lambda record: record["achieved_energy_gap"], reverse=True):
        lines.append("| `%s` | %.10g | %.10g | %.3f | %.3f |" %
                     (record["case_id"], record["achieved_energy_gap"], record["gap_per_site"],
                      record["champion_cpu_seconds"], record["teacher_cpu_seconds"]))
    lines += ["", "## Completed six-CPU states", "",
              "Direct wait4 CPU includes interpreter/import/save cost; no bwrap certification is claimed.", "",
              "| Case | Valid within limits | CPU/wall | E6 minus reference |",
              "|---|---|---:|---:|"]
    for short in short_records:
        lines.append("| `%s` | %s | %.3f / %.3f | %s |" %
                     (short["case_id"], short["valid_completed_short"], short["cpu_seconds"], short["wall_seconds"],
                      "pending" if "achieved_energy_gap" not in short else "%.10g" % short["achieved_energy_gap"]))
    lines += ["", "Requests, states, full spectra, variances, trajectories, raw timings, and SHA256 hashes",
              "are retained in `runs/<case>/`; `SEARCH_STATUS.json` independently remeasures final files.", ""]
    (ROOT / "FINDINGS.md").write_text("\n".join(lines))
    print(json.dumps({"cohorts": cohorts, "incomplete": incomplete}, indent=2))


if __name__ == "__main__":
    main()
