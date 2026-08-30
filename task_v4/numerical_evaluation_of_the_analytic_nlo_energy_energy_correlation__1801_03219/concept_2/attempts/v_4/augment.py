from fractional import *
from relaxed import relaxed_direction


def main():
    best=0
    finalists=[]
    started=time.monotonic()
    for name,tilt,curvature in [('backward',4,-4),('central',1,0),('collinear',0,0)]:
        witness=dict(version=1,bin=name,band_start=53,tilt=tilt,curvature=curvature)
        data=precompute(witness)
        patterns=set()
        for pairs in itertools.permutations(list(itertools.combinations((1,4,7),2))):
            choices=[]
            for pair in pairs:
                choices.append([pair]+[tuple(sorted(pair+(index,))) for index in range(8) if index not in pair])
            for masks in itertools.product(*choices):
                count=sum(2*len(mask)+len(set(index//2 for index in mask)) for mask in masks)
                if count>=24:
                    patterns.add(masks)
        attempted=0
        for number,masks in enumerate(sorted(patterns)):
            rows,limits,errors=constraint_rows(data,masks)
            singular=np.linalg.svd(rows/limits[:,None],compute_uv=False)
            if singular[-1]>np.sqrt(len(rows)/.02):
                continue
            attempted+=1
            results=relaxed_direction(data,masks)
            if not results:
                continue
            margin,seed,ratios=results[0]
            if margin>best:
                best=margin
                print('BEST',witness,masks,margin,ratios,'singular',singular[-1],'sec',time.monotonic()-started,flush=True)
            if len(finalists)<30 or margin>finalists[-1][0]:
                finalists.append((margin,witness.copy(),masks,seed))
                finalists.sort(key=lambda entry:entry[0],reverse=True)
                finalists=finalists[:30]
        print('DONE',name,'attempted',attempted,'all',len(patterns),'sec',time.monotonic()-started,flush=True)
        np.save('augmented_finalists.npy',np.array(finalists,dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
