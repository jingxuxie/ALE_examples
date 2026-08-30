import hashlib
import json
from pathlib import Path
import shutil
import subprocess


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]


def main():
    variants = {
        "original": {"original": True, "flags": []},
        "count_original": {"original": True, "flags": ["COUNT_PRIOR"]},
        "batch8": {"flags": []},
        "count_batch8": {"flags": ["COUNT_PRIOR"]},
        "uniform_batch8": {"flags": ["UNIFORM_SPAM"]},
        "count_uniform_batch8": {"flags": ["COUNT_PRIOR", "UNIFORM_SPAM"]},
        "count_uniform_dense": {"flags": ["COUNT_PRIOR", "UNIFORM_SPAM"], "initial": 40},
    }
    records = {}
    for name, overrides in variants.items():
        target = AREA / "policies" / name
        target.mkdir(parents=True, exist_ok=False)
        settings = dict(controls=1, initial=16, batch=8, sweeps=900, final=4000)
        settings.update(overrides)
        shutil.copyfile(ROOT / "adversary/generation_3/policies/proportional/champion_policy.py",
                        target / "champion_policy.py")
        if settings.get("original"):
            shutil.copyfile(ROOT / "adversary/generation_3/policy.py", target / "policy.py")
            (target / "allocation.json").write_text('{"allocation":"proportional"}\n')
        else:
            shutil.copyfile(AREA / "policy.py", target / "policy.py")
        (target / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
        if settings["flags"]:
            shutil.copyfile(AREA / "sampler.cpp", target / "sampler.cpp")
            subprocess.run(["g++", "-O3", "-std=c++17", "-shared", "-fPIC"] +
                           ["-D" + flag for flag in settings["flags"]] +
                           [str(target / "sampler.cpp"), "-o", str(target / "sampler.so")], check=True)
        else:
            shutil.copyfile(ROOT / "champions/generation_2/sampler.cpp", target / "sampler.cpp")
            shutil.copyfile(ROOT / "champions/generation_2/sampler.so", target / "sampler.so")
        records[name] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in target.iterdir() if path.is_file()}
    (AREA / "policy_hashes.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
