import json
import os
from pathlib import Path
import subprocess
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import trust_region as search
from epigraph import Deadline, ROOT
from model import unpack
from run import verify_freeze


directory = Path(__file__).resolve().parent/"mixed_spin"
directory.mkdir(exist_ok=True)
remaining = max(0.0,840-(time.time()-(directory.parent/"inputs.json").stat().st_mtime))
search.deadline = time.monotonic()+min(135,remaining)
records = []
freeze_id = verify_freeze()
found = False
for index,extra in enumerate(((2,21,22),(2,21,23),(8,21,22),(5,21,22))):
    if time.monotonic()>search.deadline-25:
        break
    try:
        parameters,record = search.optimize(search.seed,search.fixed+list(extra),13,100)
        if record["constraint_min"]>=-1e-3:
            parameters,record = search.optimize(parameters,search.fixed+list(extra),17,90)
    except Deadline:
        break
    path = directory/f"candidate_{index}.json"
    path.write_text(json.dumps(unpack(parameters),indent=2)+"\n")
    record.update(support=search.fixed+list(extra),witness=path.name)
    print("MIXED",index,record["proxy"],record["constraint_min"],flush=True)
    if time.monotonic()<search.deadline-12:
        result_path = directory/f"candidate_{index}_result.json"
        with (directory/f"candidate_{index}_evaluation.log").open("w") as log:
            subprocess.run([sys.executable,str(ROOT/"evaluator/evaluate.py"),"--candidate",str(path),"--output",str(result_path)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=min(45,search.deadline-time.monotonic()),env=os.environ.copy())
        report = json.loads(result_path.read_text())
        record.update(score=report["score"],accepted=report["accepted"],result=result_path.name)
        print("FULL",report["score"],report["accepted"],flush=True)
        if report["accepted"]:
            (directory/"positive_witness.json").write_bytes(path.read_bytes())
            (directory/"positive_result.json").write_bytes(result_path.read_bytes())
            found = True
    records.append(record)
    (directory/"records.json").write_text(json.dumps(records,indent=2)+"\n")
    if found:
        break
assert verify_freeze()==freeze_id
(directory/"summary.json").write_text(json.dumps({"positive_found":found,"freeze_unchanged":True,"freeze_id":freeze_id,"records":len(records),"seconds_reserved":min(135,remaining)},indent=2)+"\n")
