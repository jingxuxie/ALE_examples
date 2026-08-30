from robust import *
from scipy.special import expit
from scipy.sparse import csr_matrix
from scipy.stats import qmc


def run(arguments):
    engine=Engine()
    uniforms=qmc.Sobol(100,scramble=True,seed=arguments.seed).random_base2(arguments.power+1)
    count=len(uniforms)//2
    original_noise=.002*uniforms-.001
    original_noise[:count,np.setdiff1d(np.arange(100),CONTROL)]=0
    scales=np.r_[np.full(21,.03),np.ones(21)]
    started=time.monotonic()
    for trial,path in enumerate(sorted(Path('.').glob(arguments.pattern))):
        current=coefficients(model.load_witness(path))[CONTROL]
        sign=np.sign(engine.evaluate(current)[0][-1])
        cached={}

        def state(controls):
            if 'controls' not in cached or not np.array_equal(cached['controls'],controls):
                metrics,gradient,physical,hessian=engine.evaluate(controls,hessian=True)
                lower=np.maximum(-BOUNDS,controls-.001)
                upper=np.minimum(BOUNDS,controls+.001)
                noise=original_noise.copy()
                noise[:,CONTROL]=lower+uniforms[:,CONTROL]*(upper-lower)-controls
                noise_jac=(controls-.001>-BOUNDS)[None,:]*(1-uniforms[:,CONTROL])+(controls+.001<BOUNDS)[None,:]*uniforms[:,CONTROL]
                values=(metrics[None,:]+noise@gradient.T)*1e6
                active=np.argmax(np.abs(values[:,:35]),axis=1)
                active_values=values[np.arange(len(noise)),active]
                parents=np.abs(active_values)
                tails=values[:,-1]*sign
                margins=np.minimum(1,tails/100)-parents
                tail_margins=(tails-50)/30
                tail_only=tail_margins<margins
                margins[tail_only]=tail_margins[tail_only]
                tail_factors=(tails<100)*sign/100
                tail_factors[tail_only]=sign/30
                cached.update(controls=controls.copy(),noise=noise,noise_jac=noise_jac,gradient=gradient,hessian=hessian,active=active,active_sign=np.sign(active_values),tail_only=tail_only,margins=margins,tail_factors=tail_factors,means=metrics[:35]*1e6,mean_jac=gradient[:35,CONTROL]*1e6,tail=metrics[-1]*sign*1e6,tail_jac=gradient[-1,CONTROL]*sign*1e6,physical=physical[:2],physical_jac=engine.physical_jacobian.copy())
            return cached

        def expectation(controls,temperature,family):
            result=state(controls)
            selected=slice(0,count) if family=='vv' else slice(count,2*count)
            probabilities=expit(result['margins'][selected]/temperature)
            weights=probabilities*(1-probabilities)/(temperature*count)
            parent_weights=-weights*result['active_sign'][selected]*(~result['tail_only'][selected])
            sparse=csr_matrix((parent_weights,(result['active'][selected],np.arange(count))),shape=(35,count))
            aggregate_noise=sparse@result['noise'][selected]
            aggregate_jac=sparse@result['noise_jac'][selected]
            derivative=np.sum(result['gradient'][:35,CONTROL]*aggregate_jac,axis=0)+np.einsum('ac,acj->j',aggregate_noise,result['hessian'][:35])
            tail_weights=weights*result['tail_factors'][selected]
            derivative+=result['gradient'][-1,CONTROL]*(tail_weights@result['noise_jac'][selected])+(tail_weights@result['noise'][selected])@result['hessian'][-1]
            return np.mean(probabilities),derivative*1e6

        if arguments.check:
            center=np.clip(current,-BOUNDS+.003,BOUNDS-.003)
            direction=np.random.default_rng(617).normal(size=42)
            direction/=np.linalg.norm(direction)
            for family in ('vv','full'):
                value,derivative=expectation(center,.05,family)
                plus=expectation(center+1e-5*direction,.05,family)[0]
                minus=expectation(center-1e-5*direction,.05,family)[0]
                print(family,value,'analytic',derivative@direction,'finite',(plus-minus)/2e-5,flush=True)
            return
        for temperature in arguments.temperatures:
            def constraints(variables):
                controls=variables*scales
                result=state(controls)
                probability_vv,_=expectation(controls,temperature,'vv')
                return np.r_[.98-result['means'],.98+result['means'],.0098*result['tail']-result['means'],.0098*result['tail']+result['means'],(result['tail']-52)/20,(result['physical']-np.array([.951,.42]))*np.array([100,10]),(probability_vv-arguments.vv_minimum)*10]

            def constraint_jac(variables):
                controls=variables*scales
                result=state(controls)
                _,probability_jac=expectation(controls,temperature,'vv')
                return np.vstack((-result['mean_jac'],result['mean_jac'],.0098*result['tail_jac']-result['mean_jac'],.0098*result['tail_jac']+result['mean_jac'],result['tail_jac'][None,:]/20,result['physical_jac']*np.array([100,10])[:,None],probability_jac[None,:]*10))*scales

            def objective(variables):
                value,derivative=expectation(variables*scales,temperature,'full')
                return -value,-derivative*scales

            result=minimize(objective,current/scales,jac=True,method='SLSQP',bounds=list(zip(-BOUNDS/scales,BOUNDS/scales)),constraints=[dict(type='ineq',fun=constraints,jac=constraint_jac)],options=dict(maxiter=arguments.iterations,ftol=1e-9))
            current=np.clip(result.x*scales,-BOUNDS,BOUNDS)
            summary=engine.summary(current)
            likelihood=probability(engine,current,65536)
            destination=arguments.prefix+'_%03d_%s.json'%(trial,str(temperature).replace('.',''))
            save(destination,current)
            save(arguments.output,current)
            print(json.dumps(dict(trial=trial,source=str(path),destination=destination,temperature=temperature,elapsed=time.monotonic()-started,cost=result.fun,status=result.message,iterations=result.nit,feasible=bool(min(constraints(current/scales))>=-1e-5),probability=likelihood,**summary)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--pattern',default='frontstart_*.json')
    parser.add_argument('--seed',type=int,default=233872)
    parser.add_argument('--power',type=int,default=13)
    parser.add_argument('--temperatures',nargs='+',type=float,default=[.05,.02])
    parser.add_argument('--vv-minimum',type=float,default=.97)
    parser.add_argument('--iterations',type=int,default=400)
    parser.add_argument('--prefix',default='population')
    parser.add_argument('--output',default='population.json')
    parser.add_argument('--check',action='store_true')
    run(parser.parse_args())
