import argparse
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

ROOT = Path(__file__).resolve().parents[1] / "concept_3/generations/generation_2"
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
import exact


def make_protocol(original, index):
    protocol = copy.deepcopy(original)
    namespace = "pal-huse-generation-two-independent-stress-" + str(index)
    for family in protocol["families"]:
        offsets = []
        for member in range(32):
            values = []
            for site in range(12):
                message = f"{namespace}|{family['name']}|{member}|{site}".encode()
                number = int.from_bytes(hashlib.sha256(message).digest()[:8], "big")
                values.append(2.0 * number / (2 ** 64 - 1) - 1.0)
            values = np.asarray(values)
            offsets.append((family["amplitude_before_centering"] * (values - values.mean())).tolist())
        family["offsets"] = offsets
    protocol["generator"] = {"algorithm": "sha256-u64-centered-v1", "namespace": namespace,
                             "members_per_family": 32, "purpose": "private champion replication stress"}
    exact.validate_protocol(protocol)
    return protocol


def assess_job(job):
    index, witness, protocol = job
    try:
        result = exact.assess(witness, protocol)
        result.pop("members")
    except ValueError as error:
        result = {"valid": False, "pass": False, "core": None, "worst_family": None, "reason": str(error)}
    return {"replication": index, "protocol_sha256": hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest(),
            "result": result}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--witness", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replications", type=int, default=16)
    parser.add_argument("--workers", type=int, default=8)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise ValueError("Refusing to overwrite completed stress evidence")
    witness = json.loads(arguments.witness.read_text())
    exact.validate_witness(witness)
    original = json.loads((ROOT / "evaluator/hidden/protocol.json").read_text())
    protocols = [make_protocol(original, index) for index in range(arguments.replications)]
    started = time.monotonic()
    jobs = [(index, witness, protocol) for index, protocol in enumerate(protocols)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        records = list(executor.map(assess_job, jobs))
    valid = [row["result"] for row in records if row["result"]["valid"]]
    summary = {"passes": sum(row["result"]["pass"] for row in records),
               "replications": len(records), "valid_replications": len(valid),
               "mean_core": float(np.mean([row["core"] for row in valid])) if valid else None,
               "minimum_core": min([row["core"] for row in valid], default=None),
               "minimum_worst_family": min([row["worst_family"] for row in valid], default=None),
               "failure_reasons": sorted({row["result"]["reason"] for row in records if not row["result"]["pass"]})}
    report = {"summary": summary, "records": records,
              "seconds": time.monotonic() - started,
              "witness_sha256": hashlib.sha256(arguments.witness.read_bytes()).hexdigest(),
              "targets_unchanged": True, "family_laws_unchanged": True,
              "independent_perturbations": 128 * arguments.replications,
              "same_base_reused_across_replications": True,
              "primary_frozen_evaluation_unchanged": True}
    arguments.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"summary": summary, "seconds": report["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
