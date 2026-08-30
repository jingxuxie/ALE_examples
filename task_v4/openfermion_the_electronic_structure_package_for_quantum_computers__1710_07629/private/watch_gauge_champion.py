import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
        os.environ[variable] = "1"
    import numpy as np

    concept = ROOT / "concept_1"
    pool = concept / "adversary/second_generation_search"
    destination = pool / "champion_2_audit"
    destination.mkdir(exist_ok=True)
    official_path = concept / "attempts/v_2.evaluation.json"
    while not official_path.exists():
        time.sleep(5)
    official = json.loads(official_path.read_text())
    if not official["passed"]:
        report = {"performed": False, "reason": "Fresh generation-one challenger did not pass; private pool remains exploratory provenance, not a built task.", "official_report": "attempts/v_2.evaluation.json"}
        (destination / "report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report), flush=True)
        return
    launch = json.loads((concept / "attempts/v_2.launch.json").read_text())
    snapshot = Path(launch["scoring_snapshot"])
    champion = concept / "champions/generation_2"
    if champion.exists():
        raise RuntimeError("champion generation already exists")
    shutil.copytree(snapshot, champion, symlinks=True)
    hashes = {str(path.relative_to(champion)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(champion.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}
    (concept / "champions/generation_2_manifest.json").write_text(json.dumps({"source": str(snapshot), "official_score": official, "sha256": hashes}, indent=2))
    cases = json.loads((pool / "cases.json").read_text())["cases"]
    references = {row["id"]: row for row in json.loads((pool / "private_references.json").read_text())["records"]}
    evaluator = concept / "generations/generation_1/evaluator/evaluate.py"
    records = []
    for offset in range(0, len(cases), 2):
        batch = destination / f"batch_{offset // 2:02d}"
        batch.mkdir(exist_ok=True)
        entries = []
        for case in cases[offset:offset + 2]:
            entries.append(dict(case, baseline_cost=references[case["id"]]["initial_cost"]))
        (batch / "request.json").write_text(json.dumps({"cases": entries, "seconds_per_case": 10}))
        command = [sys.executable, str(ROOT / "private/affinity.py"), str(ROOT / "private/capture_gauge_evaluation.py"), "--evaluator", str(evaluator), "--submission", str(champion), "--cases", str(batch / "request.json"), "--report", str(batch / "report.json"), "--response", str(batch / "response.json")]
        with (batch / "evaluation.log").open("w") as logfile:
            subprocess.run(command, stdout=logfile, stderr=subprocess.STDOUT, timeout=300)
        report = json.loads((batch / "report.json").read_text())
        if not report["valid"]:
            for case in entries:
                records.append({"id": case["id"], "valid": False, "reason": report["reason"]})
            continue
        solutions = {row["id"]: row for row in json.loads((batch / "response.json").read_text())["solutions"]}
        for case in entries:
            solution = solutions[case["id"]]
            orbital = np.asarray(solution["orbital"])
            auxiliary = np.asarray(solution["auxiliary"])
            one_body = np.asarray(case["one_body"])
            factors = np.asarray(case["factors"])
            rotated = np.einsum("pi,rpq,qj->rij", orbital, factors, orbital, optimize=True)
            mixed = np.einsum("kr,rij->kij", auxiliary, rotated, optimize=True)
            cost = float(np.abs(orbital.T @ one_body @ orbital).sum() + 0.5 * np.square(np.abs(mixed).sum(axis=(1, 2))).sum())
            private_cost = references[case["id"]]["absolute_cost"]
            records.append({"id": case["id"], "valid": True, "champion_cost": cost, "private_feasible_cost": private_cost, "additional_feasible_reduction": 1 - private_cost / cost, "batch_runtime_seconds": report["runtime_seconds"]})
        print(json.dumps({"completed": len(records), "positive_quality_gaps": sum(row.get("additional_feasible_reduction", 0) > 1e-5 for row in records)}), flush=True)
    gaps = [row["additional_feasible_reduction"] for row in records if row["valid"]]
    summary = {"performed": True, "champion": "champions/generation_2", "cases": len(records), "valid_cases": len(gaps), "invalid_cases": len(records) - len(gaps), "positive_quality_gaps": sum(gap > 1e-5 for gap in gaps), "gaps_at_least_one_percent": sum(gap >= 0.01 for gap in gaps), "maximum_additional_feasible_reduction": max(gaps) if gaps else None, "not_a_global_optimality_test": True, "reference_costs_are_quality_feasible_only": True, "inference_protocol": "Twelve independent two-case batches, twenty-second wall/CPU limit, one CPU, shared timed-evaluation mutex", "records": records}
    (destination / "report.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({key: value for key, value in summary.items() if key != "records"}), flush=True)


if __name__ == "__main__":
    main()
