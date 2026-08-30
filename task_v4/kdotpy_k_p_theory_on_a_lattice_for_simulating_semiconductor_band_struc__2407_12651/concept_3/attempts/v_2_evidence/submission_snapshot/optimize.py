import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
import json
import time
import heapq
from types import SimpleNamespace
from pathlib import Path
import numpy as np
from scipy.optimize import linprog, Bounds, LinearConstraint

ASSETS = Path(os.environ['ASSETS'])
sys.path.insert(0, str(ASSETS / 'workspace'))
from model import features, full_hamiltonian, unpack, pack, baseline, SPIN_MODES, EVEN_MODES

WEIGHTS = np.array([0.] + [np.sqrt(2)] * 11 + [1. if p == q else 2. for p, q in EVEN_MODES] * 2)
BOUNDS = np.array([[-1.9, -.3]] + [[-.75, .75]] * 11 + [[-1.5, 1.5]] * 9 + [[-.75, .75]] * 9)

def milp(objective, integrality, bounds, constraints, options):
    binary = np.flatnonzero(integrality)
    original = list(zip(bounds.lb, bounds.ub))
    started = time.time()
    incumbent = None
    incumbent_value = np.inf
    nodes = 0
    serial = 0
    heap = [(float('-inf'), serial, original)]
    while heap and time.time()-started < options['time_limit']:
        lower, _, current = heapq.heappop(heap)
        if lower >= incumbent_value-1e-9:
            continue
        result = linprog(objective, A_ub=constraints.A, b_ub=constraints.ub, bounds=current, method='highs', options={'parallel':False})
        nodes += 1
        if result.x is None or result.fun >= incumbent_value-1e-9:
            continue
        fractional = [index for index in binary if abs(result.x[index]-round(result.x[index]))>1e-7]
        if not fractional:
            incumbent, incumbent_value = result.x, result.fun
            continue
        fixed = [index for index in binary if current[index][0]>.5]
        available = [index for index in binary if current[index][1]>.5 and index not in fixed]
        selected = fixed+sorted(available, key=lambda index:result.x[index], reverse=True)[:max(0, 8-len(fixed))]
        rounded = current.copy()
        for index in binary:
            value = float(index in selected)
            rounded[index] = (value, value)
        heuristic = linprog(objective, A_ub=constraints.A, b_ub=constraints.ub, bounds=rounded, method='highs', options={'parallel':False})
        if heuristic.x is not None and heuristic.fun < incumbent_value:
            incumbent, incumbent_value = heuristic.x, heuristic.fun
        branch = min(fractional, key=lambda index:abs(result.x[index]-.5))
        for value in [1., 0.]:
            child = current.copy()
            child[branch] = (value, value)
            serial += 1
            heapq.heappush(heap, (result.fun, serial, child))
    return SimpleNamespace(x=incumbent, fun=incumbent_value, success=incumbent is not None, message=f'branch search: {nodes} nodes in {time.time()-started:.1f}s, objective {incumbent_value:.8f}')

class Grid:
    def __init__(self, mesh=19, errors=None, points=None):
        axis = np.linspace(0, np.pi, mesh)
        horizontal, vertical = np.meshgrid(axis, axis, indexing='ij')
        if points is not None:
            horizontal, vertical = np.asarray(points).T
        self.horizontal = horizontal.ravel()
        self.vertical = vertical.ravel()
        self.offset, self.basis = features(self.horizontal, self.vertical)
        self.errors = errors or [(mass, anisotropy) for mass in [-.05, .05] for anisotropy in [0., .06]]
        self.count = len(self.horizontal)
        self.fixed = full_hamiltonian(unpack(np.zeros(30)), self.horizontal, self.vertical)
        self.top = features(np.array([0., np.pi, np.pi]), np.array([0., 0., np.pi]))[1][:, 3, :]
        self.top[1:] *= -1

    def evaluate(self, coefficients, gradients=True):
        components = np.einsum('nij,j->ni', self.basis, coefficients)
        matrices = self.fixed.copy()
        matrices[:, 0, 0] += components[:, 0] + components[:, 3]
        matrices[:, 1, 1] += components[:, 0] - components[:, 3]
        matrices[:, 0, 1] += components[:, 1] - 1j * components[:, 2]
        matrices[:, 1, 0] = matrices[:, 0, 1].conj()
        all_matrices = np.tile(matrices, (len(self.errors), 1, 1))
        for index, (mass, anisotropy) in enumerate(self.errors):
            current = all_matrices[index*self.count:(index+1)*self.count]
            current[:, 0, 0] += mass
            current[:, 1, 1] -= mass
            current[:, 0, 1] += anisotropy * (np.sin(self.horizontal) + 1j*np.sin(self.vertical))
            current[:, 1, 0] = current[:, 0, 1].conj()
        eigenvalues, vectors = np.linalg.eigh(all_matrices)
        energies = eigenvalues.reshape(len(self.errors), self.count, 4)
        if not gradients:
            return energies
        active = vectors[:, :2, :2]
        overlap = active[:, 0, :].conj() * active[:, 1, :]
        population = np.abs(active)**2
        derivatives = np.stack([population.sum(axis=1), 2*overlap.real, 2*overlap.imag, population[:, 0, :]-population[:, 1, :]], axis=1)
        jacobian = np.einsum('ncb,ncj->nbj', derivatives, np.tile(self.basis, (len(self.errors), 1, 1)))
        return energies, jacobian.reshape(len(self.errors), self.count, 2, 30)

    def stats(self, coefficients, energies=None):
        if energies is None:
            energies = self.evaluate(coefficients, False)
        width = np.max(np.ptp(energies[:, :, 0], axis=1))
        direct = np.min(energies[:, :, 1]-energies[:, :, 0])
        indirect = np.min(np.min(energies[:, :, 1], axis=1)-np.max(energies[:, :, 0], axis=1))
        eta = .004 * np.dot(WEIGHTS, np.abs(coefficients))
        return dict(width=float(width), direct=float(direct), indirect=float(indirect), eta=float(eta), wc=float(width+2*eta+.006), gc=float(indirect-2*eta-.009))

