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

