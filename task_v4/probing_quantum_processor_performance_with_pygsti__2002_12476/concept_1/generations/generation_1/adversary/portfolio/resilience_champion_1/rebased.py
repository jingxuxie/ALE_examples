import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / "resilience"
CHAMPION = ROOT / "champions/generation_1/design.json"
sys.path.insert(0, str(OLD))
from metrics import profile, score_profiles

TARGETS = {"overall_two_loss_reduction": 0.50, "every_family_two_loss_reduction": 0.30,
           "intact_mean_ratio_limit": 1.20}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


class Benchmark:
    def __init__(self):
        self.contract = json.loads((ROOT / "participant/input/contract.json").read_text())
        self.candidates = json.loads((ROOT / "participant/input/candidates.json").read_text())
        self.reference_counts = np.array(json.loads(CHAMPION.read_text())["batches"])
        self.champion_hash = hashlib.sha256(CHAMPION.read_bytes()).hexdigest()
        with np.load(ROOT / "evaluator/hidden/benchmark.npz", allow_pickle=False) as source:
            self.features = source["features"].copy()
            self.parameters = source["parameters"].copy()
            self.families = source["families"].copy()
            self.costs = source["costs"].copy()
        self.reference = profile(self.features, self.reference_counts, direct=True)

    def validate(self, counts):
        if counts.shape != self.costs.shape or not np.all(np.isfinite(counts)):
            raise ValueError("incorrect or nonfinite batch vector")
        if np.any(counts != np.floor(counts)) or np.any(counts < 0) or np.any(counts > 48):
            raise ValueError("invalid integral batches")
        distinct = int(np.count_nonzero(counts))
        if not 3 <= distinct <= self.contract["max_distinct_circuits"]:
            raise ValueError("invalid support size")
        cost = int(counts @ self.costs + distinct * self.contract["setup_ticks"])
        if cost > self.contract["execution_budget_ticks"]:
            raise ValueError("execution budget exceeded")
        return cost, distinct

    def evaluate(self, counts, direct=True):
        cost, distinct = self.validate(counts)
        candidate = profile(self.features, counts, direct=direct)
        result = score_profiles(candidate, self.reference, self.families)
        result.update(valid=True, core_score=result["double"]["core_score"],
                      worst_family_score=result["double"]["worst_family_score"],
                      passed=result["double"]["passed"], execution_ticks=cost,
                      distinct_circuits=distinct, total_batches=int(counts.sum()),
                      runtime_resource_score=1 - cost / self.contract["execution_budget_ticks"],
                      targets=TARGETS, reference_design_sha256=self.champion_hash,
                      every_loss_directly_inverted=direct,
                      worst_loss_taken_separately_at_each_operating_point=True)
        result["reason"] = "all fixed two-loss targets and intact guard met" if result["passed"] else "one or more fixed two-loss targets or intact guard unmet"
        return result

    def freeze(self):
        frozen = dict(targets=TARGETS, resource_contract=self.contract,
                      reference_design_sha256=self.champion_hash,
                      benchmark_sha256=hashlib.sha256((ROOT / "evaluator/hidden/benchmark.npz").read_bytes()).hexdigest(),
                      private_feasibility_only=True, fresh_submissions_read=False,
                      authorized_champion_only=str(CHAMPION.relative_to(ROOT)),
                      objective="mean of each operating point's maximum A-risk over all selected-circuit pairs removed entirely; no reallocation")
        path = HERE / "contract.json"
        if path.exists() and json.loads(path.read_text()) != frozen:
            raise ValueError("frozen private contract mismatch")
        if not path.exists():
            write_json(path, frozen)
            (HERE / "reference_design.json").write_bytes(CHAMPION.read_bytes())
            write_json(HERE / "reference_scores.json", self.evaluate(self.reference_counts))
            protected = [CHAMPION, ROOT / "participant/TASK.md", ROOT / "participant/input/contract.json",
                         ROOT / "participant/input/candidates.json", ROOT / "participant/workspace/physics.py",
                         ROOT / "evaluator/evaluate.py", ROOT / "evaluator/hidden/benchmark.npz",
                         HERE.parent / "design.json"]
            protected += sorted(path for path in OLD.rglob("*") if path.is_file())
            write_json(HERE / "protected_hashes.json", {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission")
    parser.add_argument("--output")
    args = parser.parse_args()
    data = Benchmark()
    data.freeze()
    counts = data.reference_counts
    if args.submission:
        artifact = json.loads(Path(args.submission).read_text())
        if set(artifact) != {"batches"} or any(type(value) is not int for value in artifact["batches"]):
            raise ValueError("expected an integral batches vector only")
        counts = np.array(artifact["batches"])
    score = data.evaluate(counts, direct=True)
    if args.output:
        path = Path(args.output).resolve()
        if HERE not in path.parents:
            raise ValueError("outputs must stay within private scope")
        write_json(path, score)
    print(json.dumps(score, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
