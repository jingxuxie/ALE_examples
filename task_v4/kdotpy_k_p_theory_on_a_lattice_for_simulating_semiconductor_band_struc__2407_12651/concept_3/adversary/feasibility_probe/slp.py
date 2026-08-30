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
from scipy.optimize import linprog
from epigraph import Deadline, Epigraph, ROOT
from model import pack, unpack
from run import verify_freeze


DIRECTORY = Path(__file__).resolve().parent/"linearized_trust_region"
DIRECTORY.mkdir(exist_ok=True)
overall_start = (DIRECTORY.parent/"inputs.json").stat().st_mtime
deadline = time.monotonic()+max(20,min(190,850-(time.time()-overall_start)))
seed = pack(json.loads((ROOT/"champions/generation_1/submission/witness.json").read_text()))
fixed = [0,1,12,13,14,15]


def state(model, parameters):
    selected = parameters[model.support]
    spectrum, gradient = model.spectral(selected)
    variables = np.zeros(model.variables)
    variables[:model.count] = selected
    variables[model.alpha_columns] = spectrum[...,0].min(axis=1)
    variables[model.beta_columns] = spectrum[...,0].max(axis=1)
    variables[-1] = max(variables[model.beta_columns]-variables[model.alpha_columns])
    constraints = model.constraints(variables)
    jacobian = model.constraints(variables,True)
    gap12 = (spectrum[...,2]-spectrum[...,1]-0.8).ravel()[model.keep]
    gap12_jacobian = np.zeros((len(gap12),model.variables))
    gap12_jacobian[:,:model.count] = (gradient[...,2,:]-gradient[...,1,:]).reshape(-1,model.count)[model.keep]
    constraints = np.r_[constraints,gap12]
    jacobian = np.vstack((jacobian,gap12_jacobian))
    objective, objective_gradient = model.objective(variables)
    merit = objective+80*max(0.0,-float(constraints.min()))
    return variables,constraints,jacobian,objective,objective_gradient,merit


def optimize(initial,support,mesh,iterations):
    model = Epigraph(mesh,support,deadline-15,gap=3.055)
    parameters = np.zeros(30)
    parameters[model.support] = initial[model.support]
    radius = 0.045
    history = []
    for iteration in range(iterations):
        variables,constraints,jacobian,objective,gradient,merit = state(model,parameters)
        bounds = []
        for position,index in enumerate(model.support):
            lower,upper = (-1.9,-0.3) if index==0 else (-1.5,1.5) if 12<=index<21 else (-0.75,0.75)
            bounds.append((max(-radius,lower-variables[position]),min(radius,upper-variables[position])))
        bounds += [(-5.0,5.0)]*(2*model.scenarios)+[(-variables[-1],5.0),(0.0,None)]
        result = linprog(np.r_[gradient,80.0],A_ub=np.c_[-jacobian,-np.ones(len(constraints))],b_ub=constraints,bounds=bounds,method="highs")
        if not result.success:
            break
        proposal = parameters.copy()
        proposal[model.support] += result.x[:model.count]
        proposed = state(model,proposal)
        accepted = proposed[-1]<merit-1e-9
        if accepted:
            parameters = proposal
            radius = min(0.09,radius*1.25)
        else:
            radius *= 0.4
        history.append({"iteration":iteration,"proxy":objective,"violation":max(0.0,-float(constraints.min())),"radius":radius,"accepted":accepted})
        if radius<2e-6:
            break
    final = state(model,parameters)
    return parameters,{"proxy":final[3],"constraint_min":float(final[1].min()),"iterations":len(history),"history":history}


records = []
found = False
freeze_id = verify_freeze()
supports = [(21,22,23),(21,22,24),(21,23,24),(21,23,25),(21,22,25),(22,23,24)]
for index,scalar in enumerate(supports):
    if time.monotonic()>deadline-40:
        break
    try:
        parameters,record = optimize(seed,fixed+list(scalar),13,75)
        if record["constraint_min"]>-1e-3:
            parameters,record = optimize(parameters,fixed+list(scalar),17,65)
    except Deadline:
        break
    record["support"] = fixed+list(scalar)
    path = DIRECTORY/f"candidate_{index}.json"
    path.write_text(json.dumps(unpack(parameters),indent=2)+"\n")
    print("SLP",index,record["proxy"],record["constraint_min"],flush=True)
    if record["constraint_min"]>-1e-3 and time.monotonic()<deadline-12:
        result_path = DIRECTORY/f"candidate_{index}_result.json"
        with (DIRECTORY/f"candidate_{index}_evaluation.log").open("w") as log:
            subprocess.run([sys.executable,str(ROOT/"evaluator/evaluate.py"),"--candidate",str(path),"--output",str(result_path)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=45,env=os.environ.copy())
        report = json.loads(result_path.read_text())
        record.update(score=report["score"],accepted=report["accepted"],result=result_path.name)
        print("FULL",report["score"],report["accepted"],flush=True)
        if report["accepted"]:
            (DIRECTORY/"positive_witness.json").write_bytes(path.read_bytes())
            (DIRECTORY/"positive_result.json").write_bytes(result_path.read_bytes())
            found = True
    records.append(record)
    (DIRECTORY/"records.json").write_text(json.dumps(records,indent=2)+"\n")
    if found:
        break
assert verify_freeze()==freeze_id
(DIRECTORY/"summary.json").write_text(json.dumps({"positive_found":found,"freeze_unchanged":True,"freeze_id":freeze_id,"records":len(records),"global_infeasibility_bound":None},indent=2)+"\n")
