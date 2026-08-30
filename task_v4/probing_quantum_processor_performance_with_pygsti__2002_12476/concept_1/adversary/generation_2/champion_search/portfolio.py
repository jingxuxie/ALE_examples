import hashlib
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from metrics import Benchmark, HERE, ROOT, write_json


def main():
    started = time.monotonic()
    benchmark = Benchmark()
    benchmark.freeze()
    paths = [HERE / "champion_design.json", ROOT / "adversary/portfolio/design.json",
             ROOT / "adversary/portfolio/resilience/best_double.json",
             ROOT / "adversary/portfolio/resilience/single_design.json",
             ROOT / "adversary/portfolio/resilience/double_design.json",
             ROOT / "adversary/portfolio/resilience_champion_1/design.json",
             ROOT / "adversary/portfolio/resilience_champion_1/robust_design.json"]
    scores, best, best_key = {}, None, float("inf")
    for path in paths:
        counts = np.array(json.loads(path.read_text())["batches"])
        score = benchmark.evaluate(counts, direct=True)
        label = str(path.relative_to(ROOT))
        scores[label] = score
        key = np.log(max(1, 1 / score["core_score"])) + np.log(max(1, 1 / score["worst_family_score"])) + 30 * max(0, score["intact_mean_ratio"] - 1.2)
        if key < best_key:
            best, best_key = counts, key
            write_json(HERE / "design.json", {"batches": counts.tolist()})
            write_json(HERE / "score.json", score)
        print(json.dumps(dict(event="portfolio", source=label, core=score["core_score"], worst=score["worst_family_score"],
                              intact_ratio=score["intact_mean_ratio"], passed=score["passed"],
                              elapsed=time.monotonic() - started)), flush=True)
    write_json(HERE / "usability_portfolio_scores.json", scores)
    protected = [ROOT / "champions/generation_2/design.json", ROOT / "participant/input/contract.json",
                 ROOT / "participant/input/candidates.json", ROOT / "participant/workspace/physics.py",
                 ROOT / "participant/TASK.md", ROOT / "evaluator/evaluate.py", ROOT / "evaluator/hidden/benchmark.npz"]
    protected += paths[1:]
    write_json(HERE / "protected_hashes.json", {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected})


if __name__ == "__main__":
    main()
