import argparse
import hashlib
import json
import multiprocessing
from pathlib import Path
import time

import numpy as np

from search_champion import ROOT, collect, initialize_worker, trusted_command

FAMILIES = ("strong_drive_lab", "strong_drive_target_x", "strong_drive_target_z", "strong_drive_control_x")


def draw_strong_drive(randomizer, family):
    while True:
        omega_ix = randomizer.uniform(4.45, 4.95)
        omega_iz = randomizer.uniform(2.0, 2.5)
        strength = randomizer.uniform(1.40, 1.72)
        angle = np.arctan2(omega_iz, omega_ix) + randomizer.uniform(0.12, 0.25)
        omega_zx = -strength * np.cos(angle)
        omega_zz = -strength * np.sin(angle)
        if abs(omega_zz) <= 1.08:
            break
    omega = np.array([omega_ix, omega_zx, omega_iz, omega_zz, randomizer.uniform(0.9, 1.5)])
    if family == "strong_drive_target_x":
        omega *= [1, 1, -1, -1, 1]
    elif family == "strong_drive_target_z":
        omega *= [-1, -1, 1, 1, 1]
    elif family == "strong_drive_control_x":
        omega *= [1, -1, 1, -1, -1]
    elif family != "strong_drive_lab":
        raise ValueError("unknown strong-drive family")
    nuisance = [randomizer.uniform(0.93, 0.98), randomizer.uniform(0.91, 0.95),
                randomizer.uniform(-0.025, 0.025), randomizer.uniform(0.010, 0.040)]
    return np.concatenate((omega, nuisance))


def generate_jobs(seed, episodes):
    streams = np.random.SeedSequence(seed).spawn(episodes)
    jobs = []
    for index, stream in enumerate(streams):
        parameter_stream, noise_stream = stream.spawn(2)
        family = FAMILIES[index % 4]
        parameters = draw_strong_drive(np.random.default_rng(parameter_stream), family)
        jobs.append({"case_id": f"strong_{index:04}", "family": family, "parameters": parameters.tolist(),
                     "parameter_seed": int(parameter_stream.generate_state(1, dtype=np.uint64)[0]),
                     "measurement_seed": int(noise_stream.generate_state(1, dtype=np.uint64)[0]),
                     "phase": "strong_drive_screen", "repeat_index": None})
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=64)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--seed", type=int, default=2718936719)
    arguments = parser.parse_args()
    if arguments.episodes % 4 or arguments.episodes <= 0:
        raise ValueError("balanced positive episode count required")
    output = arguments.output_dir.resolve()
    if output.exists():
        raise ValueError("refuse to overwrite screening evidence")
    command, helper = trusted_command(arguments.submission.resolve(strict=True))
    jobs = generate_jobs(arguments.seed, arguments.episodes)
    output.mkdir(parents=True)
    (output / "points.json").write_text(json.dumps(jobs, indent=2) + "\n")
    (output / "manifest.json").write_text(json.dumps({"seed": arguments.seed, "episodes": arguments.episodes,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "submission": str(arguments.submission.resolve()), "selection": "continuous neighborhood and physical Pauli-conjugate frames of repeatable broad-sweep case_00004; not selected noise seeds",
        "target_changed": False, "private_only": True}, indent=2) + "\n")
    context = multiprocessing.get_context("spawn")
    records = []
    started = time.monotonic()
    with context.Pool(arguments.jobs, initializer=initialize_worker, initargs=(command,)) as pool:
        collect(pool, jobs, output / "results.jsonl", records, started + 1800)
    valid = all(record["result"].get("valid") and not record["result"].get("infrastructure_error") for record in records)
    family_scores = {family: float(np.mean([record["result"]["nrmse"] for record in records if record["family"] == family])) for family in FAMILIES} if valid else {}
    report = {"valid": valid, "episodes": len(records), "core_score": float(np.mean([record["result"]["nrmse"] for record in records])) if valid else None,
              "worst_family_score": max(family_scores.values()) if valid else None, "family_scores": family_scores,
              "wall_seconds": time.monotonic() - started, "purpose": "Independent neighborhood confirmation before any new task generation; no participant changes"}
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
