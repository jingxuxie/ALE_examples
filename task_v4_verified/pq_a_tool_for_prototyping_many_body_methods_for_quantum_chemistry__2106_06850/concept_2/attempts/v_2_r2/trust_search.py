from search import *


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='candidate42.json')
    parser.add_argument('--output', default='trust.json')
    parser.add_argument('--rounds', type=int, default=80)
    parser.add_argument('--radius', type=float, default=.05)
    parser.add_argument('--scale', type=float, default=100.)
    parser.add_argument('--dad', type=float, default=.00095)
    parser.add_argument('--energy', type=float, default=.000095)
    parser.add_argument('--overlap', type=float, default=.99905)
    parser.add_argument('--side', type=int, default=0)
    parser.add_argument('--direct', action='store_true')
    parser.add_argument('--exact', action='store_true')
    parser.add_argument('--condition', type=float, default=99.)
    parser.add_argument('--reference', type=float, default=.451)
    parser.add_argument('--hf', type=float, default=.051)
    args = parser.parse_args()
    search = Search(direct=args.direct)
    data = json.loads(Path(args.start).read_text())
    coordinates = np.asarray(data['pair_matrix'])[search.indices]
    if args.direct:
        hamiltonian = search.base + np.einsum('k,kij->ij', coordinates, search.basis[:120])
        result = search.oracle.solve(hamiltonian, data['amplitudes'])
        multipliers = search.oracle.lambda_state(result)[0]
        coordinates = np.concatenate((coordinates, result.amplitudes, multipliers))
    started = time.monotonic()
    radius = args.radius
    objective_sign = 1 if args.side == 0 else -1

    def objective(point):
        values, derivative = search.evaluate(point)
        return args.scale * objective_sign * values[args.side], args.scale * objective_sign * derivative[args.side]

    def constraint(point):
        values, derivatives = search.constraints(point, args.dad, args.energy, args.overlap)
        values[3] -= args.reference - .451
        values[5:7] -= args.hf - .051
        values[7] += (args.condition - 99.) * .01
        return values, derivatives

    def equality(point):
        values, derivatives = search.evaluate(point)
        equalities = search.stationarity.copy() if args.direct else np.zeros(0)
        equality_derivatives = search.stationarity_derivative.copy() if args.direct else np.zeros((0, search.parameter_count))
        if args.exact:
            equalities = np.concatenate((equalities, values[14:15]))
            equality_derivatives = np.concatenate((equality_derivatives, derivatives[14:15]))
        return equalities, equality_derivatives

    def margin_at(point):
        margin = min(constraint(point)[0])
        if args.direct or args.exact:
            margin = min(margin, -np.max(abs(equality(point)[0])))
        return margin

    constraints = [{'type': 'ineq', 'fun': lambda point: constraint(point)[0], 'jac': lambda point: constraint(point)[1]}]
    if args.direct or args.exact:
        constraints.append({'type': 'eq', 'fun': lambda point: equality(point)[0], 'jac': lambda point: equality(point)[1]})
    limits = np.full(search.parameter_count, 1.499)

    for round_number in range(args.rounds):
        best_point = coordinates.copy()
        best_margin = margin_at(coordinates)
        best_objective = objective(coordinates)[0]

        def callback(point):
            nonlocal best_point, best_margin, best_objective
            margin = margin_at(point)
            value = objective(point)[0]
            if (margin >= -2e-8 and (best_margin < -2e-8 or value < best_objective)) or (best_margin < -2e-8 and margin > best_margin):
                best_point = point.copy()
                best_margin = margin
                best_objective = value

        answer = minimize(objective, coordinates, jac=True, method='SLSQP',
                          bounds=list(zip(np.maximum(-limits, coordinates-radius), np.minimum(limits, coordinates+radius))),
                          constraints=constraints,
                          callback=callback, options={'maxiter': 200, 'ftol': 1e-12, 'disp': False})
        callback(answer.x)
        step = np.max(abs(best_point - coordinates))
        coordinates = best_point
        if args.direct:
            search.evaluate(coordinates)
            result = search.oracle.solve(search.hamiltonian, coordinates[120:138], tolerance=2e-12)
            coordinates[120:138] = result.amplitudes
            coordinates[138:156] = search.oracle.lambda_state(result)[0]
            best_margin = margin_at(coordinates)
        values, _ = search.evaluate(coordinates)
        print(json.dumps({'round': round_number, 'delta': max(-values[0], values[1]-1), 'values': values.tolist(), 'margin': best_margin, 'radius': radius, 'step': step, 'message': answer.message, 'seconds': time.monotonic()-started}), flush=True)
        search.save(coordinates, args.output)
        if max(-values[0], values[1]-1) > .0202 and best_margin >= -2e-8:
            continuation = check_continuation(search.matrix(coordinates), search.result.amplitudes, search.oracle)
            print('PATH', continuation['passed'], flush=True)
            Path(args.output).with_suffix('.path.json').write_text(json.dumps(continuation, indent=2))
            if continuation['passed']:
                break
        if step < 1e-8:
            radius *= .5
        elif step > radius * .7 and best_margin > -2e-8:
            radius = min(.15, radius * 1.1)
        if radius < 1e-5:
            break


if __name__ == '__main__':
    main()
