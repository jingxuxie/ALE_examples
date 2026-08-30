import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from replay_champion import PENDING, POOL, evaluate_artifact, prepare_adapter, replay

sys.path.insert(0, str(POOL))
from pool_common import json_write, load_instance, read_artifact


def run_candidate(directory, adapter):
    instance = load_instance(directory / "input")
    private = json.loads((directory / "audit.json").read_text())
    name = directory.name
    record_folder = PENDING / "family_oracle" / name
    record_folder.mkdir(parents=True, exist_ok=True)
    records = []
    endpoints = []
    for family in instance["config"]["families"]:
        replay_name = "oracle_" + name + "__" + family["name"]
        result = replay(replay_name, directory / "input", private["score"], adapter, family["name"])
        records.append(result)
        replay_directory = PENDING / "champion_replays" / replay_name
        for stage, filename in (("coarse", "witness.npz"), ("refinement", "refined.npz")):
            audit_path = replay_directory / (stage + ".audit.json")
            if not audit_path.exists():
                continue
            audit = json.loads(audit_path.read_text())
            if not audit.get("admissible") or "physics" not in audit:
                continue
            kernels = read_artifact(replay_directory / "output" / filename, instance["config"])
            temperatures = np.array([[grid["transitions"][index]["tc_kelvin"] for spectral_family in audit["physics"]["families"] for grid in spectral_family["grids"]] for index in range(2)])
            for index in range(2):
                endpoints.append({"kernel": kernels[index], "temperatures": temperatures[index], "origin": [family["name"], stage, index]})
    if not endpoints:
        summary = {"name": name, "genuine_failure": False, "reason": "No completed admissible search; infrastructure failures are not ratchet evidence."}
    else:
        temperatures = np.array([endpoint["temperatures"] for endpoint in endpoints])
        scores = np.min(temperatures[:, None, :] / temperatures[None, :, :], axis=2)
        high, low = np.unravel_index(np.argmax(scores), scores.shape)
        pair = np.stack([endpoints[high]["kernel"], endpoints[low]["kernel"]])
        artifact = record_folder / "best_combined_witness.npz"
        with artifact.open("wb") as stream:
            np.savez_compressed(stream, kernels=pair)
        audited = evaluate_artifact(artifact, instance, {"search_family_settings": records, "endpoint_combination_oracle": True})
        json_write(record_folder / "best_combined_audit.json", audited)
        score = audited["score"]
        summary = {
            "name": name, "private_score": private["score"], "target_ratio": instance["config"]["target_ratio"],
            "champion_oracle_score": score, "champion_oracle_valid": audited["valid"], "admissible": audited["admissible"],
            "private_minus_champion": private["score"] - score,
            "genuine_failure": bool(audited["admissible"] and not audited["valid"] and private["valid"]),
            "reason": audited["reason"], "family_replays": len(records), "endpoint_count": len(endpoints),
            "selected_high_origin": endpoints[high]["origin"], "selected_low_origin": endpoints[low]["origin"],
            "algorithm_unchanged": True, "only_public_family_argument_varied": True,
            "success_threshold_handling": "v2 has no literal success-ratio stop. The per-instance target is supplied through config.json; mathematical stationarity tolerances and all search iteration counts are unchanged.",
            "stronger_than_recorded_champion": "Every public family setting is searched, followed by its recorded refinement; all produced endpoints can be combined. A stale default family or target cannot explain a remaining failure.",
        }
    json_write(record_folder / "summary.json", summary)
    print(json.dumps(summary), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidates", nargs="*")
    arguments = parser.parse_args()
    adapter = prepare_adapter()
    directories = [Path(name).resolve() for name in arguments.candidates] if arguments.candidates else sorted((PENDING / "robustness_exploration" / "candidates").glob("*"))
    results = []
    for directory in directories:
        if PENDING not in directory.parents:
            raise ValueError("candidate must be inside pending generation_1")
        private = json.loads((directory / "audit.json").read_text())
        print(json.dumps({"screening": directory.name, "private_score": private["score"], "private_family_minima": {family["name"]: min(grid["ordered_ratio"] for grid in family["grids"]) for family in private["physics"]["families"]}}), flush=True)
        results.append(run_candidate(directory, adapter))
    json_write(PENDING / "family_oracle_summary.json", {"results": results, "new_fresh_launches": 0, "active_package_unchanged": True})


if __name__ == "__main__":
    main()
