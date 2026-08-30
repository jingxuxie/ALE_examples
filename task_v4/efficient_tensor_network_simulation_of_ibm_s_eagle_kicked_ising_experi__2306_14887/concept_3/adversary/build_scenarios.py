"""Builder-only deterministic scenario construction, never participant input."""

import itertools
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def entry(name, family, gain_a=0.0, gain_b=0.0, zz_common=0.0, local=None):
    return {"name": name, "family": family, "gain_a": float(gain_a), "gain_b": float(gain_b),
            "zz_common": float(zz_common),
            "zz_local": [0.0] * 12 if local is None else np.asarray(local).tolist()}


def main():
    public = [entry("nominal", "training")]
    for axis in range(3):
        for sign in (-1, 1):
            values = [0.0, 0.0, 0.0]
            values[axis] = sign * (0.025 if axis < 2 else 0.015)
            public.append(entry(f"axis_{axis}_{sign}", "training", *values))
    for index, signs in enumerate(itertools.product((-1, 1), repeat=3)):
        public.append(entry(f"interior_{index}", "training", signs[0] * 0.018,
                            signs[1] * 0.018, signs[2] * 0.010))
    (ROOT / "participant" / "input" / "training_scenarios.json").write_text(json.dumps({"scenarios": public}, indent=2) + "\n")
    private = [entry("nominal", "core")]
    for index, public_entry in enumerate(public[1:7]):
        private.append(dict(public_entry, name=f"axis_{index}", family="core"))
    for index, signs in enumerate(itertools.product((-1, 1), repeat=3)):
        values = (signs[0] * 0.025, signs[1] * 0.025, signs[2] * 0.015)
        private.append(entry(f"corner_{index}", "core", *values))
        patterns = [np.full(12, signs[2]), (-1.0) ** np.arange(12),
                    np.cos(2 * np.pi * np.arange(12) / 12 + index * np.pi / 4)]
        for pattern_index, pattern in enumerate(patterns):
            private.append(entry(f"stress_{index}_{pattern_index}", "worst_family", *values,
                                 local=0.005 * pattern))
    generator = np.random.default_rng(914887031)
    for index in range(24):
        gains = generator.uniform(-1, 1, 3) * [0.025, 0.025, 0.015]
        local = generator.uniform(-0.005, 0.005, 12)
        private.append(entry(f"heldout_{index}", "heldout", *gains, local=local))
    (ROOT / "evaluator" / "hidden" / "scenarios.json").parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "evaluator" / "hidden" / "scenarios.json").write_text(json.dumps({"scenarios": private}, indent=2) + "\n")
    print(json.dumps({"public": len(public), "private": len(private)}))


if __name__ == "__main__":
    main()
