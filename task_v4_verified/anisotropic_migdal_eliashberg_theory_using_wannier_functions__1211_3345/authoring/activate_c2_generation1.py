import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "concept_2"
PENDING = ACTIVE / "adversary/generation_1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for attempt in ("v_1", "v_2"):
        completion = ROOT / "authoring/runs/concept_2" / attempt / "evaluation_complete.json"
        if not json.loads(completion.read_text())["passed"]:
            raise RuntimeError("Original competitive attempts must be scored and solved")
    validation = json.loads((PENDING / "validation/summary.json").read_text())
    if not validation["passed"] or validation["negative_security_and_constraint_cases"] < 17:
        raise RuntimeError("Pending numerical/artifact checks must pass")
    manifest = json.loads((PENDING / "package_manifest.json").read_text())
    for key, directory in (("public", "participant"), ("trusted_evaluator", "evaluator")):
        for relative, expected in manifest[key].items():
            path = PENDING / directory / relative
            if path.is_symlink() or digest(path) != expected:
                raise RuntimeError("Pending seal mismatch: " + str(path))
    for path in (PENDING / "participant").rglob("*.py"):
        if digest(path) != digest(ACTIVE / "participant" / path.relative_to(PENDING / "participant")):
            raise RuntimeError("Public starting code changed")
    backup = PENDING / "activation_previous"
    backup.mkdir(exist_ok=False)
    shutil.copy2(ACTIVE / "status.json", backup / "status.json")
    for name in ("participant", "evaluator"):
        (ACTIVE / name).rename(backup / name)
        shutil.copytree(PENDING / name, ACTIVE / name)
    old_text = (ACTIVE / "status.json").read_text()
    status = {
        "concept": "concept_2", "generation": 1, "ratchet_index": 1, "ratchet_limit": 3,
        "verification_mode": "B_COUNTEREXAMPLE", "active": True,
        "status": "ready_for_fresh_challengers", "target_ratio": 1.09,
        "baseline_score": validation["baseline"]["score"],
        "previous_champion_oracle_score": validation["champion_oracle"]["score"],
        "private_witness_score": validation["private_witness"]["score"],
        "known_passing_witness": True, "prior_fresh_code_public": False,
        "input_sha256": manifest["input_sha256"],
        "target_fixed_before_new_challengers": True,
        "reason": "Complete the required empirical challenger step on the genuine minimax gap despite its inexpensive private repair; no hardness claim is made before fresh trials.",
        "original_generation_backup": "adversary/generation_1/activation_previous",
        "validation": "adversary/generation_1/validation/summary.json",
    }
    new_text = json.dumps(status, indent=2) + "\n"
    patch = "*** Begin Patch\n*** Update File: " + str(ACTIVE / "status.json") + "\n@@\n"
    patch += "".join("-" + line + "\n" for line in old_text.splitlines())
    patch += "".join("+" + line + "\n" for line in new_text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)
    record = dict(status, activated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  public_files_verified=len(manifest["public"]),
                  evaluator_files_verified=len(manifest["trusted_evaluator"]),
                  new_attempts=["v_3", "v_4"])
    destination = ROOT / "authoring/activation_concept_2_generation_1.json"
    destination.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
