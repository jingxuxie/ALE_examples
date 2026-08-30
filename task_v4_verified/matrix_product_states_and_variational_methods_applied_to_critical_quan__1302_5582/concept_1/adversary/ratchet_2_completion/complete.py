from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import sys


WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from sandbox_runner import run_submission
from trusted_contractor import load_mps, measure


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def contract_bulk(request, length):
    result = copy.deepcopy(request)
    half = length // 2
    indices = list(range(half)) + list(range(request["n_sites"] - half, request["n_sites"]))
    result.update(n_sites=length, case_id=f"edge_preserving_dimer_{length}", seed=920000 + length)
    for coefficient in ("omega", "mass2", "lambda4", "field"):
        result[coefficient] = [request[coefficient][index] for index in indices]
    result["coupling"] = []
    for left, right in zip(indices[:-1], indices[1:]):
        spring = request["coupling"][left]
        if right != left + 1:
            spring = 0.5 * (spring + request["coupling"][right - 1])
        result["coupling"].append(spring)
    result.pop("budget_seconds", None)
    result.pop("wall_seconds", None)
    return result


def run(request, label, source):
    directory = WORK / "runs" / request["case_id"] / label
    assert not directory.exists(), "No automatic diagnostic retry"
    directory.mkdir(parents=True)
    timed = dict(request, budget_seconds=40.0, wall_seconds=120.0)
    write_json(directory / "request.json", timed)
    result = run_submission(source, ROOT / "participant", directory / "scratch", timed)
    row = {"request": request, "label": label, "physical_valid": False,
           "process": {key: value for key, value in result.items() if key != "state_path"}}
    state_value = result.get("state_path")
    if state_value and Path(state_value).is_file():
        state = Path(state_value)
        row["measurement"] = measure(load_mps(state, request), request)
        row["physical_valid"] = True
        row["state"] = str(state.relative_to(ROOT))
        row["state_sha256"] = digest(state)
    write_json(directory / "result.json", row)
    print(json.dumps({"case": request["case_id"], "label": label,
                      "process_valid": result["process_valid"],
                      "cpu": result["cpu_seconds"],
                      "energy": row.get("measurement", {}).get("energy")}), flush=True)
    return row


def main():
    partial_path = ROOT / "adversary/champion_2_exploration/tranche_3/PROPOSAL.json"
    partial = json.loads(partial_path.read_text())
    assert len(partial["cases"]) == 7
    matches = [record for record in partial["cases"]
               if record["source_case_id"] == "f2_even_dimerized"]
    assert len(matches) == 1
    parent = matches[0]
    sources = {"v4": ROOT / "champions/generation_2/submission",
               "v3": ROOT / "adversary/champion_2_scaling/source/v3"}
    fingerprints = {label: {str(path.relative_to(directory)): digest(path)
                            for path in sorted(directory.rglob("*")) if path.is_file()}
                    for label, directory in sources.items()}
    write_json(WORK / "PROVENANCE.json", {
        "partial_proposal": str(partial_path.relative_to(ROOT)),
        "partial_proposal_sha256": digest(partial_path),
        "source_files": fingerprints,
        "generator_sha256": digest(Path(__file__)),
        "construction": "remove central bulk, preserve both edge profiles, average the two bridge springs",
        "prospective_lengths": [32, 48],
        "screen": "repeat baseline minus attainable same-cap energy >= 2e-7*n_sites",
        "new_domain": False,
        "formal_admission": False,
        "fresh_attempt": False,
    })
    observations = []
    for length in (32, 48):
        request = contract_bulk(parent["request"], length)
        write_json(WORK / "requests" / (request["case_id"] + ".json"), request)
        baseline = run(request, "v4_40", sources["v4"])
        reference = run(request, "v3_40", sources["v3"])
        row = {"request": request, "baseline": baseline, "reference": reference,
               "screen": 1e-7 * length, "confirmed": False}
        eligible = all(record["physical_valid"] and record["process"]["process_valid"]
                       for record in (baseline, reference))
        if eligible:
            row["gap"] = baseline["measurement"]["energy"] - reference["measurement"]["energy"]
            if row["gap"] >= 2e-7 * length:
                repeated = run(request, "repeat_v4_40", sources["v4"])
                row["repeat"] = repeated
                if repeated["physical_valid"] and repeated["process"]["process_valid"]:
                    row["repeat_gap"] = repeated["measurement"]["energy"] - reference["measurement"]["energy"]
                    row["confirmed"] = row["repeat_gap"] >= 2e-7 * length
        observations.append(row)
        write_json(WORK / "RESULTS.json", {"cases": observations, "complete_suite": row["confirmed"]})
        if row["confirmed"]:
            required = ("family", "request", "reference_state", "reference_energy", "source_case_id")
            records = [{key: record[key] for key in required} for record in partial["cases"]]
            records.append({"family": parent["family"], "request": request,
                            "reference_state": reference["state"],
                            "reference_energy": reference["measurement"]["energy"],
                            "source_case_id": request["case_id"]})
            assert Counter(record["family"] for record in records) == Counter(
                {family: 2 for family in {record["family"] for record in records}})
            assert len(records) == 8
            write_json(WORK / "PROPOSAL.json", {
                "cases": records,
                "search_summary": {
                    "primary_search": "adversary/champion_2_exploration",
                    "completion": "adversary/ratchet_2_completion/RESULTS.json",
                    "eight_same_cap_attainable_references": True,
                    "all_current_domain_fixed_parity_zero_field": True,
                    "full_6_and_40_second_passing_program_known": False,
                    "no_ground_energy_optimality_claim": True,
                },
            })
            print(json.dumps({"complete_suite": True, "selected_case": request["case_id"],
                              "proposal": str(WORK / "PROPOSAL.json")}), flush=True)
            break
    assert digest(partial_path) == json.loads((WORK / "PROVENANCE.json").read_text())["partial_proposal_sha256"]


if __name__ == "__main__":
    main()