def certificate_margins(coefficients, gap01, gap12):
    from validate import fourier, derivative_bounds
    linear, quadratic, _ = derivative_bounds(fourier(coefficients))
    first = np.r_[linear+.06, 1., np.sqrt(2)]
    second = np.r_[quadratic+.06, 0., 0.]
    steps = np.array([2*np.pi/320, 2*np.pi/320, .025, .03])
    lower01 = gap01-first@steps
    lower12 = gap12-first@steps
    epsilon0 = np.dot(second+2*first**2/lower01, steps**2)/8
    epsilon1 = np.dot(second+2*first**2/min(lower01, lower12), steps**2)/8
    return np.array([2*epsilon0, epsilon0+epsilon1])

def optimize(initial, support=None, mesh=19, iterations=180, gap=3.025, verbose=True, sparse=0., save=None, certified=False, grid_override=None, mixed=False):
    grid = Grid(mesh) if grid_override is None else grid_override
    support = np.arange(30) if support is None else np.array([0]+sorted(set(support)-{0}))
    coefficients = initial.copy()
    coefficients[np.setdiff1d(np.arange(30), support)] = 0
    dimension = len(support)
    devices = len(grid.errors)
    center_start = dimension
    width_index = center_start + devices
    slack_index = width_index + 1
    abs_start = slack_index + 1
    binary_start = abs_start+dimension
    total = binary_start+(dimension-1 if mixed else 0)
    objective = np.zeros(total)
    objective[width_index] = 1.
    objective[slack_index] = 5.
    objective[abs_start:binary_start] = .008 * WEIGHTS[support] + sparse
    objective[abs_start] = 0
    trust = .12
    best_merit = np.inf
    start = time.time()
    for iteration in range(iterations):
        energies, jacobian = grid.evaluate(coefficients)
        lower, upper = energies[:, :, 0], energies[:, :, 1]
        stats = grid.stats(coefficients, energies)
        corrections = np.zeros(2)
        correction_gradient = np.zeros((dimension, 2))
        if certified:
            gap01_index = np.unravel_index(np.argmin(upper-lower), upper.shape)
            gap01 = stats['direct']
            gap12 = np.min(energies[:, :, 2]-upper)
            gap01_gradient = jacobian[gap01_index][1]-jacobian[gap01_index][0]
            corrections = certificate_margins(coefficients, gap01, gap12)
            for position, index in enumerate(support):
                changed = coefficients.copy()
                changed[index] += 1e-5
                correction_gradient[position] = (certificate_margins(changed, gap01+1e-5*gap01_gradient[index], gap12)-corrections)/1e-5
            objective[:dimension] = correction_gradient[:, 0]
        target_gap = gap+corrections[1]
        eta2 = .008*np.dot(WEIGHTS, np.abs(coefficients))
        violation = max(0., target_gap+eta2-stats['indirect'])
        merit = stats['width']+eta2+corrections[0]+5*violation+sparse*np.abs(coefficients[1:]).sum()
        if merit < best_merit:
            best_merit = merit
            best = coefficients.copy()
            if save:
                Path(save).write_text(json.dumps(unpack(best), indent=2)+'\n')
        rows = []
        targets = []
        for device in range(devices):
            row = np.zeros((grid.count, total))
            row[:, :dimension] = -jacobian[device, :, 0, support].T
            row[:, center_start+device] = 1.
            rows.append(row)
            targets.append(lower[device])
            row = np.zeros((grid.count, total))
            row[:, :dimension] = jacobian[device, :, 0, support].T
            row[:, center_start+device] = -1.
            row[:, width_index] = -1.
            rows.append(row)
            targets.append(-lower[device])
            row = np.zeros((grid.count, total))
            row[:, :dimension] = -jacobian[device, :, 1, support].T+correction_gradient[:, 1]
            row[:, center_start+device] = 1.
            row[:, width_index] = 1.
            row[:, slack_index] = -1.
            row[:, abs_start:binary_start] = .008 * WEIGHTS[support]
            rows.append(row)
            targets.append(upper[device]-target_gap)
        row = np.zeros((3, total))
        row[:, :dimension] = -grid.top[:, support]
        rows.append(row)
        targets.append(grid.top@coefficients-.25)
        row = np.zeros((2*dimension, total))
        row[:dimension, :dimension] = np.eye(dimension)
        row[:dimension, abs_start:binary_start] = -np.eye(dimension)
        row[dimension:, :dimension] = -np.eye(dimension)
        row[dimension:, abs_start:binary_start] = -np.eye(dimension)
        rows.append(row)
        targets.append(np.r_[-coefficients[support], coefficients[support]])
        bounds = [(max(-trust, BOUNDS[index, 0]-coefficients[index]), min(trust, BOUNDS[index, 1]-coefficients[index])) for index in support]
        bounds += [(None, None)]*devices + [(0, None), (0, None)] + [(0, None)]*dimension
        if mixed:
            row = np.zeros((dimension, total))
            for position, index in enumerate(support[1:]):
                row[position, abs_start+position+1] = 1
                local_bound = max(abs(coefficients[index]+bounds[position+1][0]), abs(coefficients[index]+bounds[position+1][1]))
                row[position, binary_start+position] = -max(local_bound, 1e-10)
            row[-1, binary_start:] = 1
            rows.append(row)
            targets.append(np.r_[np.zeros(dimension-1), 8.])
            bounds += [(1, 1) if bounds[position][0]>-coefficients[index] or bounds[position][1]<-coefficients[index] else (0, 1) for position, index in enumerate(support) if position>0]
        constraints = np.concatenate(rows)
        constraints[np.abs(constraints)<1e-13] = 0.
        if mixed:
            integer = np.zeros(total)
            integer[binary_start:] = 1
            lower_bounds = [-np.inf if low is None else low for low, high in bounds]
            upper_bounds = [np.inf if high is None else high for low, high in bounds]
            result = milp(objective, integrality=integer, bounds=Bounds(lower_bounds, upper_bounds), constraints=LinearConstraint(constraints, -np.inf, np.concatenate(targets)), options={'threads':1, 'time_limit':45., 'mip_rel_gap':1e-6})
        else:
            result = linprog(objective, A_ub=constraints, b_ub=np.concatenate(targets), bounds=bounds, method='highs', options={'threads':1})
        if not result.success and not mixed:
            result = linprog(objective, A_ub=constraints, b_ub=np.concatenate(targets), bounds=bounds, method='highs-ipm', options={'threads':1, 'presolve':False})
        if result.x is None:
            print('LP FAIL', result.message, flush=True)
            break
        candidate = coefficients.copy()
        candidate[support] += result.x[:dimension]
        if mixed:
            candidate[support[1:][result.x[binary_start:]<.5]] = 0
            print('MILP', iteration, result.message, 'support', np.flatnonzero(candidate).tolist(), flush=True)
        new_energies = grid.evaluate(candidate, False)
        new_stats = grid.stats(candidate, new_energies)
        new_corrections = certificate_margins(candidate, new_stats['direct'], np.min(new_energies[:, :, 2]-new_energies[:, :, 1])) if certified else np.zeros(2)
        new_eta2 = .008*np.dot(WEIGHTS, np.abs(candidate))
        new_violation = max(0., gap+new_corrections[1]+new_eta2-new_stats['indirect'])
        new_merit = new_stats['width']+new_eta2+new_corrections[0]+5*new_violation+sparse*np.abs(candidate[1:]).sum()
        change = np.max(np.abs(candidate-coefficients))
        if new_merit < merit+1e-10:
            coefficients = candidate
            trust = min(.2, trust*1.18)
            if new_merit < best_merit:
                best = candidate.copy()
                best_merit = new_merit
                if save:
                    Path(save).write_text(json.dumps(unpack(best), indent=2)+'\n')
        else:
            trust *= .5
        if verbose and (iteration % 10 == 0 or iteration == iterations-1):
            print(iteration, 'time', round(time.time()-start, 1), 'trust', round(trust, 6), stats, flush=True)
        if trust < 2e-6 or change < 2e-7:
            break
    return best, grid.stats(best)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--initial', default='baseline.json')
    parser.add_argument('--output', default='dense.json')
    parser.add_argument('--mesh', type=int, default=19)
    parser.add_argument('--iterations', type=int, default=160)
    parser.add_argument('--gap', type=float, default=3.025)
    parser.add_argument('--sparse', type=float, default=0.)
    parser.add_argument('--support', default='')
    parser.add_argument('--certified', action='store_true')
    parser.add_argument('--mixed', action='store_true')
    args = parser.parse_args()
    initial = pack(json.loads(Path(args.initial).read_text()))
    support = [int(value) for value in args.support.split(',')] if args.support else None
    coefficients, stats = optimize(initial, support=support, mesh=args.mesh, iterations=args.iterations, gap=args.gap, sparse=args.sparse, save=args.output, certified=args.certified, mixed=args.mixed)
    Path(args.output).write_text(json.dumps(unpack(coefficients), indent=2)+'\n')
    print(stats, flush=True)
    print([(index, round(value, 7)) for index, value in enumerate(coefficients) if abs(value)>1e-7], flush=True)
