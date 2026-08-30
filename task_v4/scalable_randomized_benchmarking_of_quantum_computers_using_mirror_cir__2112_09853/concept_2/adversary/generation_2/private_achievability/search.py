import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

AREA = Path(__file__).resolve().parent
sys.path.insert(0, str(AREA.parent))
import frozen_model as model
from private_transport import launch_command, run_episode


def create_file(path, content):
    if path.exists():
        assert path.read_text() == content, path
        return
    relative = str(path.relative_to(AREA))
    patch = "*** Begin Patch\n*** Add File: " + relative + "\n"
    patch += "".join("+" + line + "\n" for line in content.splitlines())
    subprocess.run(["apply_patch", patch + "*** End Patch\n"], cwd=AREA, check=True, stdout=subprocess.DEVNULL)


def execute(job):
    model.LIMITS["shots_budget"] = 12000
    directory = AREA / "runs" / job["label"] / job["id"]
    directory.mkdir(parents=True, exist_ok=False)
    artifact = AREA / "policies" / job["variant"]
    episode = model.Episode(int(job["seed_hex"], 16), job["family"], job["shape"])
    stderr = directory / "stderr.txt"
    record = run_episode(episode, launch_command(artifact, "policy.py", job["isolation"]), artifact, stderr)
    record.update(job)
    if not record["valid"]:
        record["stderr"] = stderr.read_text()[-4000:]
    (directory / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def summarize(records):
    summaries = []
    for variant in sorted({record["variant"] for record in records}):
        group = [record for record in records if record["variant"] == variant]
        families = {}
        for family in model.FAMILIES:
            members = [record for record in group if record["family"] == family]
            valid = bool(members) and all(record["valid"] for record in members)
            mse = sum(record["normalized_mse"] for record in members) / len(members) if valid else None
            families[family] = {"score": 1 / (1 + mse) if valid else 0., "episodes": len(members), "normalized_mse": mse}
        average = sum(family["score"] for family in families.values()) / 4
        worst = min(family["score"] for family in families.values())
        summaries.append({"variant": variant, "episodes": len(group), "valid_episodes": sum(record["valid"] for record in group),
                          "average_score": average, "worst_family_score": worst, "families": families,
                          "quality_target_met": all(record["valid"] for record in group) and average >= .5 and worst >= 1 / 2.5625,
                          "official_pass": False, "max_cpu_seconds": max(record["cpu_seconds"] for record in group),
                          "max_wall_seconds": max(record["wall_seconds"] for record in group)})
    return sorted(summaries, key=lambda row: row["average_score"], reverse=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--seed-set", required=True)
    parser.add_argument("--replicas", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--isolation", choices=("audit", "bwrap"), default="audit")
    parser.add_argument("--variants", nargs="+")
    arguments = parser.parse_args()
    assert 1 <= arguments.workers <= 4
    settings = json.loads((AREA / "variants.json").read_text())
    variants = arguments.variants or list(settings)
    for variant in variants:
        directory = AREA / "policies" / variant
        directory.mkdir(parents=True, exist_ok=True)
        source = AREA.parent / "budget_policy.py" if variant == "adapted_champion" else AREA / "policy.py"
        create_file(directory / "policy.py", source.read_text())
        create_file(directory / "champion_policy.py", (AREA.parent / "champion_policy.py").read_text())
        create_file(directory / "settings.json", json.dumps(settings[variant], indent=2) + "\n")
        if variant == "adapted_champion":
            create_file(directory / "allocation.json", json.dumps({"pair_shots_minimum": 64, "thin_controls": True}) + "\n")
    seed_path = AREA / ("cases_" + arguments.seed_set + ".json")
    if seed_path.exists():
        cases = json.loads(seed_path.read_text())
    else:
        cases = [{"family": family, "shape": list(shape), "replica": replica, "seed_hex": secrets.token_hex(16)}
                 for family in model.FAMILIES for shape in model.SHAPES for replica in range(arguments.replicas)]
        seed_path.write_text(json.dumps(cases, indent=2) + "\n")
    jobs = [dict(case, variant=variant, label=arguments.label, isolation=arguments.isolation,
                 id=variant + "_" + str(case_index)) for variant in variants for case_index, case in enumerate(cases)]
    started = time.monotonic()
    records = []
    with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        futures = [executor.submit(execute, job) for job in jobs]
        for future in as_completed(futures):
            records.append(future.result())
            if len(records) % 12 == 0:
                print(json.dumps({"completed": len(records), "total": len(jobs)}), flush=True)
    report = {"budget": 12000, "isolation": arguments.isolation,
              "seed_manifest_sha256": hashlib.sha256(seed_path.read_bytes()).hexdigest(),
              "wall_seconds": time.monotonic() - started, "summaries": summarize(records), "records": records}
    (AREA / (arguments.label + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summaries"], indent=2), flush=True)


if __name__ == "__main__":
    main()
