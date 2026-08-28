import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/"private"))
from evaluator import baseline, score, summarize


def main():
    manifest=json.loads((ROOT/"private/challenge_pool/manifest.json").read_text())
    reports={"baseline":{},"strong_reference":{}}
    reference_seeds=set()
    strong_seeds=set()
    for path in (ROOT/"private/reference/raw").glob("*.npz"):
        with np.load(path,allow_pickle=False) as data:
            (strong_seeds if "_strong_" in path.name else reference_seeds).add(int(data["seed"]))
    assert not reference_seeds.intersection(strong_seeds)
    for split,entries in manifest.items():
        results={"baseline":[],"strong_reference":[]}
        for entry in entries:
            case=json.loads((ROOT/entry["path"]).read_text())
            assert hashlib.sha256((ROOT/entry["path"]).read_bytes()).hexdigest()==entry["sha256"]
            reference=json.loads((ROOT/"private/reference/results"/(entry["id"]+".json")).read_text())
            started=time.monotonic()
            weak=baseline(case)
            weak_seconds=time.monotonic()-started
            strong=json.loads((ROOT/"private/reference/strong_results"/(entry["id"]+".json")).read_text())
            seconds=sum(float(np.load(path,allow_pickle=False)["seconds"])
                        for path in (ROOT/"private/reference/raw").glob(entry["id"]+"_strong_*.npz"))
            for label,prediction,runtime in [("baseline",weak,weak_seconds),("strong_reference",strong,seconds)]:
                quality,components=score(case,reference,prediction)
                results[label].append({"id":entry["id"],"family":entry["family"],"score":quality,
                                       "components":components,"runtime_seconds":runtime,"status":"ok"})
        for label,values in results.items():
            report=summarize(values,split)
            report.pop("sandbox")
            report["execution"]="Trusted offline calibration, not an untrusted-submission sandbox run"
            reports[label][split]=report
    reports["strong_reference"]["independence"]={"reference_seed_count":len(reference_seeds),
        "strong_seed_count":len(strong_seeds),"shared_seeds":0,
        "description":"Separate two-chain official CMC trajectories; no gold lookup; four-mode integration versus seven-mode, 17-angle gold integration"}
    reports["strong_reference"]["runtime_note"]="Sum of measured native subprocess wall times under concurrent authoring load; excludes Python assembly and compilation. Not cached-read latency."
    cli_path=ROOT/"private/baseline_cli_initial.json"
    if cli_path.exists():
        actual=json.loads(cli_path.read_text())
        assert abs(actual["mean_score"]-reports["baseline"]["initial"]["mean_score"])<1e-8
        reports["baseline"]["initial"]=actual
    reports["baseline"]["runtime_note"]="Initial split is an actual isolated CLI run when baseline_cli_initial.json exists; challenge and confirmation are trusted formula-only calibration timings."
    for label,report in reports.items():
        (ROOT/"private"/(label+"_scores.json")).write_text(json.dumps(report,indent=2)+"\n")
    for label,report in reports.items():
        print(label,{split:{key:report[split][key] for key in ["mean_score","worst_family_score","runtime_seconds"]}
                     for split in manifest},flush=True)


if __name__ == "__main__":
    main()
