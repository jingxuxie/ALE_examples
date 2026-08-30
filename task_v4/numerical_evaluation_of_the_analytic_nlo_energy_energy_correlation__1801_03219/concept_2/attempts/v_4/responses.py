from optimize import *
from exhaustive import balanced


def linear_data(witness):
    base=precompute(dict(witness,tilt=0,curvature=0))
    tilt=precompute(dict(witness,tilt=1,curvature=0))
    curvature=precompute(dict(witness,tilt=0,curvature=1))
    return base,tuple(value-origin for value,origin in zip(tilt,base)),tuple(value-origin for value,origin in zip(curvature,base))


def interpolate(cache,tilt,curvature):
    return tuple(base+tilt*first+curvature*second for base,first,second in zip(*cache))


def score_pattern(data,masks):
    proposals=proposal(data,masks)
    if not proposals:
        return None
    rough,coefficients,null,errors=proposals[0]
    projected=errors@null
    score,direction=balanced(projected)
    directions=np.vstack([coefficients,(null@direction)])
    l1=abs(data[4]@directions.T).T@data[5]
    predicted=abs(directions@errors.T)*data[5].sum(axis=0)[None,:]
    ratios=predicted/(1e-5*l1)
    choice=np.argmin(ratios,axis=1).argmax()
    return ratios[choice].min(),directions[choice],ratios[choice]


def main():
    structures=set()
    for filename in ['finalists.npy','exhaustive_finalists.npy']:
        if Path(filename).exists():
            records=np.load(filename,allow_pickle=True)
            structures.update(tuple(tuple(mask) for mask in record[2]) for record in records)
    structures=sorted(structures)
    print('STRUCTURES',len(structures),flush=True)
    best=0
    finalists=[]
    started=time.monotonic()
    for band in [53,52,51,50,49]:
        for name in ['central','backward','collinear']:
            witness=dict(version=1,bin=name,band_start=band,tilt=0,curvature=0)
            cache=linear_data(witness)
            for tilt,curvature in itertools.product(range(-4,5),repeat=2):
                witness.update(tilt=tilt,curvature=curvature)
                data=interpolate(cache,tilt,curvature)
                for masks in structures:
                    result=score_pattern(data,masks)
                    if result is None:
                        continue
                    margin,coefficients,ratios=result
                    if margin>best:
                        best=margin
                        print('BEST',witness,masks,margin,ratios,'sec',time.monotonic()-started,flush=True)
                    if len(finalists)<100 or margin>finalists[-1][0]:
                        finalists.append((margin,witness.copy(),masks,coefficients))
                        finalists.sort(key=lambda entry:entry[0],reverse=True)
                        finalists=finalists[:100]
            print('DONE',band,name,'sec',time.monotonic()-started,flush=True)
            np.save('response_finalists.npy',np.array(finalists,dtype=object),allow_pickle=True)
        if band==53:
            structures=sorted(set(record[2] for record in finalists))
    best_screen=0
    for rank,(margin,witness,masks,seed) in enumerate(finalists[:30]):
        data=precompute(witness)
        result=optimize_direction(data,masks,samples=1024)
        if not result:
            continue
        score,coefficients,ratios=result[0]
        candidate=integer_witness(witness,coefficients)
        report=measure(candidate,trace=True,kernel=kernel)
        actual=report['worst_screen_margin']
        print('SCREEN',rank,witness,masks,margin,score,actual,flush=True)
        if actual>best_screen:
            best_screen=actual
            Path('response_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('response_report.json').write_text(json.dumps(report,indent=2)+'\n')
            np.save('response_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
