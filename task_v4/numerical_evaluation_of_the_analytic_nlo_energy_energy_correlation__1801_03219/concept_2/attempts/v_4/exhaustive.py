from patterns import *


def balanced(projected):
    gram=projected@projected.T
    weights=np.zeros((3,13))
    weights[:,:3]=np.eye(3)
    position=3
    for first,second in [(0,1),(0,2),(1,2)]:
        for sign in [1,-1]:
            weights[first,position]=gram[second,second]-sign*gram[first,second]
            weights[second,position]=sign*gram[first,first]-gram[first,second]
            position+=1
    signs=np.array([[1,1,1,1],[1,1,-1,-1],[1,-1,1,-1]])
    weights[:,9:]=np.linalg.pinv(gram,rcond=1e-12)@signs
    predicted=gram@weights
    norms=np.sqrt(np.maximum(np.sum(weights*predicted,axis=0),1e-100))
    weights/=norms
    scores=np.min(abs(predicted/norms),axis=0)
    choice=scores.argmax()
    return scores[choice],projected.T@weights[:,choice]


def search():
    masks=[tuple(index for index in range(8) if code&(1<<index)) for code in range(1,256)]
    costs=np.array([2*len(mask)+len(set(index//2 for index in mask)) for mask in masks])
    mask_order=np.argsort(costs,kind='stable')
    masks=[masks[index] for index in mask_order]
    costs=costs[mask_order]
    finalists=[]
    started=time.monotonic()
    best=0
    for name in ['central','backward','collinear']:
        witness=dict(version=1,bin=name,band_start=53,tilt=-1,curvature=-4)
        data=precompute(witness)
        cached=[]
        for family in range(3):
            entries=[]
            for mask in masks:
                rows=[]
                for index in mask:
                    rows.extend([data[0][index,family],data[1][index,family]])
                for parent in sorted(set(index//2 for index in mask)):
                    rows.append(data[2][2*parent,family])
                rows=np.array(rows)
                rows/=np.linalg.norm(rows,axis=1)[:,None]
                error=data[3][list(mask),family].sum(axis=0)/data[5][:,family].sum()
                entries.append((rows,error))
            cached.append(entries)
        count=0
        for first,first_mask in enumerate(masks):
            if costs[first]+6>23:
                break
            for second,second_mask in enumerate(masks):
                remaining=23-costs[first]-costs[second]
                if remaining<3:
                    break
                first_rows,first_error=cached[0][first]
                second_rows,second_error=cached[1][second]
                row_start=np.concatenate([first_rows,second_rows])
                for third in range(np.searchsorted(costs,remaining,side='right')):
                    third_rows,third_error=cached[2][third]
                    rows=np.concatenate([row_start,third_rows])
                    null=null_space(rows,rcond=1e-13)
                    if null.shape[1]==0:
                        continue
                    errors=np.array([first_error,second_error,third_error])
                    projected=errors@null
                    score,direction=balanced(projected)
                    count+=1
                    if score>best*2e-6 or len(finalists)<200:
                        coefficients=null@direction
                        l1=abs(data[4]@coefficients)@data[5]
                        predicted=abs(errors@coefficients)*data[5].sum(axis=0)
                        ratios=predicted/(1e-5*l1)
                        margin=ratios.min()
                        if margin>best:
                            best=margin
                            print('BEST',name,count,(first_mask,second_mask,masks[third]),margin,ratios,'sec',time.monotonic()-started,flush=True)
                        if len(finalists)<200 or margin>finalists[-1][0]:
                            finalists.append((margin,witness.copy(),(first_mask,second_mask,masks[third]),coefficients))
                            finalists.sort(key=lambda entry:entry[0],reverse=True)
                            finalists=finalists[:200]
            if first%8==0:
                print('PROGRESS',name,first,count,best,'sec',time.monotonic()-started,flush=True)
                np.save('exhaustive_finalists.npy',np.array(finalists,dtype=object),allow_pickle=True)
        print('BIN',name,count,best,time.monotonic()-started,flush=True)
        np.save('exhaustive_finalists.npy',np.array(finalists,dtype=object),allow_pickle=True)


if __name__=='__main__':
    search()
