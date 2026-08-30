import hashlib
import json
from pathlib import Path
import shutil


AREA = Path(__file__).resolve().parent


def main():
    variants = {"probability": "batch8", "count_uniform_probability": "count_uniform_batch8",
                "count_uniform_batch4": "count_uniform_batch8"}
    records = json.loads((AREA / "policy_hashes.json").read_text())
    for name, source in variants.items():
        target = AREA / "policies" / name
        target.mkdir(exist_ok=False)
        for filename in ("champion_policy.py", "sampler.cpp", "sampler.so"):
            shutil.copyfile(AREA / "policies" / source / filename, target / filename)
        shutil.copyfile(AREA / "policy.py", target / "policy.py")
        settings = dict(controls=0, initial=12, batch=4, sweeps=900, final=5000,
                        probability_design="probability" in name)
        (target / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
        records[name] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in target.iterdir() if path.is_file()}
    (AREA / "policy_hashes.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
