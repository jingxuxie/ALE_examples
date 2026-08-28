from __future__ import annotations

import json
import sys

from runtime import PILOT

import numpy as np
from bposd.css import css_code

sys.path.insert(0, str(PILOT / "private"))
from metrics import CORE, load_npz, measure, summarize


def main():
    identifiers = set()
    reports = {}
    for path in sorted((PILOT / "private/challenge_pool").glob("*/manifest.json")):
        manifest = json.loads(path.read_text())
        if manifest["split"] == "holdout" and manifest.get("generation_phase") != "post_attempt_fresh":
            continue
        assert manifest["ready"]
        scored = {mode: [] for mode in ("weak", "reference", "oracle")}
        for record in manifest["cases"]:
            assert record["case_id"] not in identifiers
            identifiers.add(record["case_id"])
            case = load_npz(path.parent / record["input"])
            truth = load_npz(path.parent / record["truth"])
            assert not np.any(case["checks"] @ case["stabilizers"].T % 2)
            assert not np.any(case["metachecks"] @ case["checks"] % 2)
            oracle = {name: truth[name].copy() for name in ("increments", "syndrome_history")}
            oracle_metrics = measure(case, truth, oracle)
            assert all(oracle_metrics[metric] == 1.0 for metric in CORE)
            equivalent = {name: value.copy() for name, value in oracle.items()}
            equivalent["increments"][:, 0] ^= case["stabilizers"][0]
            assert measure(case, truth, equivalent)["logical_accuracy"] == 1.0
            code = css_code(case["stabilizers"], case["checks"])
            logical = code.lx.toarray()[0] if hasattr(code.lx, "toarray") else code.lx[0]
            logical_failure = {name: value.copy() for name, value in oracle.items()}
            logical_failure["increments"][:, 0] ^= np.asarray(logical, dtype=np.uint8)
            independent = measure(case, truth, logical_failure)
            assert independent["logical_accuracy"] == 0.0
            assert independent["history_balanced_accuracy"] == 1.0
            time_blind = {
                "increments": np.zeros_like(oracle["increments"]),
                "syndrome_history": np.zeros_like(oracle["syndrome_history"]),
            }
            time_blind["increments"][:, -1] = truth["final_error"]
            time_blind["syndrome_history"][:, -1] = case["terminal_syndrome"]
            independent = measure(case, truth, time_blind)
            assert independent["logical_accuracy"] == 1.0
            assert independent["history_balanced_accuracy"] == 0.5
            inconsistent = {name: value.copy() for name, value in oracle.items()}
            inconsistent["syndrome_history"][:, 0, 0] ^= 1
            assert measure(case, truth, inconsistent)["valid_fraction"] == 0.0
            for mode in ("weak", "reference", "oracle"):
                prediction = oracle if mode == "oracle" else load_npz(path.parent / record["outputs"][mode])
                metrics = measure(case, truth, prediction)
                if mode == "reference":
                    assert metrics["valid_fraction"] == 1.0
                scored[mode].append({"family": record["family"], "metrics": metrics})
        scores = {mode: summarize(results, manifest["anchors"]) for mode, results in scored.items()}
        assert abs(scores["weak"]["mean_core"]) < 1e-12
        assert abs(scores["reference"]["mean_core"] - 1.0) < 1e-12
        assert scores["oracle"]["mean_core"] > 1.0
        reports[manifest["split"]] = {
            "cases": len(manifest["cases"]),
            "shots": sum(record["shots"] for record in manifest["cases"]),
            "weak_mean_core": scores["weak"]["mean_core"],
            "reference_mean_core": scores["reference"]["mean_core"],
            "oracle_mean_core": scores["oracle"]["mean_core"],
            "anchors": manifest["anchors"],
        }
    assert {"pilot", "challenge"} <= set(reports)
    public = load_npz(PILOT / "participant/input/example.npz")
    assert public["readout"].shape[0] == 2
    assert not {"increments", "syndrome_history", "final_error", "logical_checks"} & set(public)
    report = {
        "passed": True,
        "checks": [
            "commutation and metachecks", "independent GF(2) rank checks in constructor",
            "logical equivalence accepts stabilizers", "nontrivial logical rejected despite perfect history",
            "perfect final recovery does not solve history reconstruction",
            "inconsistent history rejected", "weak=0 and reference=1", "unclipped oracle exceeds 1",
            "disjoint private case identifiers", "two-shot public input has no labels",
        ],
        "splits": reports,
    }
    (PILOT / "private/reference/audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
