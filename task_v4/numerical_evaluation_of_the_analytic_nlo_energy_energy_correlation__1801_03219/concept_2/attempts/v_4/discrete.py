from optimize import *
from scipy.optimize import milp, Bounds, LinearConstraint


def solve(data,signs,seconds=120):
    dimension=109
    rows=[]
    lower=[]
    upper=[]
    def constrain(entries,lo=-np.inf,hi=np.inf):
        row=np.zeros(dimension)
        for indices,values in entries:
            row[indices]=values
        rows.append(row)
        lower.append(lo)
        upper.append(hi)
    coefficients=np.arange(24)
    for index in range(24):
        constrain([(index,1),(24+index,-1)],hi=0)
        constrain([(index,-1),(24+index,-1)],hi=0)
    constrain([(np.arange(24,48),1)],hi=1)
    constrain([(np.arange(48,72),2),(np.arange(72,84),1)],hi=23)
    error=data[3]/data[5].sum(axis=0)[None,:,None]/1e-5
    maxima=np.max(abs(error),axis=2)
    for family in range(3):
        indicators=48+8*family+np.arange(8)
        constrain([(indicators,1)],lo=1)
        constrain([(84+8*family+np.arange(8),signs[family]),(108,-1)],lo=0)
        for parent in range(4):
            parent_index=72+4*family+parent
            row=data[2][2*parent,family]
            row=row/max(abs(row))
            constrain([(coefficients,row),(parent_index,1)],hi=1+1e-10)
            constrain([(coefficients,-row),(parent_index,1)],hi=1+1e-10)
        for index in range(8):
            hidden=48+8*family+index
            parent_index=72+4*family+index//2
            value_index=84+8*family+index
            constrain([(hidden,1),(parent_index,-1)],hi=0)
            for source in [data[0],data[1]]:
                row=source[index,family]
                row=row/max(abs(row))
                constrain([(coefficients,row),(hidden,1)],hi=1+1e-10)
                constrain([(coefficients,-row),(hidden,1)],hi=1+1e-10)
            row=error[index,family]
            maximum=maxima[index,family]
            constrain([(value_index,1),(hidden,-maximum)],hi=0)
            constrain([(value_index,-1),(hidden,-maximum)],hi=0)
            constrain([(value_index,1),(coefficients,-row),(hidden,maximum)],hi=maximum)
            constrain([(value_index,-1),(coefficients,row),(hidden,maximum)],hi=maximum)
    bounds_lower=np.concatenate([-np.ones(24),np.zeros(60),-maxima.T.ravel(),[0]])
    bounds_upper=np.concatenate([np.ones(84),maxima.T.ravel(),[1]])
    integrality=np.zeros(dimension)
    integrality[48:84]=1
    objective=np.zeros(dimension)
    objective[-1]=-1
    result=milp(objective,integrality=integrality,bounds=Bounds(bounds_lower,bounds_upper),constraints=LinearConstraint(sparse.csr_matrix(rows),lower,upper),options={'time_limit':seconds,'mip_rel_gap':.005})
    if result.x is None:
        print('FAIL',result.message,flush=True)
        return None
    masks=tuple(tuple(np.flatnonzero(result.x[48+8*family:56+8*family]>.5)) for family in range(3))
    print('MILP',signs,'objective',-result.fun,'bound',-result.mip_dual_bound,'nodes',result.mip_node_count,'masks',masks,flush=True)
    return masks


def main():
    best=0
    for name in ['central','backward','collinear']:
        witness=dict(version=1,bin=name,band_start=53,tilt=-1,curvature=-4)
        data=precompute(witness)
        for signs in ([1,1,1],[1,1,-1],[1,-1,1],[1,-1,-1]):
            masks=solve(data,signs,seconds=120)
            if masks is None:
                continue
            candidates=optimize_direction(data,masks,samples=1024)
            if not candidates:
                continue
            margin,coefficients,ratios=candidates[0]
            print('OPT',name,masks,margin,ratios,flush=True)
            if margin>best:
                best=margin
                np.save('discrete_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
