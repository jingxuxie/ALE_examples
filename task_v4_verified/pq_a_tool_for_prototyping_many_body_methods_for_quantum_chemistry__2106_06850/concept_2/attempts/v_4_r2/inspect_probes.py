import json
import sys
from pathlib import Path
import numpy as np
from oracle import DeterminantCC
from api import CONSTRAINTS
from adaptive import probe_points

filename=Path(sys.argv[1])
source=json.loads(filename.read_text())
oracle=DeterminantCC()
points,response=probe_points(source['pair_matrix'],source['amplitudes'],oracle)
records=[]
for metadata,matrix in points:
    hamiltonian=oracle.hamiltonian(CONSTRAINTS['orbital_energies'],matrix)[0]
    result=oracle.solve(hamiltonian,source['amplitudes'],tolerance=2e-11)
    diagnostics=oracle.diagnostics(hamiltonian,result)
    records.append({**metadata,**diagnostics})
for key in ['occupation_violation','energy_error','rdm_dad','reference_weight','ground_overlap','hf_real_min','hf_imaginary_min','fci_gap','jacobian_condition','amplitude_norm','lambda_norm']:
    smallest=min(records,key=lambda row:row[key]);largest=max(records,key=lambda row:row[key])
    print(key,'base',records[0][key],'min',smallest[key],smallest['point'],smallest.get('axis'),'max',largest[key],largest['point'],largest.get('axis'))
filename.with_suffix('.probes.json').write_text(json.dumps(records,indent=2))
