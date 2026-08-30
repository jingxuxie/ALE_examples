from optimize import *
from relaxed import constraint_rows, quantize


def fractional(data,masks,seed,budget=1.0,samples=512,iterations=5,mean_floor=None,custom_limits=None):
    rows,limits,errors=constraint_rows(data,masks)
    if custom_limits is not None:
        limits=np.asarray(custom_limits).copy()
    limits*=budget
    row_norms=np.linalg.norm(rows,axis=1)
    rows/=row_norms[:,None]
    limits/=row_norms
    stride=max(1,len(data[4])//samples)
    grid=data[4][::stride]
    density=data[5][::stride]
    density=density/density.sum(axis=0)
    average_density=density.mean(axis=1)
    errors=errors/data[5].sum(axis=0)[:,None]/1e-5
    signs=np.sign(errors@seed)
    signed=errors*signs[:,None]
    direction=seed/np.linalg.norm(seed)
    count=len(grid)
    dimension=24+count+24+2
    grid_abs=range(24,24+count)
    coefficient_abs=range(24+count,48+count)
    scale_index=48+count
    margin_index=49+count
    def block(left,middle,right,tail):
        return sparse.hstack([sparse.csr_matrix(left),sparse.csr_matrix(middle),sparse.csr_matrix(right),sparse.csr_matrix(tail)],format='csr')
    base=sparse.vstack([
        block(grid,-sparse.eye(count),sparse.csr_matrix((count,24)),np.zeros((count,2))),
        block(-grid,-sparse.eye(count),sparse.csr_matrix((count,24)),np.zeros((count,2))),
        block(np.eye(24),np.zeros((24,count)),-np.eye(24),np.zeros((24,2))),
        block(-np.eye(24),np.zeros((24,count)),-np.eye(24),np.zeros((24,2))),
        block(rows,np.zeros((len(rows),count)),np.zeros((len(rows),24)),np.column_stack([-limits,np.zeros(len(rows))])),
        block(-rows,np.zeros((len(rows),count)),np.zeros((len(rows),24)),np.column_stack([-limits,np.zeros(len(rows))])),
        block(np.zeros((1,24)),np.zeros((1,count)),np.ones((1,24)),[[-(1-1e-8),0]]),
        block(-direction[None,:],np.zeros((1,count)),np.zeros((1,24)),[[np.sqrt(.02)*(1+1e-7),0]]),
        block(np.zeros((1,24)),average_density[None,:],np.zeros((1,24)),[[0,0]]),
    ],format='csr')
    rhs=np.zeros(base.shape[0])
    rhs[-1]=1
    objective=np.zeros(dimension)
    objective[-1]=-1
    bounds=[(None,None)]*24+[(0,None)]*(count+24)+[(0,None),(None,None)]
    ratio=0
    best=None
    for iteration in range(iterations):
        if mean_floor is None:
            extra=block(-signed,ratio*density.T,np.zeros((3,24)),np.column_stack([np.zeros(3),np.ones(3)]))
        else:
            extra=sparse.vstack([
                block(-signed,mean_floor*density.T,np.zeros((3,24)),np.zeros((3,2))),
                block(-signed.mean(axis=0)[None,:],ratio*average_density[None,:],np.zeros((1,24)),[[0,1]]),
            ],format='csr')
        result=linprog(objective,A_ub=sparse.vstack([base,extra],format='csr'),b_ub=np.concatenate([rhs,np.zeros(extra.shape[0])]),bounds=bounds,method='highs',options={'dual_feasibility_tolerance':1e-10,'primal_feasibility_tolerance':1e-10})
        if not result.success:
            break
        if result.x[scale_index] < 1e-10:
            break
        coefficients=result.x[:24]/result.x[scale_index]
        l1=abs(data[4]@coefficients)@data[5]
        actual=abs(errors@coefficients)*data[5].sum(axis=0)*1e-5
        ratios=actual/np.maximum(1e-5*l1,4e-7)
        ratio_new=ratios.min() if mean_floor is None else abs(errors@coefficients).sum()/(l1/data[5].sum(axis=0)).sum()
        best=(ratios.min(),coefficients,ratios)
        if abs(ratio_new-ratio)<1e-7:
            break
        ratio=ratio_new
    return best


def main():
    records=np.load('finalists.npy',allow_pickle=True)
    best=0
    for rank,(old,witness,masks,seed) in enumerate(records[:20]):
        data=precompute(witness)
        result=fractional(data,masks,seed,samples=1024,iterations=6)
        if result is None:
            continue
        margin,coefficients,ratios=result
        print('FRAC',rank,witness['bin'],masks,margin,ratios,'norms',np.linalg.norm(coefficients),abs(coefficients).sum(),flush=True)
        candidate=quantize(witness,coefficients)
        report=measure(candidate,trace=True,kernel=kernel)
        actual=report['worst_screen_margin']
        print('SCREEN',actual,[(entry['target']['panels'],entry['screen_error'],entry['target']['estimated_error']) for entry in report['families'].values()],flush=True)
        if actual>best:
            best=actual
            Path('fractional_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('fractional_report.json').write_text(json.dumps(report,indent=2)+'\n')
            np.save('fractional_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
