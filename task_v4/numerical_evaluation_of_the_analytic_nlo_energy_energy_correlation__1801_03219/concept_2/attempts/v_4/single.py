from optimize import *


def single(data,mask,family=0,samples=512):
    rows=[]
    for index in mask:
        rows.extend([data[0][index,family],data[1][index,family]])
    for parent in sorted(set(index//2 for index in mask)):
        rows.append(data[2][2*parent,family])
    rows=np.array(rows)
    null=null_space(rows/np.linalg.norm(rows,axis=1)[:,None],rcond=1e-13)
    error=data[3][list(mask),family].sum(axis=0)
    projected=error@null
    magnitude=np.linalg.norm(projected)
    if magnitude<1e-15:
        return 0,None
    stride=max(1,len(data[4])//samples)
    grid=data[4][::stride]@null
    density=data[5][::stride,family].copy()
    density/=density.sum()
    count,dimension=grid.shape
    matrix=sparse.vstack([sparse.hstack([grid,-sparse.eye(count)]),sparse.hstack([-grid,-sparse.eye(count)])],format='csr')
    equality=np.concatenate([projected/magnitude,np.zeros(count)])[None,:]
    objective=np.concatenate([np.zeros(dimension),density])
    result=linprog(objective,A_ub=matrix,b_ub=np.zeros(2*count),A_eq=equality,b_eq=[1],bounds=[(None,None)]*dimension+[(0,None)]*count,method='highs')
    if not result.success:
        return 0,None
    coefficients=null@result.x[:dimension]
    coefficients/=abs(coefficients).sum()
    l1=abs(data[4]@coefficients)@data[5][:,family]
    return abs(error@coefficients)/(1e-5*l1),coefficients


def main():
    best=0
    for name in BINS:
        witness=dict(version=1,bin=name,band_start=53,tilt=-1,curvature=-4)
        data=precompute(witness)
        for code in range(1,256):
            mask=tuple(index for index in range(8) if code&(1<<index))
            margin,coefficients=single(data,mask)
            if margin>best:
                best=margin
                print('BEST',name,mask,margin,flush=True)
                np.save('single_best.npy',np.array([witness,mask,coefficients],dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
