import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import numpy as np
import run as study
from epigraph import Epigraph, ROOT
from model import full_hamiltonian, pack


directory = Path(__file__).resolve().parent
study.DIRECTORY = directory/"reduced_exchange"
study.DIRECTORY.mkdir(exist_ok=True)
seed = json.loads((ROOT/"champions/generation_1/submission/witness.json").read_text())
generator = np.random.default_rng(813)
horizontal,vertical = generator.uniform(-np.pi,np.pi,(2,31))
reference = np.linalg.eigvalsh(full_hamiltonian(seed,horizontal,vertical,0.025,0.043))
errors = []
for first,second,strain in ((-horizontal,vertical,0.043),(horizontal,-vertical,0.043),(-vertical,horizontal,-0.043)):
    errors.append(float(np.max(np.abs(np.linalg.eigvalsh(full_hamiltonian(seed,first,second,0.025,strain))-reference))))
assert max(errors)<1e-12
model = Epigraph(5,[0,1,12,13,14,15,21,22,23],time.monotonic()+15)
variables = np.zeros(model.variables)
variables[:model.count] = pack(seed)[model.support]
variables[model.alpha_columns] = -2.0
variables[model.beta_columns] = -1.5
variables[-1] = 0.5
jacobian = model.constraints(variables,True)
maximum_error = 0.0
for index in range(model.variables):
    plus,minus = variables.copy(),variables.copy()
    plus[index] += 1e-6
    minus[index] -= 1e-6
    finite = (model.constraints(plus)-model.constraints(minus))/2e-6
    maximum_error = max(maximum_error,float(np.max(np.abs(finite-jacobian[:,index]))))
assert maximum_error<2e-7
(study.DIRECTORY/"symmetry_and_jacobian.json").write_text(json.dumps({"symmetry_errors":errors,"jacobian_error":maximum_error,"passed":True},indent=2)+"\n")
elapsed = time.time()-(directory/"inputs.json").stat().st_mtime
budget = max(20,min(360,850-elapsed))
sys.argv = [sys.argv[0],"--seconds",str(budget)]
study.main()
