import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from cases import cases
from run import check_frozen, run_case


SIDE = Path(__file__).resolve().parent
ROOT = SIDE.parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", choices=("first_frozen", "robust", "champion_v2"), required=True)
    arguments = parser.parse_args()
    check_frozen()
    sources = {"first_frozen": "attempts/v_1_frozen_submission/solution.py",
               "champion_v2": "attempts/v_2_frozen_submission/solution.py",
               "robust": "adversary/portfolio/reference/solution.py"}
    source = ROOT / sources[arguments.policy]
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    original = json.loads((ROOT / "evaluator/hidden/episodes.json").read_text())["episodes"][0]
    original["rates"] = np.asarray(original["rates"])
    original["id"] = "original_chain_hooks_0"
    suite = [original] + list(cases(sizes=(20, 18, 16, 14), topologies=("ladder",)))
    results = []
    for case in suite:
        workspace = SIDE / "candidates" / arguments.policy / case["id"] / "submission"
        workspace.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(source, workspace / "solution.py")
        command = ["/usr/bin/python3", "/submission/solution.py"]
        if arguments.policy == "robust":
            command += ["--policy", "robust"]
        logs = SIDE / "runs" / (arguments.policy + "_control_logs")
        logs.mkdir(parents=True, exist_ok=True)
        result = run_case(case, workspace, command, logs, bridge=True)
        result["source_sha256"] = source_hash
        result["source_unchanged"] = hashlib.sha256((workspace / "solution.py").read_bytes()).hexdigest() == source_hash
        result["original_protocol_at_worker"] = True
        result["worker_memory_cap_GiB"] = 3
        assert result["source_unchanged"]
        if case["id"] == "original_chain_hooks_0" and arguments.policy == "first_frozen":
            official = json.loads((ROOT / "attempts/v_1_result.json").read_text())["episodes"][0]
            assert result["valid"]
            for family, mse in official["family_mse"].items():
                assert np.isclose(result["family_log_rmse"][family]**2, mse, atol=1e-12)
            result["original_official_case_reproduced"] = True
        results.append(result)
        output = {"status": "private_preparation_only", "generation_created": False, "targets": None,
                  "policy": arguments.policy, "source_sha256": source_hash, "cases": results,
                  "qualification": "Unchanged programs are scaling controls only, not scores on the original task."}
        (SIDE / "runs" / (arguments.policy + "_control_report.json")).write_text(json.dumps(output, indent=2) + "\n")
        print(json.dumps(result), flush=True)
    check_frozen()


if __name__ == "__main__":
    main()
