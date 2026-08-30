import os
import sys
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from model import EVEN_MODES, features, full_hamiltonian, unpack


class Deadline(Exception):
    pass


class Epigraph:
    def __init__(self, mesh, support, deadline, gap=3.065):
        self.deadline = deadline
        self.support = np.array(sorted(support), dtype=int)
        self.gap = gap
        axis = np.linspace(0.0, np.pi, mesh)
        horizontal, vertical = np.meshgrid(axis, axis, indexing="ij")
        self.horizontal = horizontal.ravel()
        self.vertical = vertical.ravel()
        self.points = len(self.horizontal)
        self.errors = [(mass, strain) for mass in (-0.05, 0.0, 0.05) for strain in (0.0, 0.03, 0.06)]
        self.scenarios = len(self.errors)
        self.count = len(self.support)
        self.variables = self.count+2*self.scenarios+1
        _, all_basis = features(self.horizontal, self.vertical)
        self.basis = all_basis[..., self.support]
        self.base = full_hamiltonian(unpack(np.zeros(30)), self.horizontal, self.vertical)
        self.scenario_base = np.repeat(self.base[None], self.scenarios, axis=0)
        for index, (mass, strain) in enumerate(self.errors):
            self.scenario_base[index, :, 0, 0] += mass
            self.scenario_base[index, :, 1, 1] -= mass
            perturbation = strain*(np.sin(self.horizontal)+1j*np.sin(self.vertical))
            self.scenario_base[index, :, 0, 1] += perturbation
            self.scenario_base[index, :, 1, 0] += perturbation.conj()
        weights = np.array([0.0]+[np.sqrt(2.0)]*11+[1.0 if order == cross else 2.0 for order, cross in EVEN_MODES]*2)
        self.weights = weights[self.support]
        _, trim_basis = features(np.array([0.0, np.pi, np.pi]), np.array([0.0, 0.0, np.pi]))
        self.trim = trim_basis[:, 3, self.support]*np.array([1.0, -1.0, -1.0])[:, None]
        self.cached_parameters = None
        self.cached_data = None
        self.calls = 0
        self.keep = np.concatenate([np.flatnonzero(self.horizontal<=self.vertical+1e-14 if strain==0 else np.ones(self.points,dtype=bool))+index*self.points for index,(_,strain) in enumerate(self.errors)])
        rows = len(self.keep)
        scenario_ids = np.repeat(np.arange(self.scenarios), self.points)[self.keep]
        self.scenario_ids = scenario_ids
        self.alpha_columns = self.count+2*np.arange(self.scenarios)
        self.beta_columns = self.alpha_columns+1
        self.constant_jacobian = np.zeros((3*rows+self.scenarios+3, self.variables))
        self.constant_jacobian[np.arange(rows), self.alpha_columns[scenario_ids]] = -1.0
        self.constant_jacobian[rows+np.arange(rows), self.beta_columns[scenario_ids]] = 1.0
        self.constant_jacobian[2*rows+np.arange(rows), self.beta_columns[scenario_ids]] = -1.0
        self.constant_jacobian[3*rows+np.arange(self.scenarios), self.alpha_columns] = 1.0
        self.constant_jacobian[3*rows+np.arange(self.scenarios), self.beta_columns] = -1.0
        self.constant_jacobian[3*rows:3*rows+self.scenarios, -1] = 1.0
        self.constant_jacobian[-3:, :self.count] = self.trim

    def spectral(self, selected):
        if time.monotonic() >= self.deadline:
            raise Deadline()
        if self.cached_parameters is not None and np.array_equal(selected, self.cached_parameters):
            return self.cached_data
        values = np.einsum("pik,k->pi", self.basis, selected)
        matrix = self.scenario_base.copy()
        matrix[..., 0, 0] += values[:, 0]+values[:, 3]
        matrix[..., 1, 1] += values[:, 0]-values[:, 3]
        matrix[..., 0, 1] += values[:, 1]-1j*values[:, 2]
        matrix[..., 1, 0] += values[:, 1]+1j*values[:, 2]
        spectrum, vectors = np.linalg.eigh(matrix)
        first, second = vectors[..., 0, :3], vectors[..., 1, :3]
        cross = first.conj()*second
        observable = np.stack((np.abs(first)**2+np.abs(second)**2, 2*cross.real, 2*cross.imag, np.abs(first)**2-np.abs(second)**2), axis=-1)
        gradient = np.einsum("spbi,pik->spbk", observable, self.basis)
        self.cached_parameters = selected.copy()
        self.cached_data = spectrum[..., :3], gradient
        self.calls += 1
        return self.cached_data

    def objective(self, variables):
        selected = variables[:self.count]
        smooth = np.sqrt(selected**2+1e-12)
        gradient = np.zeros(self.variables)
        gradient[:self.count] = 0.008*self.weights*selected/smooth
        gradient[-1] = 1.0
        return float(variables[-1]+0.008*self.weights@smooth), gradient

    def constraints(self, variables, jacobian=False):
        spectrum, gradient = self.spectral(variables[:self.count])
        lower, upper = spectrum[..., 0], spectrum[..., 1]
        alpha, beta = variables[self.alpha_columns], variables[self.beta_columns]
        if not jacobian:
            return np.r_[(lower-alpha[:, None]).ravel()[self.keep], (beta[:, None]-lower).ravel()[self.keep], (upper-beta[:, None]-self.gap).ravel()[self.keep], variables[-1]-beta+alpha, self.trim@variables[:self.count]-0.9]
        rows = len(self.keep)
        result = self.constant_jacobian.copy()
        result[:rows, :self.count] = gradient[..., 0, :].reshape(-1, self.count)[self.keep]
        result[rows:2*rows, :self.count] = -gradient[..., 0, :].reshape(-1, self.count)[self.keep]
        result[2*rows:3*rows, :self.count] = gradient[..., 1, :].reshape(-1, self.count)[self.keep]
        return result

    def solve(self, initial, iterations):
        selected = initial[self.support]
        spectrum, _ = self.spectral(selected)
        variables = np.zeros(self.variables)
        variables[:self.count] = selected
        variables[self.alpha_columns] = spectrum[..., 0].min(axis=1)
        variables[self.beta_columns] = spectrum[..., 0].max(axis=1)
        variables[-1] = np.max(variables[self.beta_columns]-variables[self.alpha_columns])
        bounds = [(-1.9, -0.3) if index == 0 else (-1.5, 1.5) if 12 <= index < 21 else (-0.75, 0.75) for index in self.support]
        bounds += [(None, None)]*(2*self.scenarios)+[(0.0, None)]
        rows = len(self.keep)
        active = set(range(3*rows, 3*rows+self.scenarios+3))
        total_iterations = 0
        for exchange in range(7):
            residual = self.constraints(variables)
            for group in range(3):
                for scenario in range(self.scenarios):
                    candidates = np.flatnonzero(self.scenario_ids==scenario)+group*rows
                    active.update(candidates[np.argsort(residual[candidates])[:4]].tolist())
            indices = np.array(sorted(active),dtype=int)
            result = minimize(self.objective, variables, jac=True, bounds=bounds, method="SLSQP", constraints={"type":"ineq", "fun":lambda value:self.constraints(value)[indices], "jac":lambda value:self.constraints(value,True)[indices]}, options={"maxiter":iterations,"ftol":2e-10,"disp":False})
            total_iterations += result.nit
            variables = result.x
            if np.min(self.constraints(variables))>=-2e-6:
                break
        parameters = np.zeros(30)
        parameters[self.support] = result.x[:self.count]
        constraint_min = float(np.min(self.constraints(result.x)))
        return parameters, {"objective":float(result.fun),"constraint_min":constraint_min,"success":bool(result.success),"iterations":int(total_iterations),"message":str(result.message),"spectral_calls":self.calls,"exchange_rounds":exchange+1,"retained_constraints":len(active)}
