from relaxed import *
from fractional import fractional


def main():
    finalists=[]
    best=0
    started=time.monotonic()
    for name in ['collinear','backward','central']:
        for tilt,curvature in [(0,0),(-4,-4),(4,-4),(-4,4),(4,4)]:
            witness=dict(version=1,bin=name,band_start=53,tilt=tilt,curvature=curvature)
            data=precompute(witness)
            patterns=set()
            for code in range(1,256):
                mask=tuple(index for index in range(8) if code&(1<<index))
                if 2<=len(mask)<=6:
                    patterns.add((mask,mask,mask))
            for length in [3,4,5]:
                for starts in itertools.product(range(9-length),repeat=3):
                    patterns.add(tuple(tuple(range(start,start+length)) for start in starts))
            for number,masks in enumerate(sorted(patterns)):
                candidates=relaxed_direction(data,masks)
                if not candidates:
                    continue
                margin,coefficients,ratios=candidates[0]
                if margin>best:
                    best=margin
                    print('BEST',witness,masks,margin,ratios,'sec',time.monotonic()-started,flush=True)
                if len(finalists)<30 or margin>finalists[-1][0]:
                    finalists.append((margin,witness.copy(),masks,coefficients))
                    finalists.sort(key=lambda entry:entry[0],reverse=True)
                    finalists=finalists[:30]
            print('DONE',witness,'sec',time.monotonic()-started,flush=True)
            np.save('overlapping_finalists.npy',np.array(finalists,dtype=object),allow_pickle=True)
    best_screen=0
    for rank,(margin,witness,masks,seed) in enumerate(finalists):
        data=precompute(witness)
        refined=fractional(data,masks,seed,samples=1024)
        if refined is None:
            continue
        score,coefficients,ratios=refined
        candidate=quantize(witness,coefficients)
        report=measure(candidate,trace=True,kernel=kernel)
        actual=report['worst_screen_margin']
        print('SCREEN',rank,witness,masks,margin,score,actual,flush=True)
        if actual>best_screen:
            best_screen=actual
            Path('overlapping_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('overlapping_report.json').write_text(json.dumps(report,indent=2)+'\n')
            np.save('overlapping_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
