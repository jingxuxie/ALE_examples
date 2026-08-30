from robust import *


def run(arguments):
    engine=Engine()
    rng=np.random.default_rng(arguments.seed)
    started=time.monotonic()
    edges=list(itertools.combinations(range(7),2))
    for trial in range(arguments.trials):
        signs=np.array([1]+[1 if trial&(1<<index) else -1 for index in range(6)])
        initial=np.r_[[-arguments.strength*signs[source]*signs[destination]+rng.normal(0,.02) for source,destination in edges],rng.uniform(-.5,.5,21)]
        initial=np.clip(initial,-BOUNDS+.0012,BOUNDS-.0012)
        cached={}

        def objective(controls):
            if 'controls' not in cached or not np.array_equal(cached['controls'],controls):
                metrics,gradient,physical,hessian=engine.evaluate(controls,hessian=True)
                tail=abs(metrics[-1])*1e6
                tail_jac=np.sign(metrics[-1])*gradient[-1,CONTROL]*1e6
                tail_deficit=max(0,55-tail)*.2
                weight_deficit=max(0,.953-physical[0])*1000
                residual=np.r_[metrics[:35]*1e6,(gradient[:35]*arguments.risk*1e3/np.sqrt(3)).ravel(),(physical[1]-arguments.gap)*1000,weight_deficit,tail_deficit]
                derivative=np.vstack((gradient[:35,CONTROL]*1e6,(hessian[:35]*arguments.risk*1e3/np.sqrt(3)).reshape(-1,42),engine.physical_jacobian[1][None,:]*1000,-engine.physical_jacobian[0][None,:]*1000*(physical[0]<.953),-tail_jac[None,:]*.2*(tail<55)))
                cached.update(controls=controls.copy(),residual=residual,derivative=derivative)
            return cached

        result=least_squares(lambda controls:objective(controls)['residual'],initial,jac=lambda controls:objective(controls)['derivative'],bounds=(-BOUNDS+.0011,BOUNDS-.0011),x_scale='jac',max_nfev=arguments.iterations,ftol=1e-8,xtol=1e-8,gtol=1e-7)
        summary=engine.summary(result.x)
        likelihood=probability(engine,result.x,2048)
        destination=arguments.prefix+'_%03d.json'%trial
        save(destination,result.x)
        print(json.dumps(dict(trial=trial,destination=destination,elapsed=time.monotonic()-started,cost=result.cost,evaluations=result.nfev,probability=likelihood,**summary)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=734292)
    parser.add_argument('--trials',type=int,default=64)
    parser.add_argument('--iterations',type=int,default=200)
    parser.add_argument('--risk',type=float,default=0)
    parser.add_argument('--gap',type=float,default=.43)
    parser.add_argument('--strength',type=float,default=.16)
    parser.add_argument('--prefix',default='collective')
    run(parser.parse_args())
