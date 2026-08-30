from robust import *


def run(arguments):
    engine=Engine()
    rng=np.random.default_rng(arguments.seed)
    local_edges=list(itertools.combinations(range(7),2))
    cycles=[]
    for block in itertools.combinations(range(7),4):
        for ordering in ((0,1,2,3),(0,1,3,2),(0,2,1,3)):
            cycle=[block[index] for index in ordering]
            cycles.append([local_edges.index(tuple(sorted((cycle[position],cycle[(position+1)%4])))) for position in range(4)])
    started=time.monotonic()
    for trial in range(arguments.trials):
        ring=cycles[trial%len(cycles)]
        initial=np.r_[np.zeros(21),rng.uniform(-.5,.5,21)]
        lower=-BOUNDS+.0011
        upper=BOUNDS-.0011
        for edge_index in ring:
            sign=rng.choice([-1,1])
            initial[edge_index]=sign*rng.uniform(.35,.44)
            if sign>0:lower[edge_index]=arguments.minimum
            else:upper[edge_index]=-arguments.minimum
        cached={}

        def objective(controls):
            if 'controls' not in cached or not np.array_equal(cached['controls'],controls):
                metrics,gradient,physical=engine.evaluate(controls)
                residual=np.r_[metrics[:35]*1e6,(metrics[-1]*1e6-arguments.tail)*arguments.tail_weight]
                derivative=gradient[:,CONTROL]*1e6
                derivative[-1]*=arguments.tail_weight
                cached.update(controls=controls.copy(),residual=residual,derivative=derivative)
            return cached

        result=least_squares(lambda controls:objective(controls)['residual'],initial,jac=lambda controls:objective(controls)['derivative'],bounds=(lower,upper),max_nfev=arguments.iterations,ftol=1e-9,xtol=1e-9,gtol=1e-7)
        summary=engine.summary(result.x)
        destination=arguments.prefix+'_%03d.json'%trial
        save(destination,result.x)
        print(json.dumps(dict(trial=trial,destination=destination,ring=[local_edges[index] for index in ring],elapsed=time.monotonic()-started,cost=result.cost,evaluations=result.nfev,**summary)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=154817)
    parser.add_argument('--trials',type=int,default=420)
    parser.add_argument('--iterations',type=int,default=180)
    parser.add_argument('--minimum',type=float,default=.25)
    parser.add_argument('--tail',type=float,default=-120)
    parser.add_argument('--tail-weight',type=float,default=.1)
    parser.add_argument('--prefix',default='cycle')
    run(parser.parse_args())
