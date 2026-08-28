import argparse
import concurrent.futures
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "private/reference"


def matrices(angles, modes=4):
    harmonics = 2*np.arange(1,modes+1)
    design = np.sin(np.outer(angles,harmonics))
    inverse = np.linalg.pinv(design)
    integration = -(1-np.cos(np.outer(angles,harmonics)))/harmonics
    return design, integration @ inverse


def summarize(chains):
    means = chains.mean(axis=1)
    count = chains.shape[1]
    within = np.mean(np.var(chains,axis=1,ddof=1),axis=0)
    between = count*np.var(means,axis=0,ddof=1)
    rhat = np.sqrt(np.maximum(0,((count-1)*within+between)/(count*np.maximum(within,1e-30))))
    sem = np.maximum(np.std(means,axis=0,ddof=1)/np.sqrt(len(means)),np.sqrt(within/(len(means)*count)))
    half = count//2
    drift = np.abs(chains[:,:half].mean(axis=(0,1))-chains[:,half:].mean(axis=(0,1)))
    return means.mean(axis=0),sem,rhat,drift


def worker(job):
    case, angle, chain, kind, burn, sweeps = job
    token = f"{case['case_id']}_{kind}_{angle:.10f}_{chain}"
    path = REFERENCE/"raw"/(token+".npz")
    if path.exists():
        return token
    seed = int(hashlib.sha256(token.encode()).hexdigest()[:15],16)
    environment = os.environ.copy()
    if chain%2 or kind == "strong":
        environment["REFERENCE_HOT_START"]="1"
    start=time.monotonic()
    command=[str(REFERENCE/"official_reference"),str(REFERENCE/"native"/(case["case_id"]+".txt")),
             str(case["temperature"]),str(angle),str(burn),str(sweeps),"200",str(seed)]
    result=subprocess.run(command,capture_output=True,text=True,env=environment,check=True,timeout=240)
    blocks=np.array([[float(value) for value in line.split()] for line in result.stdout.splitlines()])
    if blocks.shape != (sweeps//200,6) or not np.isfinite(blocks).all():
        raise RuntimeError("Bad reference blocks: "+token)
    np.savez_compressed(path,blocks=blocks,seed=np.array(seed),seconds=np.array(time.monotonic()-start))
    return token


def load(case,angle,kind,chains):
    extended=REFERENCE/"raw"/(f"{case['case_id']}_extended_{angle:.10f}_0.npz")
    if kind == "production" and extended.exists():
        kind="extended"
    return np.array([np.load(REFERENCE/"raw"/(f"{case['case_id']}_{kind}_{angle:.10f}_{chain}.npz"))["blocks"]
                     for chain in range(chains)])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--workers",type=int,default=48)
    parser.add_argument("--aggregate-only",action="store_true")
    options=parser.parse_args()
    manifest=json.loads((ROOT/"private/challenge_pool/manifest.json").read_text())
    cases=[json.loads((ROOT/entry["path"]).read_text()) for entries in manifest.values() for entry in entries]
    (REFERENCE/"raw").mkdir(exist_ok=True)
    (REFERENCE/"results").mkdir(exist_ok=True)
    (REFERENCE/"strong_results").mkdir(exist_ok=True)
    jobs=[]
    for case in cases:
        for angle in case["angles"][1:-1]:
            for chain in range(4):
                jobs.append((case,angle,chain,"production",3000,10000))
            for chain in range(2):
                jobs.append((case,angle,chain,"strong",6000,10000))
    selected=[case for case in cases if case["case_id"].startswith("initial_") and case["case_id"].endswith("01")]
    selected += [case for case in cases if case["case_id"].startswith("challenge_") and case["case_id"].endswith("00")]
    for case in selected:
        extra=[math.pi*index/32 for index in range(1,16,2)]
        extra += [0.0,math.pi/2,-math.pi/4]
        for angle in extra:
            for chain in range(2):
                jobs.append((case,angle,chain,"validation",6000,10000))
    if not options.aggregate_only:
        with concurrent.futures.ThreadPoolExecutor(max_workers=options.workers) as executor:
            for index,result in enumerate(executor.map(worker,jobs)):
                if index%24 == 0:
                    print(f"reference jobs {index+1}/{len(jobs)}: {result}",flush=True)
    audit={"production_chains":4,"independent_strong_chains":2,"samples_per_chain":10000,
           "burn_sweeps":3000,"strong_burn_sweeps":6000,"block_sweeps":200,
           "official_function_unchanged":True,"cases":{},"angular_and_symmetry":{},"status":"PENDING",
           "refinements":"refinement_plan.json: four fresh chains, 10000 burn and 30000 measured sweeps"}
    for case in cases:
        angles=np.array(case["angles"])
        design,integration=matrices(angles)
        production=np.zeros(len(angles))
        errors=np.zeros(len(angles))
        strong=np.zeros(len(angles))
        strong_errors=np.zeros(len(angles))
        diagnostics=[]
        for index,angle in enumerate(angles[1:-1],1):
            blocks=load(case,angle,"production",4)
            mean,sem,rhat,drift=summarize(blocks)
            production[index]=mean[0]
            errors[index]=sem[0]
            other,other_sem,_,_=summarize(load(case,angle,"strong",2))
            strong[index]=other[0]
            strong_errors[index]=other_sem[0]
            diagnostics.append({"angle":float(angle),"magnetization":float(mean[1]),
                                "measured_sweeps_per_chain":int(blocks.shape[1]*200),
                                "rhat":rhat[:3].tolist(),"half_drift":drift[:3].tolist(),
                                "sem":sem[:3].tolist(),"constraint_max":float(blocks[:,:,3].max()),
                                "spin_norm_max":float(blocks[:,:,4].max()),"acceptance":float(mean[5])})
        free=integration@production
        free_error=np.sqrt((integration**2)@(errors**2))
        result={"version":1,"case_id":case["case_id"],"torque":production.tolist(),"free_energy":free.tolist(),
                "torque_sem":errors.tolist(),"free_energy_sem":free_error.tolist(),
                "magnetization":[item["magnetization"] for item in diagnostics],"n_spins":case["n_spins"]}
        alternate={"version":1,"case_id":case["case_id"],"torque":strong.tolist(),
                   "free_energy":(integration@strong).tolist(),"torque_sem":strong_errors.tolist()}
        (REFERENCE/"results"/(case["case_id"]+".json")).write_text(json.dumps(result,indent=2)+"\n")
        (REFERENCE/"strong_results"/(case["case_id"]+".json")).write_text(json.dumps(alternate,indent=2)+"\n")
        audit["cases"][case["case_id"]]={"family":case["family"],"n_spins":case["n_spins"],
                                             "diagnostics":diagnostics,
                                             "max_rhat":max(max(item["rhat"]) for item in diagnostics),
                                             "strong_torque_zmax":float(np.max(np.abs(production-strong)/np.maximum(np.hypot(errors,strong_errors),1e-14))),
                                             "sine_fit_rmse":float(np.sqrt(np.mean((design@np.linalg.lstsq(design,production,rcond=None)[0]-production)**2)))}
        if case in selected:
            dense_angles=np.linspace(0,math.pi/2,17)
            dense_torque=np.zeros(17)
            dense_torque[::2]=production
            for index in range(1,16,2):
                dense_torque[index]=load(case,dense_angles[index],"validation",2)[:,:,0].mean()
            _,dense_integration=matrices(dense_angles,modes=7)
            refinement=(dense_integration@dense_torque)[::2]-free
            symmetry={}
            for angle in [0.0,math.pi/2,-math.pi/4]:
                mean,sem,_,_=summarize(load(case,angle,"validation",2))
                target=0 if angle>=0 else -production[4]
                uncertainty=sem[0] if angle>=0 else math.hypot(sem[0],errors[4])
                symmetry[str(angle)]={"torque":float(mean[0]),"sem":float(sem[0]),"z":float((mean[0]-target)/max(uncertainty,1e-14))}
            audit["angular_and_symmetry"][case["case_id"]]={"refinement_difference":refinement.tolist(),"symmetry":symmetry}
    maximum_rhat=max(item["max_rhat"] for item in audit["cases"].values())
    maximum_symmetry=max(abs(item["z"]) for entry in audit["angular_and_symmetry"].values() for item in entry["symmetry"].values())
    audit["max_rhat"]=maximum_rhat
    audit["max_symmetry_z"]=maximum_symmetry
    audit["status"]="PASS" if maximum_rhat<1.15 and maximum_symmetry<5.5 else "REQUIRES_REVIEW"
    (REFERENCE/"validation.json").write_text(json.dumps(audit,indent=2)+"\n")
    print(json.dumps({"status":audit["status"],"max_rhat":maximum_rhat,"max_symmetry_z":maximum_symmetry}),flush=True)


if __name__ == "__main__":
    main()
