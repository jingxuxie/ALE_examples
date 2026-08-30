from robust import *
from scipy.stats import binom

engine=Engine()
records=[]
patterns=['cycle_*.json','cyclepos_*.json','collective_*.json','collectiveref_*.json','success_*.json','fullsuccess_*.json','frontier_*.json','popscore_*.json','population_*.json','hingesuccess_*.json','scaled*.json','bound*.json']
for pattern in patterns:
    for path in sorted(Path('.').glob(pattern)):
        controls=coefficients(model.load_witness(path))[CONTROL]
        summary=engine.summary(controls)
        parent=summary['parent']
        tail=abs(summary['tail'])
        if parent>1 or tail<50 or tail<100*parent or summary['physical'][0]<.95 or summary['physical'][1]<.4:
            continue
        likelihood=probability(engine,controls,4096,982169)
        quality=sum(min(1,likelihood[family]['success']/.95) for family in ('vv','full'))
        if quality<.98:
            continue
        records.append(dict(path=str(path),quality=quality,probability=likelihood,**summary))
records.sort(key=lambda row:row['quality'],reverse=True)
selected=[]
chosen=[]
for record in records:
    controls=coefficients(model.load_witness(record['path']))[CONTROL]
    if any(np.linalg.norm(controls[:21]-other[:21])<.007 and np.linalg.norm(controls[21:]-other[21:])<.2 for other in selected):
        continue
    selected.append(controls)
    chosen.append(record)
    if len(chosen)>=24:
        break
counts=np.arange(129)
factors=np.minimum(1,counts/(.95*128))
for record,controls in zip(chosen,selected):
    likelihood=probability(engine,controls,131072,1873629)
    record['validation_probability']=likelihood
    record['expected_core']=(1+sum(float(factors@binom.pmf(counts,128,likelihood[family]['success'])) for family in ('vv','full')))/3
chosen.sort(key=lambda row:row['expected_core'],reverse=True)
Path('selection_summary.json').write_text(json.dumps(chosen,indent=2))
for index,record in enumerate(chosen):
    save('finalist_%02d.json'%index,coefficients(model.load_witness(record['path']))[CONTROL])
    print(json.dumps(record),flush=True)
