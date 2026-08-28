import argparse
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
STARTS=["aligned","hot","domain_x","domain_z"]


def statistics(blocks):
    chains,count,columns=blocks.shape
    means=blocks.mean(axis=1)
    within=np.var(blocks,axis=1,ddof=1).mean(axis=0)
    between=count*np.var(means,axis=0,ddof=1)
    rhat=np.sqrt(np.maximum(0,((count-1)*within+between)/(count*np.maximum(within,1e-30))))
    sem=np.std(means,axis=0,ddof=1)/math.sqrt(chains)
    for grouping in [1,2,5]:
        grouped=blocks.reshape(chains,count//grouping,grouping,columns).mean(axis=2)
        sem=np.maximum(sem,np.sqrt(np.var(grouped,axis=1,ddof=1).mean(axis=0)/(chains*(count//grouping))))
    return means.mean(axis=0),sem,rhat


def worker(job):
    case,angle,chain,kind,burn,sweeps,start=job
    token=f"{case['case_id']}_{kind}_{angle:.10f}_{chain}"
    path=ROOT/"reference/raw"/(token+".npz")
    if path.exists():
        return token
    seed=int(hashlib.sha256(("ce-reference:"+token).encode()).hexdigest()[:15],16)
    command=[str(ROOT/"reference/cmc"),str(ROOT/"models"/(case["case_id"]+".txt")),str(case["temperature"]),
             str(angle),str(burn),str(sweeps),"200",str(seed),start,str(case["shape"][0])]
    began=time.monotonic()
    completed=subprocess.run(command,check=True,capture_output=True,text=True,timeout=420)
    blocks=np.array([[float(value) for value in line.split()] for line in completed.stdout.splitlines()])
    assert blocks.shape==(sweeps//200,10) and np.isfinite(blocks).all(),token
    np.savez_compressed(path,blocks=blocks,seed=seed,seconds=time.monotonic()-began,start=start,burn=burn,sweeps=sweeps)
    return token


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--phase",choices=["scout","full"],default="scout")
    parser.add_argument("--workers",type=int,default=36)
    parser.add_argument("--case",action="append")
    arguments=parser.parse_args()
    manifest=json.loads((ROOT/"manifest.json").read_text())
    cases=[json.loads((ROOT/entry["path"]).read_text()) for entry in manifest
           if not arguments.case or entry["id"] in arguments.case]
    jobs=[]
    for case in cases:
        if arguments.phase=="scout":
            for index in range(5):
                for chain,start in enumerate(STARTS):
                    jobs.append((case,math.pi*index/8,chain,"scout",10000,10000,start))
        else:
            for index in range(17):
                angle=math.pi*index/32
                for chain,start in enumerate(STARTS):
                    jobs.append((case,angle,chain,"gold",20000,30000,start))
                for chain,start in enumerate(["hot","domain_x"]):
                    jobs.append((case,angle,chain,"strong",40000,40000,start))
            for index in range(1,32,2):
                for chain,start in enumerate(["hot","domain_z"]):
                    jobs.append((case,math.pi*index/64,chain,"midpoint",20000,30000,start))
            for chain,start in enumerate(["hot","domain_x"]):
                jobs.append((case,-math.pi/4,chain,"reflection",20000,30000,start))
    with concurrent.futures.ThreadPoolExecutor(max_workers=arguments.workers) as executor:
        for index,future in enumerate(concurrent.futures.as_completed([executor.submit(worker,job) for job in jobs]),1):
            token=future.result()
            if index%12==0 or index==len(jobs):
                print(f"{arguments.phase} {index}/{len(jobs)}: {token}",flush=True)
    if arguments.phase=="scout":
        previous=ROOT/"reference/scout.json"
        report=json.loads(previous.read_text()) if previous.exists() else {}
        for case in cases:
            records=[]
            for index in range(5):
                angle=math.pi*index/8
                blocks=np.array([np.load(ROOT/"reference/raw"/(f"{case['case_id']}_scout_{angle:.10f}_{chain}.npz"))["blocks"] for chain in range(4)])
                mean,sem,rhat=statistics(blocks)
                records.append({"angle":angle,"mean":mean.tolist(),"sem":sem.tolist(),"rhat":rhat.tolist(),
                    "chain_means":blocks.mean(axis=1).tolist()})
            columns=[0,1,2,5,6,7,8]
            report[case["case_id"]]={"max_rhat":max(item["rhat"][column] for item in records for column in columns),"angles":records}
        (ROOT/"reference/scout.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps({key:value["max_rhat"] for key,value in report.items()}),flush=True)


if __name__ == "__main__":
    main()
