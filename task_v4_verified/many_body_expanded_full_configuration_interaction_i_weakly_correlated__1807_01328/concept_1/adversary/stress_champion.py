import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")


def evaluate(submission, report, cases=None, models=None):
    command = [sys.executable, str(ROOT / "evaluator/evaluate.py"), "--submission", str(submission), "--output", str(report)]
    if cases is not None:
        command.extend(["--cases", str(cases), "--models", str(models)])
    completed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, env=ENVIRONMENT, timeout=230)
    if completed.returncode:
        raise RuntimeError(completed.stdout)
    result = json.loads(report.read_text())
    print(json.dumps({"report": str(report), **{key: result.get(key) for key in
                     ("valid", "passed", "rmse_hartree", "worst_family_rmse_hartree", "cpu_seconds", "runtime_seconds", "reason")}}), flush=True)
    return result


def main():
    hidden = ROOT / "evaluator/hidden"
    first_score = ROOT / "attempts/v_1.score.json"
    for path in (hidden / "baseline_score.json", first_score):
        old = path.with_name(path.stem + "_before_resource_audit.json")
        if not old.exists():
            shutil.copy2(path, old)
    baseline = evaluate(ROOT / "participant/baseline", hidden / "baseline_score.json")
    champion = evaluate(ROOT / "attempts/v_1", first_score)
    if not baseline["valid"] or not champion["valid"]:
        raise RuntimeError("resource-accounted validation failed")
    if not champion["passed"]:
        print("First-round champion no longer passes under corrected accounting; do not ratchet.", flush=True)
        return
    subprocess.run([sys.executable, str(ROOT.parent / "research/archive_champion.py"), "concept_1"],
                   stdin=subprocess.DEVNULL, check=True, env=ENVIRONMENT)
    search = ROOT / "adversary/champion_search"
    search.mkdir(parents=True, exist_ok=True)
    source = ROOT / "adversary/private_challenges"
    tables = np.load(source / "cases.npz", allow_pickle=False)["energies"]
    models = json.loads((source / "models.json").read_text())
    batches = []
    for index in range(5):
        batch = search / f"batch_{index}"
        batch.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(batch / "cases.npz", energies=tables[index * 120:(index + 1) * 120])
        (batch / "models.json").write_text(json.dumps(models[index * 120:(index + 1) * 120]))
        batches.append(batch)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(evaluate, ROOT / "champions/generation_1/submission", batch / "score.json",
                               batch / "cases.npz", batch / "models.json") for batch in batches]
        results = [future.result() for future in futures]
    records = []
    for index, result in enumerate(results):
        for record in result.get("records", []):
            records.append({**record, "source_index": index * 120 + record["index"], "batch": index})
    errors = np.asarray([record["error"] for record in records])
    family_rmse = {family: float(np.sqrt(np.mean([record["error"] ** 2 for record in records if record["family"] == family])))
                   for family in sorted({record["family"] for record in records})}
    summary = {"case_count": len(records), "requested_case_count": 600,
               "all_batches_valid": all(result["valid"] for result in results),
               "passed_batches": sum(result["passed"] for result in results), "batch_count": 5,
               "rmse_hartree": float(np.sqrt(np.mean(errors ** 2))) if len(errors) else None,
               "family_rmse_hartree": family_rmse,
               "worst_family_rmse_hartree": max(family_rmse.values()) if family_rmse else None,
               "over_25_microhartree": int(np.sum(np.abs(errors) > 2.5e-5)),
               "maximum_absolute_error_hartree": float(np.max(np.abs(errors))) if len(errors) else None,
               "cpu_limit_per_120_case_batch": 120, "wall_limit_per_120_case_batch": 180,
               "records": records}
    (search / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "records"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
