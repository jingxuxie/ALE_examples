from responses import *


def main():
    pairs=list(itertools.combinations(range(8),2))
    finalists=[]
    leaders=[]
    started=time.monotonic()
    for band in range(52,44,-1):
        for name,tilt in [('backward',4),('central',4),('collinear',-4)]:
            witness=dict(version=1,bin=name,band_start=band,tilt=tilt,curvature=-4)
            data=precompute(witness)
            best=0
            for masks in itertools.product(pairs,repeat=3):
                result=score_pattern(data,masks)
                if result is None:
                    continue
                margin,coefficients,ratios=result
                if margin>best:
                    best=margin
                    leader=(margin,witness.copy(),masks,coefficients)
                if len(finalists)<100 or margin>finalists[-1][0]:
                    finalists.append((margin,witness.copy(),masks,coefficients))
                    finalists.sort(key=lambda entry:entry[0],reverse=True)
                    finalists=finalists[:100]
            leaders.append(leader)
            print('BEST',witness,'margin',best,'masks',leader[2],'sec',time.monotonic()-started,flush=True)
            np.save('spectral_finalists.npy',np.array(finalists,dtype=object),allow_pickle=True)
            np.save('spectral_leaders.npy',np.array(leaders,dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
