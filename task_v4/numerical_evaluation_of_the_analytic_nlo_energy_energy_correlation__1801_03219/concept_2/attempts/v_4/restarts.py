from tolerances import *


def main():
    prefix=sys.argv[1] if len(sys.argv)>1 else 'restart'
    source='restart' if prefix=='edge' else 'tolerance'
    duration=float(sys.argv[2]) if len(sys.argv)>2 else 540
    witness,masks,baseline=np.load(source+'_best.npy',allow_pickle=True)
    rows=constraint_rows(precompute(witness),masks)[0]
    null=null_space(rows/np.linalg.norm(rows,axis=1)[:,None],rcond=1e-13)
    generator=np.random.default_rng(20260828)
    best=json.loads(Path(source+'_report.json').read_text())['worst']
    champion=baseline.copy()
    started=time.monotonic()
    for trial in range(20000):
        if time.monotonic()-started>duration:
            break
        fractions=[.95,.955,.96,.965,.97,.975,.98] if prefix=='edge' else [.8,.85,.9,.925,.95]
        fraction=fractions[trial%len(fractions)]
        limits=allocate(witness,masks,champion,fraction)
        strengths=[0,.0001,.0003,.001,.003,.01] if prefix=='edge' else [0,.001,.003,.01,.03,.1,.3,1]
        strength=strengths[(trial//len(fractions))%len(strengths)]
        direction=null@generator.normal(size=null.shape[1])
        direction*=np.linalg.norm(champion)/np.linalg.norm(direction)
        seed=champion+strength*direction
        coefficients,ratios,status,residual=improve(witness,masks,seed,budget=1,custom_limits=limits,maxiter=450)
        if trial%50==0:
            print('PROGRESS',trial,'best',best,'candidate',ratios.min(),'sec',time.monotonic()-started,flush=True)
        if ratios.min()<best-1e-8 or residual>1.01 or np.linalg.norm(coefficients)<np.sqrt(.02):
            continue
        candidate=quantize(witness,coefficients)
        report=verify(candidate)
        if report['worst']>best:
            best=report['worst']
            champion=coefficients.copy()
            print('BEST',trial,fraction,strength,report['worst'],report['mean'],[entry['target']['estimated_error'] for entry in report['families'].values()],flush=True)
            Path(prefix+'_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path(prefix+'_report.json').write_text(json.dumps(report,indent=2)+'\n')
            np.save(prefix+'_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)
    print('DONE','best',best,'sec',time.monotonic()-started,flush=True)


if __name__=='__main__':
    main()
