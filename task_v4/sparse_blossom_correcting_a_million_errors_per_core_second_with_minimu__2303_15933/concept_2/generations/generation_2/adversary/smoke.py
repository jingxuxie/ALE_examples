import sys

sys.dont_write_bytecode = True

import importlib.util
import json
from pathlib import Path
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    specification = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main():
    public = load("public_smoke", "participant/workspace/check.py")
    hidden = load("hidden_smoke", "evaluator/hidden/oracle.py")
    for label, relative in (("known", "adversary/known_witness.json"), ("baseline", "participant/baseline/champion.json")):
        artifact = hidden.read_artifact(ROOT / relative)
        public_groups = public.calibrations(artifact)
        private_groups = hidden.schedule(artifact["probabilities"])
        assert [group["id"] for group in public_groups] == [group["id"] for group in private_groups]
        for first, second in zip(public_groups, private_groups):
            np.testing.assert_allclose(first["probabilities"], second["rates"], rtol=1e-14, atol=1e-16)
            assert abs(first["derivative_bound"] - second["derivative"]) < 1e-12
        sample = np.concatenate([group["rates"][[0, len(group["rates"]) // 2, -1]] for group in private_groups[::11]])
        started = time.monotonic()
        native = hidden.native_many(sample, hidden.edge_masks(), 20, sum(1 << detector for detector in artifact["syndrome"]))
        for rates, result in zip(sample, native):
            frontier = public.frontier(rates, artifact["syndrome"])
            np.testing.assert_allclose(result[:2], frontier[0], rtol=3e-12, atol=0)
            np.testing.assert_allclose(result[2:], frontier[1], rtol=3e-12, atol=1e-12)
        print(label, "native_seconds_per_point", (time.monotonic() - started) / len(sample), flush=True)
        result = public.check(artifact)
        assert result["passed"] == (label == "known")
        (ROOT / f"adversary/{label}_public_metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        if label == "baseline":
            (ROOT / "participant/baseline/metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        print(label, json.dumps({key: value for key, value in result.items() if key != "groups"}), flush=True)


if __name__ == "__main__":
    main()
