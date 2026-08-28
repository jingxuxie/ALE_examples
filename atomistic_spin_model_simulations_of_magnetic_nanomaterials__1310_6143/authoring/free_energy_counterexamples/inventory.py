import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PAPER=ROOT.parents[1]
PILOT=PAPER/"pilots/free_energy"


def main():
    manifest=json.loads((PILOT/"private/challenge_pool/manifest.json").read_text())
    groups={}
    splits={}
    for split,entries in manifest.items():
        local={}
        for entry in entries:
            case=json.loads((PILOT/entry["path"]).read_text())
            physical={key:case[key] for key in ["n_spins","temperature","onsite","angles"]}
            physical["bonds"]=sorted([min(first,second),max(first,second),exchange,axial]
                                      for first,second,exchange,axial in case["bonds"])
            digest=hashlib.sha256(json.dumps(physical,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            local.setdefault(digest,[]).append(entry["id"])
            groups.setdefault(digest,[]).append(entry["id"])
        splits[split]={"rows":len(entries),"distinct_physical_inputs":len(local),
                       "duplicate_groups":[names for names in local.values() if len(names)>1]}
    report={"deduplication":"Remove case_id, family, seed, shape/periodic metadata; canonicalize undirected bond ordering. No graph-isomorphism claim.",
            "splits":splits,"all_distinct_physical_inputs":len(groups),
            "cross_split_duplicates":[names for names in groups.values() if len(names)>1],
            "submission_hashes":{name:hashlib.sha256((PILOT/"attempt"/name).read_bytes()).hexdigest()
                                 for name in ["solve.py","sampler.cpp","reweight.py"]},"main_scores":{}}
    for split in ["initial","challenge"]:
        path=PAPER/"authoring/runs"/split/(f"free_energy.{split}.parallel.scores.json")
        alternate=PAPER/"authoring/runs/initial"/(f"free_energy.{split}.parallel.scores.json")
        if not path.exists() and alternate.exists():
            path=alternate
        if path.exists():
            payload=json.loads(path.read_text())
            report["main_scores"][split]={"status":"AVAILABLE","path":str(path),"payload":payload}
        else:
            report["main_scores"][split]={"status":"PENDING","path":str(path)}
    (ROOT/"inspection.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key!="submission_hashes"}),flush=True)


if __name__ == "__main__":
    main()
