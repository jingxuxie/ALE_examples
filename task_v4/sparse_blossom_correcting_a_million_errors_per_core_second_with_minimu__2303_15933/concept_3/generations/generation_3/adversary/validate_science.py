import sys

sys.dont_write_bytecode = True

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from science_helpers import validate_case
from validation_model import LocalModel
from case_factory import sample


def check_frozen():
    freeze_path = ROOT / "evaluator/hidden/freeze.json"
    if freeze_path.exists():
        frozen = json.loads(freeze_path.read_text())
        manifest = {"evaluator/hidden/targets.json": frozen["targets_sha256"],
                    "evaluator/hidden/episodes.json": frozen["episodes_sha256"]}
    else:
        manifest = json.loads((ROOT / "adversary/draft_snapshot.json").read_text())["files"]
    for relative, expected in manifest.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def main():
    check_frozen()
    module_spec = importlib.util.spec_from_file_location("trusted_generation_sampler", ROOT / "evaluator/hidden/simulator.py")
    simulator = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(simulator)
    episodes = json.loads((ROOT / "evaluator/hidden/episodes.json").read_text())["episodes"]
    results = []
    for episode in episodes:
        result = validate_case(episode, information=True)
        model = LocalModel(episode["spec"])
        truth = np.log(episode["rates"])
        for block, counts in zip(model.blocks, model.counts):
            counts[:] = model.block_distribution(truth, block) * episode["spec"]["shot_budget"] / len(episode["spec"]["actions"])
        fitted = model.fit(iterations=350)
        alternate_start = np.random.default_rng(4001).uniform(model.bounds[:, 0], model.bounds[:, 1])
        alternative = model.fit(alternate_start, iterations=350)
        result["noiseless_multistart_max_log_errors"] = [float(np.max(np.abs(fitted - truth))), float(np.max(np.abs(alternative - truth)))]
        assert max(result["noiseless_multistart_max_log_errors"]) < 0.02
        direct = simulator.sample_events(episode["spec"], episode["rates"], 3, 4000, np.random.default_rng(5209))
        control = sample(episode, 3, 4000, np.random.default_rng(5209))
        assert all(np.array_equal(left, right) for left, right in zip(direct, control))
        result["generation_sampler_matches_validated_sampler"] = True
        results.append(result)
        output = {"validation_passed": len(results) == 12, "episodes_checked": len(results), "cases": results,
                  "limitation": "Local identifiability and exact covariance-aware moment information, not a full-state Fisher calculation or a theorem of global identifiability. Noiseless multistarts are numerical diagnostics, not a passing solution.",
                  "episodes_sha256": hashlib.sha256((ROOT / "evaluator/hidden/episodes.json").read_bytes()).hexdigest()}
        (ROOT / "adversary/validation/science.json").write_text(json.dumps(output, indent=2) + "\n")
        print(json.dumps(result), flush=True)
    check_frozen()


if __name__ == "__main__":
    main()
