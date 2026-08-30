import concurrent.futures
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1] / "concept_3"
GENERATION = ROOT / "generations/generation_2"
sys.path.insert(0, str(GENERATION / "evaluator/hidden"))
from exact import assess


def evaluate(job):
    name, scale, witness, protocol = job
    candidate = {**witness, "fields": [value * scale for value in witness["fields"]]}
    try:
        result = assess(candidate, protocol)
        margin = min(result["core"] / 0.06, result["worst_family"] / 0.05,
                     result["base"]["signed_difference"] / 0.055,
                     min(row["above_member_floor"] / 24 for row in result["families"]))
    except ValueError as error:
        result = {"valid": False, "pass": False, "reason": str(error)}
        margin = -100.0
    return {"source": name, "scale": scale, "witness": candidate, "margin": margin, "result": result}


def main():
    protocol = json.loads((GENERATION / "evaluator/hidden/protocol.json").read_text())
    sources = {"private_g1": ROOT / "adversary/champions/witness.json",
               "fresh_g1_v1": ROOT / "attempts/v_1/witness.json",
               "fresh_g1_v2": ROOT / "attempts/v_2/witness.json"}
    scales = [0.82 + 0.04 * index for index in range(10)]
    jobs = [(name, scale, json.loads(path.read_text()), protocol) for name, path in sources.items() for scale in scales]
    started = time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(evaluate, jobs))
    best = max(results, key=lambda result: result["margin"])
    destination = GENERATION / "adversary/scale_candidate"
    destination.mkdir(exist_ok=True)
    (destination / "witness.json").write_text(json.dumps(best["witness"], indent=2) + "\n")
    report = {"tested": len(results), "passing_candidates": sum(row["result"]["pass"] for row in results),
              "best": best, "records": results, "seconds": time.monotonic() - started,
              "purpose": "Privileged achievability search on the already-frozen generation2; no public files or targets changed"}
    (GENERATION / "adversary/scale_search.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"tested": report["tested"], "passing": report["passing_candidates"], "best_margin": best["margin"],
                      "source": best["source"], "scale": best["scale"], "seconds": report["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
