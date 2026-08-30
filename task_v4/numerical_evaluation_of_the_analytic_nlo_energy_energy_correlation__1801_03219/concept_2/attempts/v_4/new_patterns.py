from highres import *
from responses import score_pattern,linear_data,interpolate


def main():
    old=set(record[2] for record in np.load('batch_candidates.npy',allow_pickle=True))
    structures=set(record[2] for record in np.load('exhaustive_finalists.npy',allow_pickle=True))-old
    finalists=[]
    for name in ['backward','central','collinear']:
        witness=dict(version=1,bin=name,band_start=53,tilt=0,curvature=0)
        cache=linear_data(witness)
        for tilt,curvature in itertools.product(range(-4,5),repeat=2):
            witness.update(tilt=tilt,curvature=curvature)
            data=interpolate(cache,tilt,curvature)
            for masks in structures:
                result=score_pattern(data,masks)
                if result is None:
                    continue
                margin,seed,ratios=result
                finalists.append((margin,witness.copy(),masks,seed))
    finalists.sort(key=lambda entry:entry[0],reverse=True)
    best=json.loads(Path('highres_report.json').read_text())['worst']
    for rank,(rough,witness,masks,seed) in enumerate(finalists[:100]):
        coefficients,ratios,status,residual=improve(witness,masks,seed,maxiter=250)
        if rank%10==0:
            print('PROGRESS',rank,rough,ratios.min(),best,flush=True)
        if ratios.min()<best or residual>1.01 or np.linalg.norm(coefficients)<np.sqrt(.02):
            continue
        candidate=quantize(witness,coefficients)
        report=verify(candidate)
        print('VERIFY',witness,masks,report['worst'],flush=True)
        if report['worst']>best:
            best=report['worst']
            Path('new_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('new_report.json').write_text(json.dumps(report,indent=2)+'\n')
            np.save('new_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
