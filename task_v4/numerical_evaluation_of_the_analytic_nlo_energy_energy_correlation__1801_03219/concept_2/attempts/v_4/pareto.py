from fractional import *


def main():
    witness,masks,seed=np.load('polished_best.npy',allow_pickle=True)
    data=precompute(witness)
    for floor in [.108,.105,.100,.09,.08,0]:
        result=fractional(data,masks,seed,budget=.8,samples=1024,iterations=5,mean_floor=floor)
        if result is None:
            continue
        margin,coefficients,ratios=result
        candidate=quantize(witness,coefficients)
        report=measure(candidate,trace=True,kernel=kernel)
        scores=[entry['screen_margin'] for entry in report['families'].values()]
        print('PARETO',floor,margin,ratios,'actual',scores,'mean',np.mean(scores),flush=True)
        Path(f'pareto_{floor}.json').write_text(json.dumps(candidate,indent=2)+'\n')


if __name__=='__main__':
    main()
