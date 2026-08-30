import sys

sys.dont_write_bytecode = True

import json
from pathlib import Path

from cases import cases
from run import check_frozen
from validate import moment_information
from worker_support.local_model import feature_masks


SIDE = Path(__file__).resolve().parent


def main():
    check_frozen()
    results = []
    for case in cases():
        result = {"case": case["id"], "detectors": case["spec"]["detector_count"],
                  "channels": len(case["spec"]["channels"]),
                  "information": moment_information(case["spec"], case["rates"], feature_masks(case["spec"]))}
        results.append(result)
        (SIDE / "information_report.json").write_text(json.dumps({"status": "unfrozen_information_diagnostic",
            "targets": None, "cases": results,
            "warning": "Exact within-shot cross-feature/shared-mode covariance; asymptotic optimal-moment uncertainty, not a finite-budget solver or a full likelihood CRB."}, indent=2) + "\n")
        print(json.dumps(result), flush=True)
    check_frozen()


if __name__ == "__main__":
    main()
