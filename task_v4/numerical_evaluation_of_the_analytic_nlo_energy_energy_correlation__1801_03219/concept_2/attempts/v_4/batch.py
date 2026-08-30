from highres import *
from responses import score_pattern,linear_data,interpolate


def main():
    structures=set()
    for filename in ['exhaustive_finalists.npy','finalists.npy','lp_finalists.npy']:
        if Path(filename).exists():
            for record in np.load(filename,allow_pickle=True):
                structures.add(tuple(tuple(mask) for mask in record[2]))
    candidates=[]
    for name in ['backward','central','collinear']:
        witness=dict(version=1,bin=name,band_start=53,tilt=0,curvature=0)
        data_cache=linear_data(witness)
        for tilt,curvature in [(4,-4),(-4,-4),(4,4),(-4,4),(0,0)]:
            witness.update(tilt=tilt,curvature=curvature)
            data=interpolate(data_cache,tilt,curvature)
            for masks in structures:
                result=score_pattern(data,masks)
                if result is None:
                    continue
                margin,seed,ratios=result
                candidates.append((margin,witness.copy(),masks,seed))
    candidates.sort(key=lambda entry:entry[0],reverse=True)
    np.save('batch_candidates.npy',np.array(candidates,dtype=object),allow_pickle=True)
    best=json.loads(Path('highres_report.json').read_text())['worst']
    started=time.monotonic()
    for rank,(rough,witness,masks,seed) in enumerate(candidates[:600]):
        coefficients,ratios,result,residual=improve(witness,masks,seed,maxiter=250)
        if rank%20==0:
            print('PROGRESS',rank,rough,'ratio',ratios.min(),'best',best,'sec',time.monotonic()-started,flush=True)
        if residual>1.01 or np.linalg.norm(coefficients)<np.sqrt(.02) or ratios.min()<best*.999:
            continue
        candidate=quantize(witness,coefficients)
        report=verify(candidate)
        print('VERIFY',rank,witness,masks,rough,report['worst'],report['mean'],flush=True)
        if report['worst']>best:
            best=report['worst']
            Path('highres_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('highres_report.json').write_text(json.dumps(report,indent=2)+'\n')
            np.save('highres_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
