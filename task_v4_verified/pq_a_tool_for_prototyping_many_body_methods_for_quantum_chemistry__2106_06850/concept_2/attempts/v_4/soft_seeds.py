import json
import time
from pathlib import Path
import numpy as np
from oracle import DeterminantCC
from api import artifact

oracle=DeterminantCC()
epsilon=np.array([-1.2,-.9,-.5,.5,.9,1.2])
axes=[]; diagonal=[]
for row in range(15):
    for column in range(row,15):
        if sorted(orbital%3 for orbital in oracle.pairs[row]) != sorted(orbital%3 for orbital in oracle.pairs[column]):continue
        axis=np.zeros((15,15));axis[row,column]=axis[column,row]=1 if row==column else 1/np.sqrt(2)
        axes.append(axis)
        if row==column:diagonal.append((len(axes)-1,row))
axes=np.array(axes)
hbase=oracle.hamiltonian(epsilon,np.zeros((15,15)))[0]
haxes=np.array([oracle.hamiltonian(np.zeros(6),axis)[0] for axis in axes])
hfbase=np.array(oracle.hf_stability(hbase));hfaxes=np.array([oracle.hf_stability(hamiltonian) for hamiltonian in haxes])
rng=np.random.default_rng(746389);best=[];started=time.monotonic();count=0
for trial in range(40000):
    values=rng.normal(size=len(axes))*rng.uniform(.15,.6)
    spacing=rng.uniform(.92,1.25)
    for index,pair in diagonal:
        first,second=oracle.pairs[pair]
        values[index]=abs(epsilon[first])+abs(epsilon[second])-spacing+rng.normal()*rng.uniform(0,.08)
    matrix=np.einsum('k,kij->ij',values,axes)
    if max(abs(matrix.ravel()))>1.498 or np.linalg.norm(matrix)>6.98:continue
    real_hf,imag_hf=hfbase+np.einsum('k,kbij->bij',values,hfaxes)
    if min(np.linalg.eigvalsh(real_hf)[0],np.linalg.eigvalsh(imag_hf)[0])<.03:continue
    hamiltonian=hbase+np.einsum('k,kij->ij',values,haxes)
    result=oracle.solve(hamiltonian)
    if not result.converged or np.linalg.norm(result.amplitudes)>1.25:continue
    diagnostic=oracle.diagnostics(hamiltonian,result)
    if diagnostic['ground_overlap']<.98 or diagnostic['reference_weight']<.43 or diagnostic['jacobian_condition']>180 or diagnostic['fci_gap']<.075:continue
    count+=1
    minimum=diagnostic['occupations'][0]
    merit=minimum+.015*diagnostic['rdm_dad']
    if minimum<-.001 and (len(best)<40 or merit<best[-1][0]):
        filename=f'soft_seed_{trial}.json';Path(filename).write_text(json.dumps(artifact(matrix,result.amplitudes)))
        best.append([merit,filename,diagnostic]);best.sort(key=lambda row:row[0]);best=best[:40]
        Path('soft_seeds.json').write_text(json.dumps(best,indent=2))
        print(trial,minimum,diagnostic['rdm_dad'],diagnostic['jacobian_condition'],np.linalg.svd(result.jacobian,compute_uv=False)[0],time.monotonic()-started,flush=True)
print('END',count,time.monotonic()-started,flush=True)
