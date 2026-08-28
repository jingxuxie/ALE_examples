import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import zipfile

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
LIMIT=2*1024*1024
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT.parents[1]/"authoring"))
from isolated import run_submission as isolated_run


def baseline(case):
    count=case["n_spins"]
    coordination=2*sum(bond[2] for bond in case["bonds"])/count
    magnetization=max(0.05,1-case["temperature"]/coordination)
    quadratic=np.asarray(case["onsite"])[:,:6].sum(axis=0)*magnetization**2
    cubic=np.asarray(case["onsite"])[:,6].sum()*magnetization**4
    quadratic[2] += sum(bond[3] for bond in case["bonds"])*magnetization**2
    angles=np.asarray(case["angles"])
    horizontal=np.sin(angles)
    vertical=np.cos(angles)
    energy=-quadratic[0]*horizontal**2-quadratic[2]*vertical**2-2*quadratic[4]*horizontal*vertical-cubic*(horizontal**4+vertical**4)
    field_x=2*quadratic[0]*horizontal+2*quadratic[4]*vertical+4*cubic*horizontal**3
    field_z=2*quadratic[2]*vertical+2*quadratic[4]*horizontal+4*cubic*vertical**3
    return {"torque":(vertical*field_x-horizontal*field_z)/count,"free_energy":(energy+quadratic[2]+cubic)/count}


def score(case, reference, prediction):
    if abs(float(np.asarray(prediction["free_energy"])[0]))>1e-12:
        raise ValueError("free_energy[0] must be zero")
    for name in ["torque_sem","free_energy_sem"]:
        if name in prediction:
            uncertainty=np.asarray(prediction[name],dtype=float)
            if uncertainty.shape!=(len(case["angles"]),) or not np.isfinite(uncertainty).all() or np.any(uncertainty<0):
                raise ValueError("Invalid "+name)
    raw_baseline=baseline(case)
    components={}
    for observable in ["torque","free_energy"]:
        values=np.asarray(prediction[observable],dtype=float)
        truth=np.asarray(reference[observable],dtype=float)
        if values.shape != truth.shape or values.ndim != 1 or not np.isfinite(values).all():
            raise ValueError("Invalid "+observable+" shape or values")
        error=float(np.sqrt(np.mean((values-truth)**2)))
        baseline_error=float(np.sqrt(np.mean((raw_baseline[observable]-truth)**2)))
        uncertainty=float(np.sqrt(np.mean(np.asarray(reference[observable+"_sem"])**2)))
        scale=max(baseline_error,20*uncertainty,1e-5)
        components[observable]={"quality":1/(1+error/scale),"rmse":error,
                                "baseline_rmse":baseline_error,"normalization":scale}
    return 0.65*components["torque"]["quality"]+0.35*components["free_energy"]["quality"],components


def read_output(path, case):
    if path.is_symlink():
        raise ValueError("Symlink output rejected")
    if path.exists():
        if path.stat().st_size>LIMIT:
            raise ValueError("Oversized output")
        result=json.loads(path.read_text())
        if result.get("version") != 1 or result.get("case_id") != case["case_id"]:
            raise ValueError("Wrong version or case_id")
        return result
    archive=Path(str(path)+".npz")
    if archive.is_symlink() or archive.stat().st_size>LIMIT:
        raise ValueError("Invalid archive")
    with zipfile.ZipFile(archive) as stream:
        if sum(entry.file_size for entry in stream.infolist())>LIMIT or len(stream.infolist())>8:
            raise ValueError("Oversized uncompressed archive")
    with np.load(archive,allow_pickle=False) as data:
        return {key:data[key] for key in ["torque","free_energy"]}


def run_submission(submission, case_path, case):
    if not shutil.which("bwrap"):
        raise RuntimeError("bwrap required; refusing unsandboxed submission")
    if not (submission/"solve.py").is_file():
        raise ValueError("Submission requires solve.py")
    files=list(submission.rglob("*"))
    if any(path.is_symlink() for path in files):
        raise ValueError("Submission symlinks rejected")
    if any(not path.is_dir() and not path.is_file() for path in files):
        raise ValueError("Nonregular submission files rejected")
    regular=[path for path in files if path.is_file()]
    if len(regular)>512 or sum(path.stat().st_size for path in regular)>64*1024**2:
        raise ValueError("Submission exceeds 512 files or 64 MiB")
    with tempfile.TemporaryDirectory(prefix="eval_",dir=ROOT/"private/run_scratch") as directory:
        stage=Path(directory)
        shutil.copytree(submission,stage/"submission")
        shutil.copyfile(case_path,stage/"case.json")
        (stage/"out").mkdir()
        output=stage/"out/result.json"
        metrics=isolated_run(stage/"submission",stage/"case.json",output,
                             ROOT/"participant",timeout=600,memory_gib=4)
        if metrics["timeout"]:
            raise TimeoutError("Submission exceeded 600 wall seconds")
        if metrics["returncode"]:
            raise RuntimeError(f"Sandbox/submission exit {metrics['returncode']}: {metrics['stderr'][-1200:]}")
        return read_output(output,case),metrics["elapsed"]


def summarize(results, split):
    families={}
    for item in results:
        families.setdefault(item["family"],[]).append(item["score"])
    family_scores={family:float(np.mean(values)) for family,values in families.items()}
    return {"split":split,"mean_score":float(np.mean(list(family_scores.values()))),
            "worst_family_score":min(family_scores.values()),"family_scores":family_scores,
            "runtime_seconds":sum(item["runtime_seconds"] for item in results),"cases":results,
            "sandbox":"bubblewrap, fail-closed, isolated PID/network/mount namespaces",
            "scoring":"0.65/(1+normalized_torque_RMSE)+0.35/(1+normalized_free_energy_RMSE)"}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--submission",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--split",choices=["initial","challenge","confirmation"],default="initial")
    arguments=parser.parse_args()
    manifest=json.loads((ROOT/"private/challenge_pool/manifest.json").read_text())
    (ROOT/"private/run_scratch").mkdir(exist_ok=True)
    results=[]
    for entry in manifest[arguments.split]:
        case_path=ROOT/entry["path"]
        if hashlib.sha256(case_path.read_bytes()).hexdigest()!=entry["sha256"]:
            raise RuntimeError("Frozen case hash mismatch: "+entry["id"])
        case=json.loads(case_path.read_text())
        reference=json.loads((ROOT/"private/reference/results"/(entry["id"]+".json")).read_text())
        item={"id":entry["id"],"family":entry["family"],"score":0.0,"runtime_seconds":0.0}
        start=time.monotonic()
        try:
            prediction,elapsed=run_submission(arguments.submission.resolve(),case_path,case)
            item["score"],item["components"]=score(case,reference,prediction)
            item["runtime_seconds"]=elapsed
            item["status"]="ok"
        except Exception as error:
            item["runtime_seconds"]=time.monotonic()-start
            item["status"]="failed"
            item["error"]=str(error)
        results.append(item)
    report=summarize(results,arguments.split)
    arguments.output.parent.mkdir(parents=True,exist_ok=True)
    arguments.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:report[key] for key in ["mean_score","worst_family_score","runtime_seconds"]}))


if __name__ == "__main__":
    main()
