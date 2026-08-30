from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import time


AREA = Path(__file__).resolve().parent
specification = importlib.util.spec_from_file_location("generation_three_sweep", AREA / "sweep.py")
sweep = importlib.util.module_from_spec(specification)
import sys
sys.modules[specification.name] = sweep
specification.loader.exec_module(sweep)


def main():
    cases = [{"family": family, "shape": list(shape), "replica": replica, "seed_hex": secrets.token_hex(16)}
             for family in sweep.model.FAMILIES for shape in sweep.model.SHAPES for replica in range(2)]
    seed_path = AREA / "cases_confirmation.json"
    assert not seed_path.exists()
    seed_path.write_text(json.dumps(cases, indent=2) + "\n")
    jobs = [dict(case, budget=budget, strategy=strategy, isolation="bwrap", label="confirmation",
                 id=str(budget) + "_" + strategy + "_" + str(case_index))
            for budget, strategy in ((2000, "proportional"), (6000, "adaptive"))
            for case_index, case in enumerate(cases) if budget == 2000 or case["replica"] == 0]
    started = time.monotonic()
    records = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(sweep.execute, job) for job in jobs]
        for future in as_completed(futures):
            records.append(future.result())
            if len(records) % 6 == 0:
                print(json.dumps({"completed": len(records), "total": len(jobs),
                                  "valid": all(record["valid"] for record in records)}), flush=True)
    report = {"calibration_only": False, "sampler_rescaled": False,
              "seed_manifest_sha256": hashlib.sha256(seed_path.read_bytes()).hexdigest(),
              "wall_seconds": time.monotonic() - started, "summaries": sweep.summarize(records), "records": records}
    (AREA / "confirmation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summaries"], indent=2), flush=True)


if __name__ == "__main__":
    main()
