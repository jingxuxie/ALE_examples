import concurrent.futures
import json
from pathlib import Path
import time

from stress_counterexample import evaluate_job


def main():
    root = Path(__file__).resolve().parents[1] / "concept_3"
    protocols = json.loads((root / "adversary/private_replication_protocols.json").read_text())
    witness = json.loads((root / "champions/generation_1/submission/witness.json").read_text())
    started = time.monotonic()
    jobs = [("fresh_v1_best_initial_core", index, witness, protocol) for index, protocol in enumerate(protocols)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        records = list(executor.map(evaluate_job, jobs))
    for record in records:
        record["result"].pop("members", None)
    scores = [record["result"] for record in records]
    summary = {"passes": sum(score["pass"] for score in scores), "replications": len(scores),
               "mean_core": sum(score["core"] for score in scores) / len(scores),
               "min_core": min(score["core"] for score in scores),
               "min_worst_family": min(score["worst_family"] for score in scores)}
    report = {"summary": summary, "records": records, "seconds": time.monotonic() - started,
              "same_private_protocols_as_initial_champion_stress": True,
              "completed_after_generation_two_freeze": True,
              "generation_two_targets_and_data_unchanged": True}
    (root / "adversary/best_champion_replication.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"summary": summary, "seconds": report["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
