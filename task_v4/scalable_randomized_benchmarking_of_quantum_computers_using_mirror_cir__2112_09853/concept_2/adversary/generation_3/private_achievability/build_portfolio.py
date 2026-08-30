from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


AREA = Path(__file__).resolve().parent


def main():
    target = AREA / "policies" / "family_portfolio"
    target.mkdir(exist_ok=False)
    for filename in ("policy.py", "champion_policy.py", "settings.json"):
        shutil.copyfile(AREA / "policies/count_batch8" / filename, target / filename)
    shutil.copyfile(AREA / "sampler.cpp", target / "sampler.cpp")
    subprocess.run(["g++", "-O3", "-std=c++17", "-shared", "-fPIC", "-DCOUNT_PRIOR",
                    "-DUNIFORM_SPAM", "-DDISTANT_SPAM", str(target / "sampler.cpp"),
                    "-o", str(target / "sampler.so")], check=True)
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
              for path in target.iterdir() if path.is_file()}
    selection = dict(selected_utc=datetime.now(timezone.utc).isoformat(), variant="family_portfolio",
                     policy_files_sha256=hashes, selection_basis="Exploration only, before independent confirmation.",
                     family_rules={"distant_pairs": "count_uniform_batch8", "other": "count_batch8"},
                     exploratory_average=.47706736608309524,
                     note="Family labels are disclosed in hello. No instance parameters, hidden seeds or hidden test results are consulted by this policy.")
    (AREA / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    records = json.loads((AREA / "policy_hashes.json").read_text())
    records["family_portfolio"] = hashes
    (AREA / "policy_hashes.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
