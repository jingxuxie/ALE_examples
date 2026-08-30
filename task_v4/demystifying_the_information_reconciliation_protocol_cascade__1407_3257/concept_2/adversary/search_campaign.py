import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from replay import replay


def search():
    deployment = json.loads((ROOT / "participant/input/deployment.json").read_text())
    generator = random.Random(528740071331)
    started = time.monotonic()
    families = {}
    for weight in (8, 12, 16, 20, 24):
        survivors = 0
        valid_witnesses = 0
        maximum_residual = 0
        trials = 256
        for repetition in range(trials):
            errors = generator.sample(range(deployment["n"]), weight)
            result = replay(deployment, errors, "earliest")
            maximum_residual = max(maximum_residual, len(result["residual"]))
            survivors += bool(result["residual"])
            valid_witnesses += len(result["residual"]) >= 8 and len(result["corrected"]) >= 6 and result["initial_odd"] >= 6
        families[str(weight)] = {"trials": trials, "surviving_frames": survivors, "max_residual": maximum_residual, "valid_witnesses": valid_witnesses}
    witness = json.loads((ROOT / "evaluator/hidden/privileged_witness.json").read_text())
    certificate = [replay(deployment, witness["errors"], priority) for priority in ("earliest", "shortest")]
    signatures = []
    for position in range(deployment["n"]):
        signature = []
        for specification in deployment["passes"]:
            signature.append(specification["permutation"].index(position) // specification["block_size"])
        signatures.append(tuple(signature))
    report = {"campaign": "pre-attempt private random search plus constructive adversary", "random_trials": sum(value["trials"] for value in families.values()), "families": families, "duplicate_column_signatures": len(signatures) - len(set(signatures)), "privileged_certificate": certificate, "elapsed_seconds": time.monotonic() - started, "root_cause": "Known-parity consistency does not rule out a nonzero discrepancy pattern in the simultaneous kernel of fixed shuffle partitions. Initial corrections in other roots do not activate that core.", "interpretation": "Uniform bounded-weight random trials are a search diagnostic, not a statistically justified BSC failure-rate estimate. The deployment has adversarially conditioned valid permutations."}
    (ROOT / "adversary/search_results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"random_trials": report["random_trials"], "families": families, "elapsed_seconds": report["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    search()
