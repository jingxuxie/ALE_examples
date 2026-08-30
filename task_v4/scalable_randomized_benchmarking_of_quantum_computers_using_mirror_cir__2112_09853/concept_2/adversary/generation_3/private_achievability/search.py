import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time


os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
sys.path.insert(0, str(ROOT / "participant/workspace"))
import model
from transport import launch_command, run_episode


def execute(job):
    directory = AREA / "runs" / job["label"] / job["id"]
    directory.mkdir(parents=True, exist_ok=False)
    episode = model.Episode(int(job["seed_hex"], 16), job["family"], job["shape"])
    artifact = AREA / "policies" / job["variant"]
    stderr = directory / "stderr.txt"
    record = run_episode(episode, launch_command(artifact, "policy.py", job["isolation"]), artifact, stderr)
    record.update(job)
    if not record["valid"]:
        record["stderr"] = stderr.read_text()[-4000:]
    record["targets_sha256"] = hashlib.sha256(json.dumps(episode.targets).encode()).hexdigest()
    (directory / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def summarize(records):
    results = []
    for variant in sorted({record["variant"] for record in records}):
        members = [record for record in records if record["variant"] == variant]
        scores = {}
        for family in model.FAMILIES:
            cases = [record for record in members if record["family"] == family]
            scores[family] = (1 / (1 + sum(record["normalized_mse"] for record in cases) / len(cases))
                              if cases and all(record["valid"] for record in cases) else 0.)
        average = sum(scores.values()) / len(scores)
        worst = min(scores.values())
        results.append(dict(variant=variant, average_score=average, worst_family_score=worst,
                            families=scores, valid_episodes=sum(record["valid"] for record in members),
                            episodes=len(members), quality_target_met=average >= .5 and worst >= 1 / 2.5625,
                            max_cpu_seconds=max(record["cpu_seconds"] for record in members),
                            max_wall_seconds=max(record["wall_seconds"] for record in members)))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", nargs="+", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--replicas", type=int, default=1)
    parser.add_argument("--isolation", choices=("audit", "bwrap"), default="audit")
    parser.add_argument("--workers", type=int, default=4)
    arguments = parser.parse_args()
    assert 1 <= arguments.workers <= 4
    cases = [dict(family=family, shape=list(shape), replica=replica, seed_hex=secrets.token_hex(16))
             for family in model.FAMILIES for shape in model.SHAPES for replica in range(arguments.replicas)]
    seed_path = AREA / (arguments.label + "_cases.json")
    assert not seed_path.exists()
    seed_path.write_text(json.dumps(cases, indent=2) + "\n")
    jobs = [dict(case, variant=variant, isolation=arguments.isolation, label=arguments.label,
                 id=variant + "_" + str(index))
            for variant in arguments.variants for index, case in enumerate(cases)]
    started = time.monotonic()
    records = []
    with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        futures = [executor.submit(execute, job) for job in jobs]
        for future in as_completed(futures):
            records.append(future.result())
            if len(records) % 12 == 0:
                print(json.dumps(dict(completed=len(records), total=len(jobs), summaries=summarize(records))), flush=True)
    report = dict(calibration_only=arguments.isolation != "bwrap", isolation=arguments.isolation,
                  shots_budget=model.LIMITS["shots_budget"], wall_seconds=time.monotonic() - started,
                  seed_manifest_sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest(),
                  summaries=summarize(records), records=records)
    (AREA / (arguments.label + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summaries"], indent=2), flush=True)


if __name__ == "__main__":
    main()
