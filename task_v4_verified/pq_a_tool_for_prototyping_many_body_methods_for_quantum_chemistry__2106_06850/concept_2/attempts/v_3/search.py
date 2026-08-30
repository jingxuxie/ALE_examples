import os
os.environ.setdefault('JAX_ENABLE_X64', 'True')
os.environ.setdefault('XLA_FLAGS', '--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1')
import sys
import json
import time
import argparse
import numpy as np
import jax
import jax.numpy as jnp
from scipy.optimize import minimize
from oracle import DeterminantCC
from api import CONSTRAINTS, artifact, endpoint_failures, check_continuation

jax.config.update('jax_enable_x64', True)

class Model:
    def __init__(self, full=False, dad=0.0, energy=0.00006, boost=0.0, triple=0.0, target=0.0, condition=90.0, gap=0.11, robust_energy=0.0):
        self.oracle = oracle = DeterminantCC()
        self.energy_tol = energy
        self.dad_tol = dad
        self.coords = [(row, col) for row in range(15) for col in range(row, 15)
                       if full or sorted(orbital % 3 for orbital in oracle.pairs[row]) == sorted(orbital % 3 for orbital in oracle.pairs[col])]
        self.active = list(range(18)) if full else [index for index, label in enumerate(oracle.labels)
                if sorted(orbital % 3 for orbital in label['holes']) == sorted(orbital % 3 for orbital in label['particles'])]
        self.num_v = len(self.coords)
        self.num_t = len(self.active)
        axes = []
        haxes = []
        for row, col in self.coords:
            axis = np.zeros((15, 15))
            axis[row, col] = axis[col, row] = 1.0 if row == col else 1.0 / np.sqrt(2)
            axes.append(axis)
            haxes.append(oracle.hamiltonian(np.zeros(6), axis)[0])
        self.axes = np.array(axes)
        self.haxes = np.array(haxes)
        hzero = oracle.hamiltonian(CONSTRAINTS['orbital_energies'], np.zeros((15, 15)))[0]
        targets = jnp.array(oracle.targets[self.active])
        all_targets = jnp.array(oracle.targets)
        generators = jnp.array(oracle.generators[self.active])
        identity = jnp.eye(20)
        ref = jnp.array(oracle.ref)
        one = jnp.array(oracle.one)
        haxes_j = jnp.array(self.haxes)
        single_targets = jnp.array(oracle.single_targets)
        double_tangents = np.array([[left @ right @ oracle.ref for right in oracle.singles] for left in oracle.singles])
        double_tangents_j = jnp.array(double_tangents)
        anti_rows, anti_cols = np.triu_indices(6, 1)
        if not full:
            anti_rows, anti_cols = np.array([0,1,2]), np.array([3,4,5])
        self.anti_rows, self.anti_cols = anti_rows, anti_cols

        def calc(values):
            coordinates = values[:self.num_v]
            amps = values[self.num_v:self.num_v+self.num_t]
            multipliers = values[self.num_v+self.num_t:]
            hamiltonian = hzero + jnp.einsum('k,kij->ij', coordinates, haxes_j)
            cluster = jnp.einsum('k,kij->ij', amps, generators)
            square = cluster @ cluster
            cube = square @ cluster / 6
            positive = identity + cluster + square / 2 + cube
            negative = identity - cluster + square / 2 - cube
            hbar = negative @ hamiltonian @ positive
            column = hbar[:, oracle.reference]
            jacobian = hbar[jnp.ix_(targets, targets)] - jnp.einsum('kij,j->ik', generators, column)[targets]
            jacobian_full = hbar[jnp.ix_(all_targets, all_targets)] - jnp.einsum('kij,j->ik', jnp.array(oracle.generators), column)[all_targets]
            left_row = ref.at[targets].set(multipliers)
            left = left_row @ negative
            right = positive[:, oracle.reference]
            gamma = jnp.einsum('i,pqij,j->pq', left, one, right)
            occupations = jnp.linalg.eigvalsh((gamma + gamma.T) / 2)
            anti = gamma[anti_rows, anti_cols] - gamma[anti_cols, anti_rows]
            exact_energy, exact_vectors = jnp.linalg.eigh(hamiltonian)
            delta_energy = column[oracle.reference] - exact_energy[0]
            overlap = (exact_vectors[:, 0] @ right)**2 / (right @ right)
            tangent = hamiltonian[jnp.ix_(single_targets, single_targets)] - hamiltonian[0, 0] * jnp.eye(9)
            double_tangent = jnp.einsum('ijk,k->ij', double_tangents_j, hamiltonian[:, 0])
            hf_real = jnp.linalg.eigvalsh(2*(tangent+double_tangent))[0]
            hf_imag = jnp.linalg.eigvalsh(2*(tangent-double_tangent))[0]
            singular = jnp.linalg.svd(jacobian_full, compute_uv=False)
            eom_min = jnp.min(jnp.linalg.eigvals(jacobian_full).real)
            eq = jnp.concatenate((column[targets], hbar[0, targets]+multipliers@jacobian, anti if self.dad_tol == 0 else jnp.zeros(0)))
            ineq = jnp.array([
                (self.energy_tol-delta_energy)*100,
                (self.energy_tol+delta_energy)*100,
                (overlap-0.9992)*100,
                exact_vectors[0,0]**2-0.46,
                exact_energy[1]-exact_energy[0]-gap,
                hf_real-0.065, hf_imag-0.065,
                singular[-1]-singular[0]/condition,
                1.4**2-multipliers@multipliers,
                1.2**2-amps@amps,
                6.90**2-coordinates@coordinates,
                eom_min-0.065,
                (self.dad_tol**2-jnp.sum(anti**2)*2/3)*1e5 if self.dad_tol else 1.0,
                right[-1]**2-triple**2,
                -occupations[0]-target if target else 1.0,
            ])
            if robust_energy:
                gradient_energy = jnp.einsum('i,kij,j->k', left, haxes_j, right)-jnp.einsum('i,kij,j->k',exact_vectors[:,0],haxes_j,exact_vectors[:,0])
                ineq = jnp.concatenate((ineq, (robust_energy-delta_energy-.001*gradient_energy)*100,
                    (robust_energy+delta_energy+.001*gradient_energy)*100,
                    (robust_energy-delta_energy+.001*gradient_energy)*100,
                    (robust_energy+delta_energy-.001*gradient_energy)*100))
            objective = (coordinates@coordinates)/50+(amps@amps+multipliers@multipliers)/10 if target else occupations[0]*10-boost*right[-1]**2
            info = jnp.array([occupations[0], occupations[-1]-1, delta_energy, overlap, exact_vectors[0,0]**2,
                              hf_real, hf_imag, singular[0]/singular[-1], jnp.sqrt(jnp.sum(anti**2)*2/3)])
            return objective, eq, ineq, info

        self.calc = jax.jit(calc)
        self.objgrad = jax.jit(jax.grad(lambda values: calc(values)[0]))
        self.eqjac = jax.jit(jax.jacfwd(lambda values: calc(values)[1]))
        self.ineqjac = jax.jit(jax.jacfwd(lambda values: calc(values)[2]))
        self.bounds = [(-1.49*(1 if row==col else np.sqrt(2)), 1.49*(1 if row==col else np.sqrt(2))) for row,col in self.coords]+[(-1.2,1.2)]*self.num_t+[(-1.4,1.4)]*self.num_t

    def unpack(self, values):
        matrix = np.einsum('k,kij->ij', values[:self.num_v], self.axes)
        amps = np.zeros(18)
        amps[self.active] = values[self.num_v:self.num_v+self.num_t]
        return matrix, amps

    def pack(self, matrix, initial=None):
        hamiltonian = self.oracle.hamiltonian(CONSTRAINTS['orbital_energies'], matrix)[0]
        result = self.oracle.solve(hamiltonian, initial)
        multipliers = self.oracle.lambda_state(result)[0]
        return np.concatenate((np.einsum('kij,ij->k', self.axes, matrix), result.amplitudes[self.active], multipliers[self.active]))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--seed', type=int, default=71)
    parser.add_argument('--starts', type=int, default=20)
    parser.add_argument('--iterations', type=int, default=400)
    parser.add_argument('--input')
    parser.add_argument('--dad', type=float, default=0)
    parser.add_argument('--energy', type=float, default=0.00006)
    parser.add_argument('--boost', type=float, default=0)
    parser.add_argument('--triple', type=float, default=0)
    parser.add_argument('--target', type=float, default=0)
    parser.add_argument('--condition', type=float, default=90)
    parser.add_argument('--gap', type=float, default=.11)
    parser.add_argument('--robust-energy', type=float, default=0)
    args = parser.parse_args()
    model = Model(args.full, args.dad, args.energy, args.boost, args.triple, args.target, args.condition, args.gap, args.robust_energy)
    rng = np.random.default_rng(args.seed)
    started = time.time()
    best = 0
    print('dimensions', model.num_v, model.num_t, flush=True)
    for trial in range(args.starts):
        if args.input and trial == 0:
            source = json.load(open(args.input))
            values = model.pack(np.array(source['pair_matrix']), source['amplitudes'])
        else:
            coordinates = rng.normal(size=model.num_v)*rng.uniform(0.15,0.65)
            matrix, _ = model.unpack(np.concatenate((coordinates,np.zeros(2*model.num_t))))
            try:
                values = model.pack(matrix)
            except Exception:
                continue
        iteration = [0]
        def callback(current):
            iteration[0] += 1
            if iteration[0] % 25 == 0:
                objective, eq, ineq, info = model.calc(current)
                print('iter', trial, iteration[0], 'time', round(time.time()-started,1), 'info',np.array(info).round(7).tolist(),'eq',float(np.max(np.abs(eq))),'ineq',float(np.min(ineq)),flush=True)
            if iteration[0] % 50 == 0:
                matrix, amplitudes = model.unpack(current)
                json.dump(artifact(matrix,amplitudes),open('latest.json','w'))
        answer = minimize(lambda current: float(model.calc(current)[0]), values, jac=lambda current: np.array(model.objgrad(current)), method='SLSQP', bounds=model.bounds,
                constraints=[{'type':'eq','fun':lambda current:np.array(model.calc(current)[1]),'jac':lambda current:np.array(model.eqjac(current))},
                             {'type':'ineq','fun':lambda current:np.array(model.calc(current)[2]),'jac':lambda current:np.array(model.ineqjac(current))}],
                callback=callback, options={'ftol':1e-11,'maxiter':args.iterations,'disp':False})
        matrix, amplitudes = model.unpack(answer.x)
        hamiltonian = model.oracle.hamiltonian(CONSTRAINTS['orbital_energies'],matrix)[0]
        result = model.oracle.solve(hamiltonian, amplitudes)
        diagnostics = model.oracle.diagnostics(hamiltonian,result)
        failures = endpoint_failures(diagnostics)
        print('DONE', trial, answer.message, 'time',time.time()-started,'fail',failures,'delta',diagnostics['occupation_violation'],'dad',diagnostics['rdm_dad'],'energy',diagnostics['energy_error'],flush=True)
        json.dump(artifact(matrix,result.amplitudes),open(f'candidate_{args.seed}_{trial}.json','w'))
        json.dump(diagnostics,open(f'diagnostics_{args.seed}_{trial}.json','w'))
        if not failures and diagnostics['occupation_violation']>best:
            best=diagnostics['occupation_violation']
            json.dump(artifact(matrix,result.amplitudes),open('best.json','w'))
            path=check_continuation(matrix,result.amplitudes,model.oracle)
            print('BEST',best,'path',path['passed'],flush=True)
        if not failures and diagnostics['occupation_violation'] > .025:
            break

if __name__ == '__main__':
    main()
