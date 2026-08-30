"""Private paired transcript comparison, never a substitute for sandbox scoring."""

import json
from concurrent.futures import ProcessPoolExecutor

import ratchet


def compare(case):
    records = []
    for name in ("champion_original", "champion_parameterized"):
        ratchet.initialize(ratchet.HERE / "profiles/control", ratchet.HERE / "policies" / (name + ".py"))
        device = ratchet.EVALUATOR.Device(case["family"], case["contamination_denominator"], case["seed"])
        policy = ratchet.POLICY_MODULE.Policy(device.handle)
        prediction = policy.run()
        device.handle({"op": "guess", "family": prediction})
        records.append({"transcript": device.transcript, "prediction": prediction, "queries": device.queries, "frames": device.frames, "trace": policy.trace})
    return {"seed": case["seed"], "exact_transcripts_equal": records[0] == records[1], "prediction": records[0]["prediction"], "queries": records[0]["queries"], "frames": records[0]["frames"], "trace": records[0]["trace"]}


def main():
    path = ratchet.HERE / "reports/control_original-control_champion_original"
    cases = json.loads((path / "private_cases.json").read_text())
    with ProcessPoolExecutor(max_workers=16) as executor:
        comparisons = list(executor.map(compare, cases))
    original = {record["case"]["seed"]: record for record in json.loads((path / "episodes.json").read_text())}
    for comparison in comparisons:
        scored = original[comparison["seed"]]
        comparison["matches_sandbox_prediction_and_resources"] = all(comparison[key] == scored["result"][key] for key in ("prediction", "queries", "frames"))
        comparison["matches_sandbox_replayed_trace"] = json.loads(json.dumps(comparison["trace"])) == scored["diagnostic"]["trace"]
    report = {"episodes": len(comparisons), "exact_transcripts_equal": sum(row["exact_transcripts_equal"] for row in comparisons), "sandbox_predictions_resources_traces_match": sum(row["matches_sandbox_prediction_and_resources"] and row["matches_sandbox_replayed_trace"] for row in comparisons), "passed": all(row["exact_transcripts_equal"] and row["matches_sandbox_prediction_and_resources"] and row["matches_sandbox_replayed_trace"] for row in comparisons), "scope": "Private original-contract functional equivalence only; actual control and candidate scores use bwrap plus the unmodified parent evaluator."}
    (ratchet.HERE / "validation_equivalence.json").write_text(ratchet.encoded(report))
    print(ratchet.encoded(report))


if __name__ == "__main__":
    main()
