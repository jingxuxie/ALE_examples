import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import numpy as np
from epigraph import Deadline, Epigraph, ROOT
from model import EVEN_MODES, pack, unpack


DIRECTORY = Path(__file__).resolve().parent


def verify_freeze():
    path = ROOT/"evaluator/hidden/freeze.json"
    manifest = json.loads(path.read_text())
    assert all(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest for relative,digest in manifest["sha256"].items())
    return manifest["freeze_id"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=600)
    arguments = parser.parse_args()
    started = time.monotonic()
    deadline = started+min(arguments.seconds, 850)
    freeze_id = verify_freeze()
    seed_path = ROOT/"champions/generation_1/submission/witness.json"
    seed = pack(json.loads(seed_path.read_text()))
    fixed_support = [0]+(np.flatnonzero(seed[1:])+1).tolist()
    assert len(fixed_support)==6
    records, evaluations, pool = [], [], []
    gradient_model = Epigraph(5, fixed_support+[21,22,23], deadline)
    selected = seed[gradient_model.support]
    spectrum, gradient = gradient_model.spectral(selected)
    gradient_error = 0.0
    for index in range(len(selected)):
        plus, minus = selected.copy(), selected.copy()
        plus[index] += 2e-6
        minus[index] -= 2e-6
        finite = (gradient_model.spectral(plus)[0]-gradient_model.spectral(minus)[0])/4e-6
        gradient_error = max(gradient_error,float(np.max(np.abs(finite-gradient[...,index]))))
    assert gradient_error < 2e-7
    metadata = {"freeze_id":freeze_id,"source":str(seed_path.relative_to(ROOT)),"source_sha256":hashlib.sha256(seed_path.read_bytes()).hexdigest(),"seconds_limit":min(arguments.seconds,850),"gradient_max_error":gradient_error,"fixed_optional_channels":fixed_support[1:],"fresh2_inspected":False}
    (DIRECTORY/"inputs.json").write_text(json.dumps(metadata,indent=2)+"\n")
    print("INPUTS",json.dumps(metadata),flush=True)

    def checkpoint():
        (DIRECTORY/"search_records.json").write_text(json.dumps(records,indent=2)+"\n")
        (DIRECTORY/"evaluation_index.json").write_text(json.dumps(evaluations,indent=2)+"\n")

    def solve(stage, mesh, initial, support, iterations, allowance):
        model = Epigraph(mesh,support,min(deadline-35,time.monotonic()+allowance))
        parameters, record = model.solve(initial,iterations)
        record.update(stage=stage,mesh=mesh,support=list(map(int,support)),elapsed_seconds=time.monotonic()-started)
        name = f"{len(records):03d}_{stage}"
        path = DIRECTORY/(name+".json")
        path.write_text(json.dumps(unpack(parameters),indent=2)+"\n")
        record["witness"] = path.name
        records.append(record)
        checkpoint()
        print("SEARCH",json.dumps(record),flush=True)
        return parameters,record,path

    def certify(path, record):
        if time.monotonic()>deadline-18 or len(evaluations)>=9:
            return False
        result_path = path.with_name(path.stem+"_result.json")
        command = [sys.executable,str(ROOT/"evaluator/evaluate.py"),"--candidate",str(path),"--output",str(result_path)]
        with path.with_name(path.stem+"_evaluation.log").open("w") as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=min(55,deadline-time.monotonic()-2),env=os.environ.copy())
        report = json.loads(result_path.read_text())
        entry = {"witness":path.name,"result":result_path.name,"score":report["score"],"accepted":report["accepted"],"proxy_objective":record["objective"]}
        evaluations.append(entry)
        checkpoint()
        print("CERTIFICATE",json.dumps(entry),flush=True)
        if report["accepted"]:
            (DIRECTORY/"positive_witness.json").write_bytes(path.read_bytes())
            (DIRECTORY/"positive_result.json").write_bytes(result_path.read_bytes())
            return True
        return False

    found = False
    supports = list(itertools.combinations(range(9),3))
    supports.sort(key=lambda subset:sum(sum(EVEN_MODES[index]) for index in subset))
    coarse_end = started+min(210,arguments.seconds*0.36)
    for subset in supports:
        if time.monotonic()>=coarse_end:
            break
        support = fixed_support+[21+index for index in subset]
        initial = seed if not pool else min(pool,key=lambda item:item[1]["objective"])[0]
        try:
            parameters,record,path = solve("coarse",13,initial,support,65,min(24,coarse_end-time.monotonic()))
        except Deadline:
            continue
        if record["constraint_min"]>=-2e-5:
            pool.append((parameters,record,support))
        if record["constraint_min"]>=-2e-5 and record["objective"]<0.168 and len(evaluations)<3:
            try:
                refined,details,candidate = solve("early17",17,parameters,support,140,40)
                if details["constraint_min"]>=-2e-5 and certify(candidate,details):
                    found = True
                    break
            except Deadline:
                pass
    if not found:
        for parameters,record,support in sorted(pool,key=lambda item:item[1]["objective"])[:10]:
            if time.monotonic()>deadline-60:
                break
            try:
                refined,details,candidate = solve("refine17",17,parameters,support,170,45)
                if details["constraint_min"]>=-2e-5:
                    refined,details,candidate = solve("refine33",33,refined,support,100,65)
                    if certify(candidate,details):
                        found = True
                        break
            except Deadline:
                continue
    if not evaluations and pool and time.monotonic()<deadline-18:
        parameters,record,support = min(pool,key=lambda item:item[1]["objective"])
        found = certify(DIRECTORY/record["witness"],record)
    assert verify_freeze()==freeze_id
    summary = {"achievability":"demonstrated" if found else "unknown","positive_found":found,"elapsed_seconds":time.monotonic()-started,"supports_completed":sum(record["stage"]=="coarse" for record in records),"total_possible_scalar_supports":84,"local_solves_completed":len(records),"full_checker_evaluations":evaluations,"freeze_unchanged":True,"freeze_id":freeze_id,"gradient_max_error":gradient_error,"global_infeasibility_bound":None,"fresh_agents_launched":False,"fresh2_inspected":False}
    (DIRECTORY/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("SUMMARY",json.dumps(summary),flush=True)


if __name__ == "__main__":
    main()
