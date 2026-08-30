from responses import *


def main():
    best=0
    finalists=[]
    started=time.monotonic()
    for name,tilt,curvature in [('central',1,0),('backward',4,-1),('collinear',0,0)]:
        witness=dict(version=1,bin=name,band_start=53,tilt=tilt,curvature=curvature)
        data=precompute(witness)
        patterns=[]
        for indices in itertools.product(range(8),repeat=3):
            patterns.append(tuple((index,) for index in indices))
        for indices in itertools.product(range(4),repeat=3):
            patterns.append(tuple((2*index,2*index+1) for index in indices))
        for number,masks in enumerate(patterns):
            rough=score_pattern(data,masks)
            if rough is None or rough[0]<.032:
                continue
            results=optimize_direction(data,masks,samples=512)
            if not results:
                continue
            margin,coefficients,ratios=results[0]
            if margin>best:
                best=margin
                print('BEST',witness,masks,rough[0],margin,ratios,'sec',time.monotonic()-started,flush=True)
            if len(finalists)<50 or margin>finalists[-1][0]:
                finalists.append((margin,witness.copy(),masks,coefficients))
                finalists.sort(key=lambda entry:entry[0],reverse=True)
                finalists=finalists[:50]
        print('DONE',name,'sec',time.monotonic()-started,flush=True)
        np.save('lp_finalists.npy',np.array(finalists,dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
