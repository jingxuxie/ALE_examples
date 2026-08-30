from robust import *


def matchings(nodes):
    if not nodes:
        yield []
    else:
        for position in range(1, len(nodes)):
            edge = (nodes[0], nodes[position])
            remaining = nodes[1:position] + nodes[position+1:]
            for rest in matchings(remaining):
                yield [edge] + rest


def run(arguments):
    engine = Engine()
    rng = np.random.default_rng(arguments.seed)
    local_edges = list(itertools.combinations(range(7), 2))
    graphs = [edges for spectator in range(7) for edges in matchings([node for node in range(7) if node != spectator])]
    records = []
    started = time.monotonic()
    for trial in range(arguments.trials):
        edges = graphs[trial % len(graphs)]
        initial = np.zeros(42)
        for edge in edges:
            initial[local_edges.index(edge)] = rng.choice([-1, 1]) * rng.uniform(.3, .4488)
        initial[21:] = rng.uniform(-.59, .59, 21)
        active = np.array([local_edges.index(edge) for edge in edges] + list(range(21, 42)))
        cached = {}

        def objective(variables):
            controls = initial.copy()
            controls[active] = variables
            if 'controls' not in cached or not np.array_equal(cached['controls'], controls):
                metrics, gradient, physical = engine.evaluate(controls)
                residual = np.r_[metrics[:35] * 1e6, (metrics[-1] * 1e6 - arguments.tail) * arguments.tail_weight]
                derivative = gradient[:, CONTROL[active]] * 1e6
                derivative[-1] *= arguments.tail_weight
                cached.update(controls=controls.copy(), residual=residual, derivative=derivative)
            return cached

        result = least_squares(lambda variables: objective(variables)['residual'], initial[active], jac=lambda variables: objective(variables)['derivative'], bounds=(-BOUNDS[active]+.0011, BOUNDS[active]-.0011), max_nfev=arguments.iterations, ftol=1e-9, xtol=1e-9, gtol=1e-8)
        controls = initial.copy()
        controls[active] = result.x
        summary = engine.summary(controls)
        destination = arguments.prefix+'_%03d.json'%trial
        save(destination,controls)
        print(json.dumps(dict(trial=trial, destination=destination, edges=edges, elapsed=time.monotonic()-started, cost=result.cost, evaluations=result.nfev, **summary)),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=92049)
    parser.add_argument('--trials',type=int,default=210)
    parser.add_argument('--iterations',type=int,default=150)
    parser.add_argument('--tail',type=float,default=-70)
    parser.add_argument('--tail-weight',type=float,default=.2)
    parser.add_argument('--prefix',default='sparse')
    run(parser.parse_args())
