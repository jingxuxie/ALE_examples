from robust import *


def run(arguments):
    engine=Engine()
    rng=np.random.default_rng(arguments.seed)
    started=time.monotonic()
    best=-np.inf
    for trial in range(arguments.trials):
        initial=np.r_[rng.normal(0,arguments.spread,21),rng.uniform(-.5,.5,21)]
        initial=np.clip(initial,-BOUNDS+.0012,BOUNDS-.0012)
        sign=arguments.sign if arguments.sign else rng.choice([-1,1])
        cached={}

        def objective(controls):
            if 'controls' not in cached or not np.array_equal(cached['controls'],controls):
                metrics,gradient,physical,hessian=engine.evaluate(controls,hessian=True)
                means=metrics[:35]*1e6
                mean_jac=gradient[:35,CONTROL]*1e6
                sigma=np.sqrt(np.sum(gradient[:35]**2,axis=1)+1e-28)*1e3/np.sqrt(3)
                sigma_jac=np.einsum('ij,ijk->ik',gradient[:35],hessian[:35])*(1e6/3)/sigma[:,None]
                tails=sign*metrics[-1]*1e6
                tail_jac=sign*gradient[-1,CONTROL]*1e6
                upper=means+arguments.risk*sigma
                lower=-means+arguments.risk*sigma
                upper_jac=mean_jac+arguments.risk*sigma_jac
                lower_jac=-mean_jac+arguments.risk*sigma_jac
                residual=np.r_[upper-arguments.limit,lower-arguments.limit,upper-tails/100,lower-tails/100,(55-tails)*arguments.tail_weight,(np.array([.951,.42])-physical[:2])*np.array([100,10])]
                derivative=np.vstack((upper_jac,lower_jac,upper_jac-tail_jac/100,lower_jac-tail_jac/100,-tail_jac[None,:]*arguments.tail_weight,-engine.physical_jacobian*np.array([100,10])[:,None]))
                derivative[residual<0]=0
                residual=np.maximum(residual,0)
                cached.update(controls=controls.copy(),residual=residual,derivative=derivative)
            return cached

        result=least_squares(lambda controls:objective(controls)['residual'],initial,jac=lambda controls:objective(controls)['derivative'],bounds=(-BOUNDS+.0011,BOUNDS-.0011),x_scale='jac',max_nfev=arguments.iterations,ftol=1e-8,xtol=1e-8,gtol=1e-7)
        summary=engine.summary(result.x)
        likelihood=probability(engine,result.x,2048)
        destination=arguments.prefix+'_%03d.json'%trial
        save(destination,result.x)
        nominal=min(1,1/max(summary['parent'],.0001),abs(summary['tail'])/50,abs(summary['tail'])/max(100*summary['parent'],.0001))
        quality=nominal+min(1,likelihood['vv']['success']/.95)+min(1,likelihood['full']['success']/.95)
        if quality>best:
            best=quality
            save(arguments.output,result.x)
        print(json.dumps(dict(trial=trial,destination=destination,elapsed=time.monotonic()-started,cost=result.cost,evaluations=result.nfev,quality=quality,probability=likelihood,**summary)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=2361287)
    parser.add_argument('--trials',type=int,default=200)
    parser.add_argument('--iterations',type=int,default=150)
    parser.add_argument('--spread',type=float,default=.18)
    parser.add_argument('--risk',type=float,default=1.6)
    parser.add_argument('--limit',type=float,default=.95)
    parser.add_argument('--sign',type=int,default=-1)
    parser.add_argument('--tail-weight',type=float,default=.3)
    parser.add_argument('--prefix',default='hinge')
    parser.add_argument('--output',default='hinge.json')
    run(parser.parse_args())
