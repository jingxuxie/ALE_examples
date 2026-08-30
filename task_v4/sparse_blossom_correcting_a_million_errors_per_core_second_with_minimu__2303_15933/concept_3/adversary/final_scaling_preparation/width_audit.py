import sys

sys.dont_write_bytecode = True

import json
from pathlib import Path

import numpy as np

from cases import cases, sample
from run import check_frozen


ROOT = Path(__file__).resolve().parent


def python_integer_sampler(case, action_id, shots, rng):
    spec = case["spec"]
    action = spec["actions"][action_id]
    modes = rng.choice(2, shots, p=action["mode_weights"])
    exposure = np.array(action["exposures"])
    syndromes = [0] * shots
    for index, channel in enumerate(spec["channels"]):
        intensity = exposure[modes, index] * case["rates"][index]
        firing = rng.random(shots) < -0.5 * np.expm1(-2.0 * intensity)
        alternate = rng.random(shots) < action["alternate_probability"][index]
        for shot in np.flatnonzero(firing):
            syndromes[int(shot)] ^= int(channel["masks"][int(alternate[shot])])
    return np.unique(np.asarray(syndromes, dtype=np.int64), return_counts=True)


def main():
    check_frozen()
    results = []
    for case in cases(seed=49371023, sizes=(24, 28, 36, 44)):
        dimension = case["spec"]["detector_count"]
        direct = sample(case, 1, 4000, np.random.default_rng(17021))
        independent = python_integer_sampler(case, 1, 4000, np.random.default_rng(17021))
        assert all(np.array_equal(left, right) for left, right in zip(direct, independent))
        payload = json.dumps({"syndromes": direct[0].tolist(), "multiplicities": direct[1].tolist()})
        restored = json.loads(payload)
        assert np.array_equal(np.asarray(restored["syndromes"], dtype=np.int64), direct[0])
        clicks = [sum(count for syndrome, count in zip(restored["syndromes"], restored["multiplicities"])
                      if syndrome & (1 << detector)) for detector in range(dimension)]
        assert min(clicks) > 0 and max(restored["syndromes"]) < 1 << dimension
        if dimension > 32:
            assert max(restored["syndromes"]) >= 1 << 32
        results.append({"case": case["id"], "detectors": dimension, "integer_sampler_matches_int64": True,
                        "json_roundtrip_exact": True, "every_detector_observed_active": True,
                        "minimum_observed_clicks": min(clicks), "maximum_syndrome": max(restored["syndromes"]),
                        "maximum_syndrome_less_than_2_pow_53": max(restored["syndromes"]) < 1 << 53})
    (ROOT / "width_audit.json").write_text(json.dumps({"passed": True, "cases": results,
        "scope": "Sampler, sparse JSON, and Python/int64 handling; does not repair or excuse the actual champion's int32 casts."}, indent=2) + "\n")
    check_frozen()
    print("All twelve width/JSON/active-bit controls passed.", flush=True)


if __name__ == "__main__":
    main()
