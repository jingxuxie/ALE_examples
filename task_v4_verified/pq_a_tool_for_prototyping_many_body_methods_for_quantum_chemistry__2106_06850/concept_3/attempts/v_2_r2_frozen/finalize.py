from synth import *
from fermion import Excitation,evaluate_path

def finalize():
    cases=load_cases()
    available={case.case_id:[] for case in cases}
    for path in ROOT.glob('*.json'):
        try:
            payload=json.loads(path.read_text())
            entries=payload.get('circuits',[]) if isinstance(payload,dict) else []
            if isinstance(payload,dict) and 'case_id' in payload and 'gates' in payload:entries=[payload]
            for entry in entries:
                if isinstance(entry,dict) and entry.get('case_id') in available:
                    available[entry['case_id']].append((path.name,entry))
        except (ValueError,OSError,TypeError):
            continue
    circuits=[]
    origins=[]
    for case_index,case in enumerate(cases):
        engine=Engine(case_index)
        lookup={label:index for index,label in enumerate(engine.labels)}
        best=None
        for path,payload in available[case.case_id]:
            try:
                gates=payload['gates']
                if len(gates)>case.max_gates:continue
                labels=[lookup[Excitation(tuple(gate['annihilate']),tuple(gate['create']))] for gate in gates]
                angles=np.array([float(gate['theta']) for gate in gates])
                if not np.all(np.isfinite(angles)) or np.any(abs(angles)>np.pi):continue
                state=engine.state(labels,angles)
                fidelity=squared_overlap(engine.target,state)
                if best is None or fidelity>best[0]:best=fidelity,path,labels,angles
            except (KeyError,TypeError,ValueError):
                continue
        if best is None:raise RuntimeError('No valid candidate for '+case.case_id)
        fidelity,path,labels,angles=best
        if engine.target@engine.state(labels,angles)<0:engine.setup(target=-engine.target)
        value,parameters=engine.optimize(labels,angles,iterations=1200,precise=True)
        improved=squared_overlap(engine.target,engine.state(labels,parameters))
        if improved>=fidelity:angles=parameters;fidelity=improved
        circuits.append({'case_id':case.case_id,'gates':[{'annihilate':list(engine.labels[label].annihilate),'create':list(engine.labels[label].create),'theta':float((angle+np.pi)%(2*np.pi)-np.pi)} for label,angle in zip(labels,angles)]})
        origins.append({'case_id':case.case_id,'source':path,'fidelity':fidelity,'gates':len(labels)})
    temporary=ROOT/'submission.pending'
    temporary.write_text(json.dumps({'schema_version':1,'circuits':circuits},separators=(',',':'),allow_nan=False)+'\n')
    os.replace(temporary,ROOT/'submission.json')
    report=evaluate_path(ROOT/'submission.json')
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (ROOT/'selection.json').write_text(json.dumps(origins,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'origins':origins,'report':report,'bytes':(ROOT/'submission.json').stat().st_size},indent=2),flush=True)

if __name__=='__main__':finalize()
