import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import json
import resource
import sys
from pathlib import Path
import numpy as np
ASSETS='/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
sys.path.insert(0,ASSETS+'/workspace')
from protocol import run_policy,summarize
from pair_model import FAMILIES

synthetic=np.load('synthetic.npz')
cancellation=np.load('cancellation.npz')
models=[]
tables=[]
kinds=[]
for kind,indices,archive in [('ordinary',np.arange(0,240,5),synthetic),('stress',np.arange(600,840,5),synthetic),('cancellation',np.arange(0,120,5),cancellation)]:
    for local,index in enumerate(indices):
        family=str(archive['families'][index]) if 'families' in archive.files else FAMILIES[local%6]
        models.append({'family':family,'orbital_energy':archive['orbital_energy'][index].tolist()})
        tables.append(archive['energies'][index])
        kinds.append(kind)
generator=np.random.default_rng(46819)
ordering=generator.permutation(len(models))
models=[models[index] for index in ordering]
tables=np.array(tables)[ordering]
kinds=np.array(kinds)[ordering]
environment=dict(os.environ,PYTHONPATH=ASSETS+'/workspace',PYTHONDONTWRITEBYTECODE='1')
records,wall=run_policy([sys.executable,str(Path('solution.py').resolve())],models,tables,environment=environment)
report=summarize(records,wall)
usage=resource.getrusage(resource.RUSAGE_CHILDREN)
report['cpu_seconds']=usage.ru_utime+usage.ru_stime
report['peak_rss_kib']=usage.ru_maxrss
report['kind_rmse_microhartree']={kind:float(np.sqrt(np.mean([record['error']**2 for record,label in zip(records,kinds) if label==kind]))*1e6) for kind in sorted(set(kinds))}
for record,kind in zip(records,kinds):
    record['kind']=str(kind)
Path('synthetic_validation_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({key:value for key,value in report.items() if key!='records'},indent=2))
