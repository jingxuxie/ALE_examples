from responses import *
from relaxed import constraint_rows


def main():
    best=0
    finalists=[]
    started=time.monotonic()
    for name in ['backward','central','collinear']:
        witness=dict(version=1,bin=name,band_start=53,tilt=0,curvature=0)
        cache=linear_data(witness)
        for points in [(1,4,7),(0,3,6)]:
            pairs=list(itertools.combinations(points,2))
            patterns=list(itertools.permutations(pairs))
            for tilt,curvature in itertools.product(range(-4,5),repeat=2):
                witness.update(tilt=tilt,curvature=curvature)
                data=interpolate(cache,tilt,curvature)
                for masks in patterns:
                    rough=score_pattern(data,masks)
                    if rough is None:
                        continue
                    errors=constraint_rows(data,masks)[2]
                    signs=np.sign(errors@rough[1])
                    signs*=signs[0]
                    results=optimize_direction(data,masks,samples=512,signs_options=[signs])
                    if not results:
                        continue
                    margin,coefficients,ratios=results[0]
                    if margin>best:
                        best=margin
                        print('BEST',witness,masks,margin,ratios,'sec',time.monotonic()-started,flush=True)
                    if len(finalists)<100 or margin>finalists[-1][0]:
                        finalists.append((margin,witness.copy(),masks,coefficients))
                        finalists.sort(key=lambda entry:entry[0],reverse=True)
                        finalists=finalists[:100]
                if curvature==4:
                    np.save('triangle_finalists.npy',np.array(finalists,dtype=object),allow_pickle=True)
                    print('ROW',name,points,tilt,'sec',time.monotonic()-started,flush=True)
            print('DONE',name,points,'sec',time.monotonic()-started,flush=True)
            np.save('triangle_finalists.npy',np.array(finalists,dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
