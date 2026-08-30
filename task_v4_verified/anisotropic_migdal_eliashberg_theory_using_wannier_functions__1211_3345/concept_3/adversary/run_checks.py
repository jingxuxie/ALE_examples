import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import evaluate, score, target_configuration


def main():
    candidate = ROOT / "adversary" / "probe"
    outcomes = {}
    for mode in ("valid", "private_read", "clone3", "thread", "network", "exec", "header_bomb", "symlink", "fifo", "missing", "exit", "nan", "inf", "shape",
                 "normalization", "negative", "object", "complex", "oversized", "spoof", "extra_key"):
        settings = dict(mode=mode, private_path=str(ROOT / "evaluator" / "hidden" / "test_labels.npz"))
        (candidate / "settings.json").write_text(json.dumps(settings))
        result = evaluate(candidate, "validation")
        expected_valid = mode in ("valid", "private_read", "clone3", "thread", "network", "exec")
        outcomes[mode] = dict(expected_valid=expected_valid, result=result,
                              check_passed=result["valid"] == expected_valid)
        print(mode, outcomes[mode]["check_passed"], flush=True)
    configuration, target_hash = target_configuration()
    with np.load(ROOT / "evaluator" / "hidden" / "test_labels.npz", allow_pickle=False) as labels:
        sanity = score(labels["spectral_mass"], labels["spectral_mass"], labels["family"], configuration)
        permuted = labels["spectral_mass"].copy()
        for index in range(len(permuted)):
            count = int(np.sum(permuted[index].sum(axis=-1) > .5))
            permuted[index, :count] = permuted[index, :count][::-1]
        permutation_sanity = score(permuted, labels["spectral_mass"], labels["family"], configuration)
    report = dict(target_sha256=target_hash, checks=outcomes,
                  label_replay_scorer_sanity_only=sanity,
                  permutation_invariance_scorer_sanity_only=permutation_sanity,
                  all_passed=all(item["check_passed"] for item in outcomes.values()) and sanity["core"] == 0 and permutation_sanity["core"] == 0)
    (ROOT / "adversary" / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    if not report["all_passed"]:
        raise RuntimeError("adversarial checks failed")


if __name__ == "__main__":
    main()
