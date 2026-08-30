from patterns import *


def constraint_rows(data,masks):
    rows, limits = [], []
    errors = []
    for family, indices in enumerate(masks):
        total = len(indices)
        for index in indices:
            rows.extend([data[0][index,family],data[1][index,family]])
            limits.extend([1e-8 / total**(2/3),7e-9 / total])
        for parent in sorted(set(index//2 for index in indices)):
            rows.append(data[2][2*parent,family])
            limits.append(1.4e-8/total)
        errors.append(data[3][list(indices),family].sum(axis=0))
    return np.array(rows),np.array(limits),np.array(errors)


def relaxed_direction(data,masks,budget=1.0):
    rows,limits,errors=constraint_rows(data,masks)
    limits *= budget
    row_norms=np.linalg.norm(rows,axis=1)
    rows=rows/row_norms[:,None]
    limits=limits/row_norms
    normalized=errors/data[5].sum(axis=0)[:,None]
    normalized/=np.linalg.norm(normalized,axis=1).max()
    matrix=np.vstack([
        np.column_stack([rows,np.zeros((len(rows),25))]),
        np.column_stack([-rows,np.zeros((len(rows),25))]),
        np.column_stack([np.eye(24),-np.eye(24),np.zeros(24)]),
        np.column_stack([-np.eye(24),-np.eye(24),np.zeros(24)]),
        np.concatenate([np.zeros(24),np.ones(24),[0]])[None,:],
    ])
    rhs=np.concatenate([limits,limits,np.zeros(48),[1-1e-8]])
    objective=np.concatenate([np.zeros(48),[-1]])
    candidates=[]
    for signs in ([1,1,1],[1,1,-1],[1,-1,1],[1,-1,-1]):
        signed=np.array(signs)[:,None]*normalized
        inequalities=np.vstack([matrix,np.column_stack([-signed,np.zeros((3,24)),np.ones(3)])])
        result=linprog(objective,A_ub=inequalities,b_ub=np.concatenate([rhs,np.zeros(3)]),bounds=[(None,None)]*24+[(0,None)]*24+[(None,None)],method='highs',options={'dual_feasibility_tolerance':1e-10,'primal_feasibility_tolerance':1e-10,'time_limit':.4})
        if result.success:
            coefficients=result.x[:24]
            if np.linalg.norm(coefficients) < np.sqrt(.02):
                continue
            l1=abs(data[4]@coefficients)@data[5]
            ratios=abs(errors@coefficients)/np.maximum(1e-5*l1,4e-7)
            candidates.append((ratios.min(),coefficients,ratios))
    return sorted(candidates,key=lambda entry:entry[0],reverse=True)


def quantize(witness,coefficients):
    integers=np.rint(coefficients*1e10).astype(np.int64)
    candidate=dict(witness,cosine=integers[:12].tolist(),sine=integers[12:].tolist())
    validate(candidate)
    return candidate


def main():
    generator=np.random.default_rng(8291)
    best=0
    finalists=[]
    started=time.monotonic()
    for name in BINS:
        witness=dict(version=1,bin=name,band_start=53,tilt=-1,curvature=-4)
        data=precompute(witness)
        patterns=[]
        for indices in itertools.product(range(8),repeat=3):
            patterns.append(tuple((index,) for index in indices))
        for indices in itertools.product(range(4),repeat=3):
            patterns.append(tuple((2*index,2*index+1) for index in indices))
        for trial in range(500):
            lengths=generator.choice([1,2,3,4],size=3,p=[.15,.45,.30,.10])
            patterns.append(tuple(tuple(sorted(generator.choice(8,length,replace=False))) for length in lengths))
        for number,masks in enumerate(patterns):
            candidates=relaxed_direction(data,masks)
            if not candidates:
                continue
            margin,coefficients,ratios=candidates[0]
            if margin>best:
                best=margin
                print('BEST',name,number,masks,margin,ratios,'sec',time.monotonic()-started,flush=True)
            if len(finalists)<30 or margin>finalists[-1][0]:
                finalists.append((margin,witness.copy(),masks,coefficients))
                finalists.sort(key=lambda entry:entry[0],reverse=True)
                finalists=finalists[:30]
        print('BIN',name,time.monotonic()-started,flush=True)
    np.save('relaxed_finalists.npy',np.array(finalists,dtype=object),allow_pickle=True)
    best_screen=0
    for rank,(margin,witness,masks,coefficients) in enumerate(finalists):
        try:
            candidate=quantize(witness,coefficients)
        except ValueError:
            continue
        report=measure(candidate,trace=True,kernel=kernel)
        result=report['worst_screen_margin']
        print('SCREEN',rank,margin,witness,masks,result,[(entry['target']['panels'],entry['screen_error'],entry['target']['estimated_error']) for entry in report['families'].values()],flush=True)
        if result>best_screen:
            best_screen=result
            Path('relaxed_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('relaxed_report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
