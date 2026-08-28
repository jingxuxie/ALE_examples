import concurrent.futures
import json
from pathlib import Path
import shutil

from reference.run import worker

ROOT = Path(__file__).resolve().parent
PHYSICAL = [0, 1, 2, 5, 6, 7, 8]


def main():
    case_id = "ce_surface_compensation"
    folder = ROOT / "reference/results" / case_id
    archive = folder / "first_pass"
    archive.mkdir(exist_ok=True)
    if not (archive / "validation.json").exists():
        for path in folder.glob("*.json"):
            shutil.copyfile(path, archive / path.name)
    original = json.loads((archive / "validation.json").read_text())
    case = json.loads((ROOT / "cases" / f"{case_id}.json").read_text())
    plan = {"reason": "Extend every physical-observable Rhat or split-Rhat failure without changing any gate.",
            "burn": 60000, "sweeps": 120000,
            "starts": ["aligned", "hot", "domain_x", "domain_z"],
            "retention": "All first-pass trajectories and diagnostics retained; no frozen pilot/reference files changed.",
            "replacements": {}}
    jobs = []
    for kind, records in original["records"].items():
        if isinstance(records, dict):
            records = [records]
        for record in records:
            maximum = max(record[key][column] for key in ["rhat", "split_rhat"] for column in PHYSICAL)
            if maximum < 1.05:
                continue
            angle = record["angle"]
            raw_kind = kind + "_extended"
            plan["replacements"][f"{case_id}:{kind}:{angle:.10f}"] = {
                "raw_kind": raw_kind, "chains": 4, "first_pass_max_rhat_or_split": maximum}
            for chain, start in enumerate(plan["starts"]):
                jobs.append((case, angle, chain, raw_kind, plan["burn"], plan["sweeps"], start))
    path = ROOT / "reference/refinement_plan.json"
    if path.exists():
        assert json.loads(path.read_text()) == plan
    else:
        path.write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps(plan), flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(worker, job) for job in jobs]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            print(f"refine {index}/{len(jobs)}: {future.result()}", flush=True)


if __name__ == "__main__":
    main()
