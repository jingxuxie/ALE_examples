from robust import *
from scipy.special import expit


def run(arguments):
    engine=Engine()
    rng=np.random.default_rng(arguments.seed)
    uniforms=rng.random((arguments.samples*2,100))
    original_noise=.002*uniforms-.001
    original_noise[:arguments.samples,np.setdiff1d(np.arange(100),CONTROL)]=0
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
                parent_jac=(gradient[active][:,CONTROL]*noise_jac+np.einsum('ni,nij->nj',noise,hessian[active]))*(1e6*np.sign(active_values))[:,None]
                tails=values[:,-1]*sign
                tail_jac=(gradient[-1,CONTROL][None,:]*noise_jac+noise@hessian[-1])*(1e6*sign)
                losses=parents-np.minimum(1,tails/100)
                loss_jac=parent_jac-(tails<100)[:,None]*tail_jac/100
                tail_losses=(50-tails)/30
                select=tail_losses>losses
                losses[select]=tail_losses[select]
                loss_jac[select]=-tail_jac[select]/30
                vv_count=max(1,int(arguments.samples*arguments.vv_fraction))
                selected=np.argpartition(losses[:arguments.samples],-vv_count)[-vv_count:]
                cached.update(controls=controls.copy(),losses=losses,loss_jac=loss_jac,vv=np.mean(losses[selected]),vv_jac=np.mean(loss_jac[selected],axis=0),means=metrics[:35]*1e6,mean_jac=gradient[:35,CONTROL]*1e6,tail=metrics[-1]*sign*1e6,tail_jac=gradient[-1,CONTROL]*sign*1e6,physical=physical[:2],physical_jac=engine.physical_jacobian.copy())
            return cached

        def constraints(variables):
            result=state(variables*scales)
            return np.r_[.98-result['means'],.98+result['means'],.0098*result['tail']-result['means'],.0098*result['tail']+result['means'],(result['tail']-52)/20,(result['physical']-np.array([.951,.42]))*np.array([100,10]),-result['vv']-arguments.vv_margin]

        def constraint_jac(variables):
            result=state(variables*scales)
            return np.vstack((-result['mean_jac'],result['mean_jac'],.0098*result['tail_jac']-result['mean_jac'],.0098*result['tail_jac']+result['mean_jac'],result['tail_jac'][None,:]/20,result['physical_jac']*np.array([100,10])[:,None],-result['vv_jac'][None,:]))*scales

        for fraction in arguments.fractions:
            def objective(variables):
                result=state(variables*scales)
                losses=result['losses'][arguments.samples:]
                derivatives=result['loss_jac'][arguments.samples:]
                if fraction>0:
                    count=max(1,int(arguments.samples*fraction))
                    selected=np.argpartition(losses,-count)[-count:]
                    return np.mean(losses[selected]),np.mean(derivatives[selected],axis=0)*scales
                probabilities=expit(-losses/(-fraction))
                return -np.mean(probabilities),np.mean((probabilities*(1-probabilities)/(-fraction))[:,None]*derivatives,axis=0)*scales
            result=minimize(objective,current/scales,jac=True,method='SLSQP',bounds=list(zip(-BOUNDS/scales,BOUNDS/scales)),constraints=[dict(type='ineq',fun=constraints,jac=constraint_jac)],options=dict(maxiter=arguments.iterations,ftol=1e-8))
            current=np.clip(result.x*scales,-BOUNDS,BOUNDS)
            summary=engine.summary(current)
            likelihood=probability(engine,current,16384)
            destination=arguments.prefix+'_%03d_%s.json'%(trial,str(fraction).replace('.',''))
            save(destination,current)
            save(arguments.output,current)
            print(json.dumps(dict(trial=trial,source=str(path),destination=destination,fraction=fraction,elapsed=time.monotonic()-started,cost=result.fun,status=result.message,iterations=result.nit,feasible=bool(min(constraints(current/scales))>=-1e-5),probability=likelihood,**summary)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--pattern',default='frontstart_*.json')
    parser.add_argument('--seed',type=int,default=9862871)
    parser.add_argument('--samples',type=int,default=1024)
    parser.add_argument('--vv-fraction',type=float,default=.05)
    parser.add_argument('--vv-margin',type=float,default=0)
    parser.add_argument('--fractions',nargs='+',type=float,default=[.1,-.15,-.07])
    parser.add_argument('--iterations',type=int,default=500)
    parser.add_argument('--prefix',default='frontier')
    parser.add_argument('--output',default='frontier.json')
    run(parser.parse_args())
