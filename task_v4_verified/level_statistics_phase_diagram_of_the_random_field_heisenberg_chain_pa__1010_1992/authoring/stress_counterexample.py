import concurrent.futures
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1] / "concept_3"
GENERATION = ROOT / "generations/generation_1" if (ROOT / "generations/generation_1/participant").exists() else ROOT
sys.path.insert(0, str(GENERATION / "evaluator/hidden"))
from exact import assess


def make_protocol(original, namespace):
    protocol = copy.deepcopy(original)
    protocol["offset_namespace"] = namespace
    for family in protocol["families"]:
        offsets = []
        for member in range(8):
            values = []
            for site in range(12):
                text = f"{namespace}|{family['name']}|{member}|{site}"
                integer = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
                values.append(2 * integer / (2 ** 64 - 1) - 1)
            values = np.array(values)
            offsets.append(((values - values.mean()) * family["amplitude_before_centering"]).tolist())
        family["offsets"] = offsets
    return protocol


def evaluate_job(job):
    identity, replicate, witness, protocol = job
    try:
        result = assess(witness, protocol)
    except ValueError as error:
        result = {"valid": False, "pass": False, "reason": str(error), "core": None, "worst_family": None}
    return {"source": identity, "replicate": replicate, "result": result}


def main():
    original = json.loads((GENERATION / "evaluator/hidden/protocol.json").read_text())
    sources = {"fresh_v2": ROOT / "attempts/v_2/witness.json",
               "privileged_initial": ROOT / "adversary/champions/witness.json"}
    protocols = [make_protocol(original, "palhuse-blind-replication-" + str(index)) for index in range(16)]
    jobs = [(identity, index, json.loads(path.read_text()), protocol)
            for identity, path in sources.items() for index, protocol in enumerate(protocols)]
    started = time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        records = list(executor.map(evaluate_job, jobs))
    summary = {}
    for identity in sources:
        selected = [record["result"] for record in records if record["source"] == identity]
        summary[identity] = {"passes": sum(record["pass"] for record in selected), "replications": len(selected),
                             "mean_core": float(np.mean([record["core"] for record in selected if record["valid"]])),
                             "min_core": min(record["core"] for record in selected if record["valid"]),
                             "min_worst_family": min(record["worst_family"] for record in selected if record["valid"]),
                             "failure_reasons": sorted(set(record["reason"] for record in selected if not record["pass"]))}
    result = {"summary": summary, "records": records, "seconds": time.monotonic() - started,
              "challenged_claim": "replicability of a robust spectral-window discrepancy under independent draws of exactly the same perturbation law",
              "targets_unchanged": True, "root_cause_clusters": ["public-calibration overfitting", "insufficient per-family signed discrepancy under independent field jitter"]}
    (ROOT / "adversary/champion_stress.json").write_text(json.dumps(result, indent=2) + "\n")
    (ROOT / "adversary/private_replication_protocols.json").write_text(json.dumps(protocols) + "\n")
    print(json.dumps({"summary": summary, "seconds": result["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
