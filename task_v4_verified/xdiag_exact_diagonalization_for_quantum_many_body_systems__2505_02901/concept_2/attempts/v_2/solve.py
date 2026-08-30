import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import minimize


class Compiler:
    def __init__(self, directory, mode='linear', members=None):
        directory = Path(directory)
        self.spec = json.loads((directory / 'spec.json').read_text())
        with np.load(directory / 'hamiltonians.npz') as archive:
            self.drifts = archive['drifts']
            self.controls = archive['controls']
            self.initial = archive['initial']
        with np.load(directory / 'targets.npz') as archive:
            self.targets = archive['targets']
        self.members = list(range(len(self.drifts))) if members is None else members
        self.mode = mode
        self.duration = self.spec['slice_duration']
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.calls = 0
        self.best = np.inf
        self.start = time.monotonic()
        self.output = None

    def forward(self, arguments):
        amplitudes, member = arguments
        states = self.initial.copy()
        records = []
        for row in amplitudes:
            hamiltonian = self.drifts[member] + np.einsum('c,cij->ij', row, self.controls)
            energies, vectors = eigh(hamiltonian, check_finite=False, driver='evd')
            phases = np.exp(-1j * self.duration * energies)
            before = vectors.conj().T @ states
            states = vectors @ (phases[:, None] * before)
            records.append((energies, vectors, phases, before))
        return states, records

    def member(self, arguments):
        amplitudes, member = arguments
        states, records = self.forward(arguments)
        target = self.targets[member]
        trace = np.vdot(target, states)
        columns = states.shape[1]
        if self.mode == 'linear':
            loss = 1 - trace.real / columns
            adjoint = -target / columns
        elif self.mode == 'aligned':
            loss = 1 - abs(trace) / columns
            adjoint = -(trace / max(abs(trace), 1e-30)) * target / columns
        elif self.mode == 'columns':
            overlaps = np.sum(target.conj() * states, axis=0)
            loss = 1 - np.mean(abs(overlaps) ** 2)
            adjoint = -2 * target * overlaps[None, :] / columns
        elif self.mode == 'subspace':
            overlap = target.conj().T @ states
            loss = 1 - np.sum(abs(overlap) ** 2) / columns
            adjoint = -2 * target @ overlap / columns
        else:
            loss = 1 - abs(trace / columns) ** 2
            adjoint = -2 * trace * target / columns ** 2
        gradient = self.backward(records, adjoint)
        return loss, gradient, states

    def backward(self, records, adjoint):
        gradient = np.empty((len(records), 3))
        for step in range(len(records) - 1, -1, -1):
            energies, vectors, phases, before = records[step]
            after = vectors.conj().T @ adjoint
            differences = energies[:, None] - energies[None, :]
            divided = (-1j * self.duration) * np.exp(-0.5j * self.duration * (energies[:, None] + energies[None, :]))
            divided *= np.sinc(self.duration * differences / (2 * np.pi))
            kernel = (after.conj() @ before.T) * divided
            original = vectors.conj() @ kernel @ vectors.T
            gradient[step] = np.einsum('cij,ij->c', self.controls, original).real
            adjoint = vectors @ (phases.conj()[:, None] * after)
        return gradient

    def objective(self, flattened):
        amplitudes = flattened.reshape(self.spec['slices'], self.spec['channels'])
        results = list(self.executor.map(self.member, [(amplitudes, member) for member in self.members]))
        loss = np.mean([result[0] for result in results])
        gradient = np.mean([result[1] for result in results], axis=0)
        self.calls += 1
        if loss < self.best:
            self.best = loss
            if self.output is not None:
                self.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}) + '\n')
        if self.calls % 20 == 0:
            print('eval', self.calls, 'seconds', round(time.monotonic() - self.start, 2), 'loss', loss, 'best', self.best, 'grad', np.linalg.norm(gradient), flush=True)
        return loss, gradient.ravel()

    def report(self, amplitudes):
        results = list(self.executor.map(self.member, [(amplitudes, member) for member in range(len(self.drifts))]))
        members = []
        for member, result in enumerate(results):
            overlap = self.targets[member].conj().T @ result[2]
            trace = np.trace(overlap)
            aligned = np.exp(-1j * np.angle(trace)) * overlap
            floor = max(0., np.linalg.eigvalsh((aligned + aligned.conj().T) / 2)[0]) ** 2
            members.append({'isometry_fidelity': float(abs(trace / 6) ** 2), 'minimum_column_fidelity': float(np.min(abs(np.diag(overlap)) ** 2)), 'superposition_floor': float(floor)})
        limits = np.array(self.spec['amplitude_limits'])
        jumps = np.diff(np.vstack((np.zeros((1, 3)), amplitudes, np.zeros((1, 3)))), axis=0)
        exposure = float(self.duration * np.sum((amplitudes / limits) ** 2))
        valid = bool(np.all(abs(amplitudes) <= limits + 1e-10) and np.all(abs(jumps) <= np.array(self.spec['adjacent_jump_limits']) + 1e-10) and exposure <= self.spec['normalized_control_exposure_limit'] + 1e-10)
        return {'core_score': float(np.mean([entry['isometry_fidelity'] for entry in members])), 'worst_family_score': min(entry['superposition_floor'] for entry in members), 'members': members, 'physical_valid': valid, 'normalized_control_exposure': exposure, 'maximum_amplitude_by_channel': np.max(abs(amplitudes), axis=0).tolist(), 'maximum_jump_by_channel': np.max(abs(jumps), axis=0).tolist()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=['linear', 'aligned', 'fidelity'], default='linear')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--scale', type=float, default=0.)
    parser.add_argument('--iterations', type=int, default=1500)
    parser.add_argument('--initial', type=Path)
    parser.add_argument('--member', type=int)
    parser.add_argument('--check', action='store_true')
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input, arguments.mode, None if arguments.member is None else [arguments.member])
    generator = np.random.default_rng(arguments.seed)
    amplitudes = np.zeros((24, 3))
    if arguments.initial is not None:
        amplitudes = np.array(json.loads(arguments.initial.read_text())['amplitudes'])
    if arguments.scale:
        coarse = generator.normal(size=(6, 3))
        amplitudes += arguments.scale * np.column_stack([np.interp(np.linspace(0, 5, 24), np.arange(6), coarse[:, channel]) for channel in range(3)])
    if arguments.check:
        direction = generator.normal(size=72)
        direction /= np.linalg.norm(direction)
        loss, gradient = compiler.objective(amplitudes.ravel())
        epsilon = 1e-5
        positive = compiler.objective(amplitudes.ravel() + epsilon * direction)[0]
        negative = compiler.objective(amplitudes.ravel() - epsilon * direction)[0]
        print('gradient check', np.dot(gradient, direction), (positive - negative) / (2 * epsilon), flush=True)
    compiler.output = arguments.output
    bounds = [(-limit, limit) for step in range(24) for limit in compiler.spec['amplitude_limits']]
    result = minimize(compiler.objective, amplitudes.ravel(), jac=True, method='L-BFGS-B', bounds=bounds, options={'maxiter': arguments.iterations, 'ftol': 1e-15, 'gtol': 1e-9, 'maxls': 30, 'maxcor': 30})
    amplitudes = result.x.reshape(24, 3)
    arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}, indent=2) + '\n')
    report = compiler.report(amplitudes)
    report['optimizer_message'] = str(result.message)
    report['seconds'] = time.monotonic() - compiler.start
    arguments.output.with_suffix('.report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
