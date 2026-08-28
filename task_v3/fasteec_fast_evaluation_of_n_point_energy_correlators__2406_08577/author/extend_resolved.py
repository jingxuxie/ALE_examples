import json
import subprocess
import sys

from build_pilots import AUTHOR, ROOT, SPECS, queries, reference


pilot = ROOT / "pilots" / "resolved"
participant = pilot / "participant"
(participant / "TASK.md").write_text("# Mission\n\n" + SPECS["resolved"] + "\n")
sample_file = participant / "input" / "sample.json"
sample = json.loads(sample_file.read_text())
sample["queries"] = queries("resolved")
sample_file.write_text(json.dumps(sample, indent=2))
subprocess.run([sys.executable, str(AUTHOR / "build_pilots.py"), "refresh", "--kind", "resolved"], check=True)
manifest = json.loads((pilot / "private" / "challenge_pool" / "manifest.json").read_text())
for case in manifest["cases"]:
    if case["id"] == "pilot_full_sample_scale":
        continue
    job_file = pilot / "private" / "challenge_pool" / case["id"] / "job.json"
    job = json.loads(job_file.read_text())
    job["queries"] = queries("resolved")
    job_file.write_text(json.dumps(job, indent=2))
for split in ["pilot", "pool", "heldout"]:
    for case in manifest["cases"]:
        if case["id"] != "pilot_full_sample_scale" and case["split"] == split:
            reference("resolved", case["id"])
