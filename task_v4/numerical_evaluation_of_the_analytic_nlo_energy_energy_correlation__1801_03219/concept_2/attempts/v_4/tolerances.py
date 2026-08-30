from highres import *


def allocate(witness,masks,seed,fraction,ratio_limit=None):
    seed=seed/np.linalg.norm(seed)*np.sqrt(.02)*(1+1e-5)
    lower,upper=BINS[witness['bin']]
    limits=[]
    data=precompute(witness)
    errors=constraint_rows(data,masks)[2]
    for family,indices in enumerate(masks):
        allowed=fraction*2e-8
        if ratio_limit is not None:
            allowed=min(allowed,abs(errors[family]@seed)/ratio_limit)
        local=allowed/len(indices)
        for index in indices:
            points=(index+.5)/8+NODES/16
            values=2*(upper-lower)*COLOR[family]*kernel(lower+(upper-lower)*points)[:,family]*response(points,witness)*(basis(points,witness)@seed)
            kronrod=np.dot(KWEIGHTS,values)/16
            variation=np.dot(KWEIGHTS,abs(values-8*kronrod))/16
            embedded=(local/variation)**(2/3)*variation/200
            limits.extend([embedded,local])
        for parent in sorted(set(index//2 for index in indices)):
            limits.append(2*local)
    return np.array(limits)


def main():
    witness,masks,seed=np.load('highres_best.npy',allow_pickle=True)
    data=precompute(witness)
    best=json.loads(Path('highres_report.json').read_text())['worst']
    for fraction,ratio_limit in [(0.5,100),(.7,100),(.8,75),(.7,None),(.8,None),(.9,None)]:
        limits=allocate(witness,masks,seed,fraction,ratio_limit)
        result=fractional(data,masks,seed,budget=1,custom_limits=limits,samples=1024,iterations=6)
        if result is None:
            continue
        predicted,coefficients,ratios=result
        coefficients,ratios,status,residual=improve(witness,masks,coefficients,budget=1,custom_limits=limits,maxiter=700)
        if residual>1.01 or np.linalg.norm(coefficients)<np.sqrt(.02):
            print('REJECT',fraction,ratio_limit,residual,np.linalg.norm(coefficients),flush=True)
            continue
        candidate=quantize(witness,coefficients)
        report=verify(candidate)
        print('TOLERANCE',fraction,ratio_limit,'pred',predicted,'actual',report['worst'],report['mean'],'checks',[(entry['target']['panels'],entry['error']/entry['target']['estimated_error']) for entry in report['families'].values()],flush=True)
        if report['worst']>best:
            best=report['worst']
            Path('tolerance_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('tolerance_report.json').write_text(json.dumps(report,indent=2)+'\n')
            np.save('tolerance_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
