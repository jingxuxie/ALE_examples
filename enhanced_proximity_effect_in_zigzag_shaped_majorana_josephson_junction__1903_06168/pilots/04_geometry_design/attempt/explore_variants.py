from explore import *


def main():
    with open(Path(__file__).resolve().parent.parent / 'participant' / 'input' / 'example.json') as handle:
        request = json.load(handle)
    if len(sys.argv)>1 and sys.argv[1]=='mismatch':
        request['operating_region']={'mu_normal_mev':[9.5,10.5],'zeeman_mev':[1.35,1.65],'mu_sc_rule':'fixed','mu_sc_mev':15.0}
        scenarios = [dict(mu_normal_mev=mu,zeeman_mev=zeeman) for mu,zeeman in [(9.7,1.41),(10,1.5),(10.3,1.59)]]
        candidates=[None]+[dict(amplitude=amplitude,width=width) for amplitude in [70,110,150,190] for width in [100,140,180,220]]
        candidates += [dict(amplitude=amplitude,width=width,harmonics=2) for amplitude in [70,110] for width in [100,140,180]]
        name='mismatch'
    else:
        scenarios = [dict(mu_normal_mev=mu, zeeman_mev=zeeman) for mu,zeeman in [(11,0.7),(12.5,1),(14,1.3)]]
        candidates=[dict(amplitude=amplitude,width=width,harmonics=harmonics) for harmonics in [1,2,3] for amplitude in [70,110,150] for width in [95,110,140]]
        name='variants'
    started=time.monotonic()
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
        for result in pool.map(evaluate, [(request, candidate, scenarios, 5) for candidate in candidates]):
            parameters,feasible,gaps,invariants=result
            score=(0.5*np.mean(gaps)+0.5*np.min(gaps)) if gaps and max(invariants)<0 else 0
            results.append(dict(parameters=parameters,gaps=gaps,invariants=invariants,score=score,feasible=feasible))
            print(round(time.monotonic()-started,2),json.dumps(results[-1]),flush=True)
    with open(Path(__file__).resolve().parent/(name+'.json'),'w') as handle:
        json.dump(results,handle,indent=2)


if __name__=='__main__':
    main()
