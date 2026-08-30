from fractional import *
from verify import verify
from scipy.optimize import minimize


def reference_grid(witness,order,panels):
    nodes,weights=np.polynomial.legendre.leggauss(order)
    lower,upper=BINS[witness['bin']]
    boundaries=list(np.linspace(0,1,panels+1))
    boundaries.extend((edge-lower)/(upper-lower) for edge in kernel.edges if lower<edge<upper)
    boundaries=np.array(sorted(set(boundaries)))
    half=np.diff(boundaries)/2
    points=((boundaries[:-1]+boundaries[1:])[:,None]/2+half[:,None]*nodes).ravel()
    weights=(half[:,None]*weights).ravel()
    density=abs(2*(upper-lower)*COLOR*kernel(lower+(upper-lower)*points))
    density*=response(points,witness)[:,None]*weights[:,None]
    return basis(points,witness),density


def improve(witness,masks,seed,budget=.6,maxiter=300,custom_limits=None):
    data=precompute(witness)
    rows,limits,errors=constraint_rows(data,masks)
    if custom_limits is not None:
        limits=np.asarray(custom_limits).copy()
    limits*=budget
    normalized=rows/limits[:,None]
    left,singular,right=np.linalg.svd(normalized,full_matrices=True)
    scales=np.ones(24)
    scales[:len(singular)]=1/np.maximum(singular,1)
    transform=right.T*scales[None,:]
    guard=normalized@transform
    coarse_basis,coarse_density=reference_grid(witness,24,32)
    fine_basis,fine_density=reference_grid(witness,36,64)
    target_norm=np.sqrt(.02)*(1+1e-5)
    coefficients=seed/np.linalg.norm(seed)*target_norm
    if np.max(abs(normalized@coefficients))>1.001 and len(singular)<24:
        null=right[len(singular):].T
        coefficients=null@(null.T@coefficients)
        coefficients*=target_norm/np.linalg.norm(coefficients)
    initial=(right@coefficients)/scales
    signs=np.sign(errors@coefficients)
    signed=errors*signs[:,None]
    cache={}
    def information(parameters):
        values=parameters[:24]
        if 'values' in cache and np.array_equal(values,cache['values']):
            return cache['ratios'],cache['gradient'],cache['coefficients']
        coefficients=transform@values
        coarse_weight=coarse_basis@coefficients
        fine_weight=fine_basis@coefficients
        coarse_l1=abs(coarse_weight)@coarse_density
        fine_l1=abs(fine_weight)@fine_density
        coarse_gradient=(np.sign(coarse_weight)[:,None]*coarse_density).T@coarse_basis
        fine_gradient=(np.sign(fine_weight)[:,None]*fine_density).T@fine_basis
        use_coarse=coarse_l1>=fine_l1
        l1=np.where(use_coarse,5*coarse_l1-4*fine_l1,5*fine_l1-4*coarse_l1)
        l1_gradient=np.where(use_coarse[:,None],5*coarse_gradient-4*fine_gradient,5*fine_gradient-4*coarse_gradient)
        actual=signed@coefficients-2e-11
        required=np.maximum(1e-5*l1,4e-7)
        required_gradient=np.where((1e-5*l1>=4e-7)[:,None],1e-5*l1_gradient,0)
        ratios=actual/required
        gradient=(signed-required_gradient*ratios[:,None])/required[:,None]
        cache.update(values=values.copy(),ratios=ratios,gradient=gradient,coefficients=coefficients)
        return ratios,gradient,coefficients
    initial=np.concatenate([initial,[0]])
    initial[-1]=information(initial)[0].min()*.99
    guard_jacobian=np.column_stack([guard,np.zeros(len(guard))])
    def norm_function(parameters):
        coefficients=transform@parameters[:24]
        return coefficients@coefficients/target_norm**2-1
    def norm_gradient(parameters):
        coefficients=transform@parameters[:24]
        return np.concatenate([2*coefficients@transform/target_norm**2,[0]])
    def margin_function(parameters):
        return information(parameters)[0]-parameters[-1]
    def margin_gradient(parameters):
        return np.column_stack([information(parameters)[1]@transform,-np.ones(3)])
    constraints=[
        {'type':'eq','fun':norm_function,'jac':norm_gradient},
        {'type':'ineq','fun':lambda values:1-guard@values[:24],'jac':lambda values:-guard_jacobian},
        {'type':'ineq','fun':lambda values:1+guard@values[:24],'jac':lambda values:guard_jacobian},
        {'type':'ineq','fun':margin_function,'jac':margin_gradient},
    ]
    objective=np.concatenate([np.zeros(24),[-1]])
    result=minimize(lambda values:-values[-1],initial,jac=lambda values:objective,method='SLSQP',constraints=constraints,bounds=[(-10,10)]*24+[(0,1)],options={'maxiter':maxiter,'ftol':1e-11})
    ratios,gradient,coefficients=information(result.x)
    return coefficients,ratios,result,np.max(abs(normalized@coefficients))


def main():
    filename=sys.argv[1] if len(sys.argv)>1 else 'triangle_finalists.npy'
    records=np.load(filename,allow_pickle=True)
    best=json.loads(Path('highres_report.json').read_text())['worst'] if Path('highres_report.json').exists() else 0
    seen=set()
    for rank,(margin,witness,masks,seed) in enumerate(records[:40]):
        tag=(tuple(witness.values()),masks)
        if tag in seen:
            continue
        seen.add(tag)
        coefficients,ratios,result,residual=improve(witness,masks,seed)
        print('OPT',rank,witness,masks,'ratio',ratios,'success',result.success,'iterations',result.nit,'residual',residual,flush=True)
        if residual>1.01 or np.linalg.norm(coefficients)<np.sqrt(.02):
            continue
        candidate=quantize(witness,coefficients)
        report=verify(candidate)
        print('VERIFY',report['worst'],report['mean'],flush=True)
        if report['worst']>best:
            best=report['worst']
            Path('highres_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('highres_report.json').write_text(json.dumps(report,indent=2)+'\n')
            np.save('highres_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)


if __name__=='__main__':
    main()
