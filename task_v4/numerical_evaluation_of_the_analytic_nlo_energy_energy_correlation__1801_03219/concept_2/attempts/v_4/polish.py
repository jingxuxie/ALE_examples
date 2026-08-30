from fractional import *


def main():
    filename=sys.argv[1] if len(sys.argv)>1 else 'response_finalists.npy'
    records=np.load(filename,allow_pickle=True)
    best=json.loads(Path('polished_report.json').read_text())['worst_screen_margin'] if Path('polished_report.json').exists() else 0
    cache={}
    for rank,(old,witness,masks,seed) in enumerate(records[:100]):
        tag=tuple(witness.values())
        if tag not in cache:
            cache[tag]=precompute(witness)
        data=cache[tag]
        refined=fractional(data,masks,seed,samples=1024,iterations=6,budget=.8)
        if refined is None:
            continue
        margin,coefficients,ratios=refined
        if margin<best*.995:
            continue
        candidate=quantize(witness,coefficients)
        report=measure(candidate,trace=True,kernel=kernel)
        actual=report['worst_screen_margin']
        print('SCREEN',rank,witness,masks,old,margin,actual,ratios,flush=True)
        if actual>best:
            best=actual
            Path('polished_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('polished_report.json').write_text(json.dumps(report,indent=2)+'\n')
            np.save('polished_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
