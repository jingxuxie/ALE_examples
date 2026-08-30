from design import *
from target import integrate


def composite(witness,order,panels,split=True):
    nodes,weights=np.polynomial.legendre.leggauss(order)
    boundaries=list(np.linspace(0,1,panels+1))
    if split:
        lower,upper=BINS[witness['bin']]
        boundaries.extend((edge-lower)/(upper-lower) for edge in kernel.edges if lower<edge<upper)
    boundaries=np.array(sorted(set(boundaries)))
    half=np.diff(boundaries)/2
    points=((boundaries[:-1]+boundaries[1:])[:,None]/2+half[:,None]*nodes).ravel()
    weights=(half[:,None]*weights).ravel()
    values=np.array([kernel.integrand(witness,family)(points) for family in FAMILIES])
    return values@weights,abs(values)@weights


def verify(witness):
    validate(witness)
    coarse,coarse_l1=composite(witness,24,32)
    fine,fine_l1=composite(witness,36,64)
    frozen_coarse,_=composite(witness,40,64)
    frozen_fine,_=composite(witness,56,128)
    absolute=np.maximum(coarse_l1,fine_l1)+4*abs(coarse_l1-fine_l1)
    results={}
    for channel,family in enumerate(FAMILIES):
        target=integrate(kernel.integrand(witness,family),trace=True)
        gap=abs(frozen_fine[channel]-frozen_coarse[channel])
        uncertainty=max(2e-11,10*gap)
        error=max(0,abs(target['value']-frozen_fine[channel])-uncertainty)
        required=max(20*target['tolerance'],50*target['estimated_error'],1e-5*absolute[channel])
        results[family]=dict(target=target,reference=float(frozen_fine[channel]),refinement_gap=float(gap),coarse_signed_gap=float(abs(coarse[channel]-fine[channel])),l1=float(absolute[channel]),coarse_l1=float(coarse_l1[channel]),fine_l1=float(fine_l1[channel]),error=float(error),required=float(required),margin=float(error/required) if target['converged'] else 0)
    return dict(families=results,worst=min(entry['margin'] for entry in results.values()),mean=float(np.mean([entry['margin'] for entry in results.values()])))


if __name__=='__main__':
    for filename in sys.argv[1:] or ['polished_witness.json']:
        witness=json.loads(Path(filename).read_text())
        report=verify(witness)
        print(filename,report['worst'],report['mean'])
        for family,entry in report['families'].items():
            print(family,{key:entry[key] for key in ['reference','refinement_gap','coarse_signed_gap','coarse_l1','fine_l1','l1','error','required','margin']})
