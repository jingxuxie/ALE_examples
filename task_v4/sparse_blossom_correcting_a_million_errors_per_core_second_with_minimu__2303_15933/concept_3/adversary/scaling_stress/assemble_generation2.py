import sys

sys.dont_write_bytecode = True

import datetime
import hashlib
import json
import secrets
import subprocess
from pathlib import Path

from cases import cases
from run import check_frozen


SIDE = Path(__file__).resolve().parent
ORIGINAL = SIDE.parents[1]
ROOT = ORIGINAL / "generations/generation_2"


def write_code(relative, contents):
    destination = ROOT / relative
    if destination.exists():
        raise RuntimeError("Refusing to overwrite " + str(destination))
    patch = "*** Begin Patch\n*** Add File: " + str(destination) + "\n"
    patch += "".join("+" + line + "\n" for line in contents.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True, stdout=subprocess.DEVNULL)


def main():
    check_frozen()
    if ROOT.exists():
        raise RuntimeError("Generation already exists; frozen fixtures must not be regenerated")
    for directory in ("participant/input", "participant/workspace", "participant/baseline", "evaluator/hidden",
                      "attempts", "champions", "adversary/portfolio", "adversary/validation"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    precommit = json.loads((SIDE / "GEN2_TARGET_PRECOMMIT.json").read_text())
    targets = {key: value for key, value in precommit.items() if key not in ("stage", "status", "recorded_utc")}
    targets.update({"version": "efficient-active-calibration-generation-2", "generation": 2,
                    "date": "2026-08-28", "regimes": ["chain_hooks", "patch_crosstalk", "burst_aliases"],
                    "episodes_per_regime": 4, "frozen_before_portfolio_and_fresh": True,
                    "precommit_sha256": hashlib.sha256((SIDE / "GEN2_TARGET_PRECOMMIT.json").read_bytes()).hexdigest(),
                    "metric": "Equal-weight RMS log error within each episode/family, RMS over four episodes in each regime/family, then mean and maximum of the 12 cells."})
    for relative in ("participant/input/targets.json", "evaluator/hidden/targets.json"):
        (ROOT / relative).write_text(json.dumps(targets, indent=2) + "\n")
    seeds = {name: secrets.randbits(63) for name in ("private", "training")}
    for split in ("private", "training"):
        episodes = list(cases(seed=seeds[split], sizes=(14, 16, 18, 20) if split == "private" else (14, 18)))
        for episode in episodes:
            episode["rates"] = episode["rates"].tolist()
            episode["spec"]["protocol"] = "efficient-detector-calibration-v2"
            episode["id"] = split + "_" + episode["id"]
        relative = "evaluator/hidden/episodes.json" if split == "private" else "participant/input/training.json"
        (ROOT / relative).write_text(json.dumps({"episodes": episodes}, indent=2) + "\n")
    (ROOT / "evaluator/hidden/generation_seeds.json").write_text(json.dumps(seeds, indent=2) + "\n")
    write_code("evaluator/hidden/case_factory.py", (SIDE / "cases.py").read_text())
    sampler = '''import numpy as np


def sample_events(spec, rates, action_id, shots, rng):
    action = spec["actions"][action_id]
    modes = rng.choice(len(action["mode_weights"]), shots, p=action["mode_weights"])
    exposures = np.asarray(action["exposures"])
    syndromes = np.zeros(shots, dtype=np.int64)
    for index, channel in enumerate(spec["channels"]):
        intensity = exposures[modes, index] * rates[index]
        fired = rng.random(shots) < -0.5 * np.expm1(-2.0 * intensity)
        alternate = rng.random(shots) < action["alternate_probability"][index]
        footprint = np.where(alternate, channel["masks"][1], channel["masks"][0])
        syndromes ^= np.where(fired, footprint, 0)
    return np.unique(syndromes, return_counts=True)
'''
    write_code("evaluator/hidden/simulator.py", sampler)
    write_code("participant/input/simulator.py", sampler)
    write_code("evaluator/hidden/worker_supervisor.py", (ORIGINAL / "evaluator/hidden/worker_supervisor.py").read_text())
    evaluator = (ORIGINAL / "evaluator/evaluate.py").read_text()
    evaluator = evaluator.replace("inside concept_3", "inside this generation root")
    evaluator = evaluator.replace("counts = sample_events(spec, rates, action, shots, rng)",
                                  "syndromes, multiplicities = sample_events(spec, rates, action, shots, rng)")
    evaluator = evaluator.replace('"counts": counts.tolist(), "shots_remaining":',
                                  '"encoding": "sparse_histogram_v1", "syndromes": syndromes.tolist(),\n                            "multiplicities": multiplicities.tolist(), "shots_remaining":')
    write_code("evaluator/evaluate.py", evaluator)
    write_code("participant/baseline/previous_champion.py", (ORIGINAL / "attempts/v_2_frozen_submission/solution.py").read_text())
    write_code("participant/input/legacy_bridge.py", (SIDE / "worker_support/legacy_bridge.py").read_text())
    write_code("adversary/portfolio/local_model.py", (SIDE / "worker_support/local_model.py").read_text())
    policy = (SIDE / "workers/active/solution.py").read_text().replace('sys.path.insert(0, "/stress_public")',
                         'sys.path.insert(0, str(Path(__file__).resolve().parent))')
    write_code("adversary/portfolio/solution.py", policy)
    manifest = {"generation": 2, "frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "targets_sha256": hashlib.sha256((ROOT / "evaluator/hidden/targets.json").read_bytes()).hexdigest(),
                "episodes_sha256": hashlib.sha256((ROOT / "evaluator/hidden/episodes.json").read_bytes()).hexdigest(),
                "precommit_sha256": targets["precommit_sha256"], "fresh_launches": 0,
                "no_parameter_filtering": True, "source_champion_sha256": hashlib.sha256((ROOT / "participant/baseline/previous_champion.py").read_bytes()).hexdigest()}
    (ROOT / "evaluator/hidden/freeze.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "adversary/target_precommit.json").write_bytes((SIDE / "GEN2_TARGET_PRECOMMIT.json").read_bytes())
    check_frozen()
    print(json.dumps(manifest), flush=True)


if __name__ == "__main__":
    main()
