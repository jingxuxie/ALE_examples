from highres import *


def global_direction(witness,masks,seed,samples=4096):
    data=precompute(witness)
    proposals=proposal(data,masks)
    if not proposals:
        return None
    rough,initial,null,errors=proposals[0]
    points=(np.arange(samples)+.5)/samples
    lower,upper=BINS[witness['bin']]
    density=abs(2*(upper-lower)*COLOR*kernel(lower+(upper-lower)*points))*response(points,witness)[:,None]
    density/=density.sum(axis=0)
    average=density.mean(axis=1)
    grid=basis(points,witness)@null
    dimension=null.shape[1]
    projected=errors@null/1e-5
    signs=np.sign(errors@seed)
    projected*=signs[:,None]
    base=sparse.vstack([
        sparse.hstack([grid,-sparse.eye(samples),np.zeros((samples,1))]),
        sparse.hstack([-grid,-sparse.eye(samples),np.zeros((samples,1))]),
        sparse.csr_matrix(np.concatenate([np.zeros(dimension),average,[0]])[None,:]),
    ],format='csr')
    rhs=np.concatenate([np.zeros(2*samples),[1]])
    objective=np.concatenate([np.zeros(dimension+samples),[-1]])
    bounds=[(None,None)]*dimension+[(0,None)]*samples+[(None,None)]
    ratio=0
    best=None
    for iteration in range(8):
        extra=sparse.csr_matrix(np.column_stack([-projected,ratio*density.T,np.ones((3,1))]))
        result=linprog(objective,A_ub=sparse.vstack([base,extra],format='csr'),b_ub=np.concatenate([rhs,np.zeros(3)]),bounds=bounds,method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9})
        if not result.success or np.linalg.norm(result.x[:dimension])<1e-10:
            break
        coefficients=null@result.x[:dimension]
        coefficients/=abs(coefficients).sum()
        l1=abs(basis(points,witness)@coefficients)@density
        ratios=abs(errors@coefficients)/(1e-5*l1)
        next_ratio=ratios.min()
        best=(next_ratio,coefficients,ratios)
        if abs(next_ratio-ratio)<1e-8:
            break
        ratio=next_ratio
    return best


def main():
    records=np.load('triangle_finalists.npy',allow_pickle=True)
    best=json.loads(Path('highres_report.json').read_text())['worst']
    for rank,(old,witness,masks,seed) in enumerate(records[:30]):
        result=global_direction(witness,masks,seed)
        if result is None:
            continue
        bound,coefficients,ratios=result
        print('GLOBAL',rank,witness,masks,bound,ratios,flush=True)
        if bound<best*.998:
            continue
        coefficients,ratios,status,residual=improve(witness,masks,coefficients,maxiter=500)
        candidate=quantize(witness,coefficients)
        report=verify(candidate)
        print('VERIFY',report['worst'],report['mean'],flush=True)
        if report['worst']>best:
            best=report['worst']
            Path('global_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('global_report.json').write_text(json.dumps(report,indent=2)+'\n')
            np.save('global_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
