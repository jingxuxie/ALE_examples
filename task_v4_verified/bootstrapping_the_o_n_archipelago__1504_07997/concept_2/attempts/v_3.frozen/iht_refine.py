import time
import numpy as np
import improve

def refine(solver, seconds=60):
    deadline = time.monotonic()+seconds
    shared = solver.optimizer.shared
    limit = solver.instance['max_atoms']
    best = solver.optimizer.best
    for restart in range(1000):
        current = np.zeros((solver.count, 3))
        if restart % 3 == 0:
            for atom in best['atoms']:
                first, second = atom['ope']
                current[atom['index']] = [first*first, np.sqrt(2)*first*second, second*second]
        elif restart > 1:
            vectors = solver.rng.normal(0, 0.15, (solver.count, 2))
            current = improve.products(vectors)
            current[:, 1] *= np.sqrt(2)
        current[0, 0] = shared*shared
        previous = current.copy()
        for iteration in range(1200):
            acceleration = (iteration-1)/(iteration+2) if iteration else 0.
            extrapolated = current+acceleration*(current-previous)
            residuals = [basis @ extrapolated[:, component]-solver.observations[component] for component, basis in enumerate(solver.bases)]
            gradient = np.column_stack([basis.T @ residuals[component] for component, basis in enumerate(solver.bases)])
            trial = extrapolated-(0.9 if restart % 2 else 0.5)*gradient
            difference = trial[:, 0]-trial[:, 2]
            radius = np.sqrt(difference**2+2*trial[:, 1]**2)
            eigenvalue = np.maximum(0, (trial[:, 0]+trial[:, 2]+radius)/2)
            radius = np.maximum(radius, 1e-30)
            projected = np.column_stack((0.5*eigenvalue*(1+difference/radius), eigenvalue*trial[:, 1]/radius, 0.5*eigenvalue*(1-difference/radius)))
            second = current[0, 1]/(np.sqrt(2)*shared)
            for newton in range(8):
                value = second**3+(shared*shared-trial[0, 2])*second-shared*trial[0, 1]/np.sqrt(2)
                derivative = 3*second**2+shared*shared-trial[0, 2]
                second -= value/max(abs(derivative), 1e-8)*np.sign(derivative)
                second = np.clip(second, -3.9, 3.9)
            projected[0] = [shared*shared, np.sqrt(2)*shared*second, second*second]
            support = np.sort(np.r_[0, np.argsort(-eigenvalue[1:])[:limit-1]+1])
            keep = np.zeros(solver.count, dtype=bool)
            keep[support] = True
            projected[~keep] = 0
            if not np.isfinite(projected).all():
                break
            while projected[0, 0]+projected[0, 2] > solver.instance['trace_budget']:
                second *= 0.5
                projected[0] = [shared*shared, np.sqrt(2)*shared*second, second*second]
            remaining = solver.instance['trace_budget']-projected[0, 0]-projected[0, 2]
            outside = np.sum(projected[1:, 0]+projected[1:, 2])
            if outside > remaining:
                projected[1:] *= remaining/outside
            previous, current = current, projected
            if iteration in (199, 599, 1199):
                vectors = np.zeros((limit, 2))
                vectors[:, 0] = np.sqrt(np.maximum(current[support, 0], 1e-20))
                vectors[:, 1] = current[support, 1]/(np.sqrt(2)*vectors[:, 0])
                vectors[0, 0] = shared
                vectors, cost = solver.full_fit(support, vectors, nfev=600)
                for cutoff in (1e-4, 0):
                    _, vectors, _ = solver.optimizer.fit(support, vectors, cutoff, nfev=600)
                print('IHT', restart, iteration, cost, solver.optimizer.best_error, flush=True)
                best = solver.optimizer.best
                if solver.optimizer.best_error < 1e-8 or time.monotonic() > deadline:
                    return
