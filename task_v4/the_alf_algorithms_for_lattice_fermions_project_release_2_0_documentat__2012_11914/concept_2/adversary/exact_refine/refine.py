import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logsumexp


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def save(name, payload):
    (HERE / name).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def protected_hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for directory in (ROOT / "participant", ROOT / "evaluator") for path in sorted(directory.rglob("*")) if path.is_file()}


class ComputeLimit(Exception):
    pass


class PassingMargin(Exception):
    pass


class ExactModel:
    def __init__(self):
        self.rules = json.loads((ROOT / "evaluator/hidden/contract.json").read_text())
        self.instances = json.loads((ROOT / "evaluator/hidden/instances.json").read_text())["instances"]
        self.labels = self.rules["components"]
        self.family_names = [family["name"] for family in self.rules["sampling"]["families"]]
        self.targets = self.rules["scoring"]["targets"]
        raw = (ROOT / "champions/generation_1/submission.json").read_bytes()
        self.initial_payload = json.loads(raw)
        (HERE / "initialization.json").write_bytes(raw)
        self.word = [stage["component"] for stage in self.initial_payload["stages"][:17]]
        self.groups = [np.array([index for index, label in enumerate(self.word) if label == component]) for component in self.labels]
        self.multiplicity = np.array([2.0] * 16 + [1.0])
        self.floor = self.rules["constraints"]["minimum_coefficient"]
        self.numeric_floor = self.rules["scoring"]["numerical_floor"]
        dimension = 24
        count = len(self.instances)
        matrices = np.zeros((count, 5, dimension, dimension), dtype=complex)
        partners = np.broadcast_to(np.arange(dimension), (count, 4, dimension)).copy()
        amplitudes = np.zeros((count, 4, dimension))
        phases = np.zeros_like(amplitudes)
        onsite = np.zeros((count, dimension))
        physical_sizes = []
        families = []
        for sample, instance in enumerate(self.instances):
            physical_size = math.prod(instance["shape"])
            physical_sizes.append(physical_size)
            families.append(self.family_names.index(instance["family"]))
            onsite[sample, :physical_size] = instance["site_potential"]
            matrices[sample, 4] = np.diag(onsite[sample])
            for label, source, target, amplitude, phase in instance["bonds"]:
                component = self.labels.index(label)
                value = -amplitude * np.exp(1j * phase)
                matrices[sample, component, source, target] = value
                matrices[sample, component, target, source] = value.conjugate()
                partners[sample, component, source] = target
                partners[sample, component, target] = source
                amplitudes[sample, component, source] = amplitudes[sample, component, target] = amplitude
                phases[sample, component, source] = -phase
                phases[sample, component, target] = phase
        values, vectors = np.linalg.eigh(matrices.sum(axis=1))
        steps_per_case = len(self.rules["sampling"]["dtau"])
        self.steps = np.tile(self.rules["sampling"]["dtau"], count)
        self.partners = np.repeat(partners, steps_per_case, axis=0)
        self.amplitudes = np.repeat(amplitudes, steps_per_case, axis=0)
        self.phases = np.repeat(phases, steps_per_case, axis=0)
        self.onsite = np.repeat(onsite, steps_per_case, axis=0)
        values = np.repeat(values, steps_per_case, axis=0)
        vectors = np.repeat(vectors, steps_per_case, axis=0)
        self.batch = len(self.steps)
        self.identity = np.broadcast_to(np.eye(dimension, dtype=complex), (self.batch, dimension, dimension))
        sizes = np.repeat(physical_sizes, steps_per_case)
        mask = (np.arange(dimension)[None, :] < sizes[:, None])
        mask = mask[:, :, None] & mask[:, None, :]
        self.exact = []
        self.exact_norms = []
        self.observables = []
        for repeats in self.rules["sampling"]["repetitions"]:
            logs = -repeats * self.steps[:, None] * values
            for observable, diagonal in (("propagator", np.exp(logs)), ("green", expit(-logs))):
                target = (vectors * diagonal[:, None, :]) @ vectors.conj().swapaxes(-1, -2)
                target = (target + target.conj().swapaxes(-1, -2)) / 2
                self.exact.append(target)
                self.exact_norms.append(np.sqrt(np.sum(np.abs(target) ** 2 * mask, axis=(-2, -1))))
                self.observables.append((repeats, observable))
        self.exact = np.array(self.exact)
        self.exact_norms = np.array(self.exact_norms)
        self.point_families = np.tile(np.repeat(families, steps_per_case), len(self.observables))
        self.family_masks = [self.point_families == index for index in range(len(self.family_names))]
        reference = []
        order = self.rules["baseline"]["order"]
        for repeat in range(4):
            for index, label in enumerate(order + order[-2::-1]):
                weight = 0.25 if index == 4 else 0.125
                if reference and reference[-1][0] == label:
                    reference[-1][1] += weight
                else:
                    reference.append([label, weight])
        reference_word = [label for label, weight in reference[:17]]
        reference_weights = np.array([weight for label, weight in reference[:17]])
        baseline_factor, baseline_prefix = self.forward(reference_weights, reference_word)
        baseline_values, baseline_residuals, unused = self.residuals(baseline_factor)
        baseline_squared = np.sum(np.abs(baseline_residuals) ** 2, axis=(-2, -1))
        self.floor_squared = (self.numeric_floor * self.exact_norms) ** 2
        self.baseline_squared = np.maximum(baseline_squared, self.floor_squared)
        self.evaluations = 0
        self.last_parameters = None
        self.last_result = None

    def encode(self, weights):
        parameters = []
        for positions in self.groups:
            logarithms = np.log(np.asarray(weights)[positions] - self.floor)
            parameters.extend(logarithms[:-1] - logarithms[-1])
        return np.array(parameters)

    def decode(self, parameters):
        weights = np.empty(17)
        derivative = np.zeros((17, len(parameters)))
        offset = 0
        for positions in self.groups:
            free_count = len(positions) - 1
            logarithms = np.append(parameters[offset:offset + free_count], 0.0)
            fractions = np.exp(logarithms - logarithms.max())
            fractions /= np.dot(fractions, self.multiplicity[positions])
            remaining = 1 - self.floor * self.multiplicity[positions].sum()
            weights[positions] = self.floor + remaining * fractions
            for local_index in range(free_count):
                values = -remaining * fractions * self.multiplicity[positions[local_index]] * fractions[local_index]
                values[local_index] += remaining * fractions[local_index]
                derivative[positions, offset + local_index] = values
            offset += free_count
        return weights, derivative

    def payload(self, parameters):
        weights, derivative = self.decode(parameters)
        half = [{"component": label, "coefficient": float(weight)} for label, weight in zip(self.word, weights)]
        return {"schema_version": 1, "stages": half + half[-2::-1]}

    def layer(self, matrix, label, weight, center=False, derivative=False):
        scale = self.steps * (0.5 if center else 1.0)
        component = self.labels.index(label)
        if component == 4:
            diagonal = np.exp(-weight * scale[:, None] * self.onsite)
            if derivative:
                diagonal *= -scale[:, None] * self.onsite
            return matrix * diagonal[:, None, :]
        generator = scale[:, None] * self.amplitudes[:, component]
        angle = weight * generator
        if derivative:
            diagonal = generator * np.sinh(angle)
            offdiagonal = generator * np.cosh(angle) * np.exp(1j * self.phases[:, component])
        else:
            diagonal = np.cosh(angle)
            offdiagonal = np.sinh(angle) * np.exp(1j * self.phases[:, component])
        indices = self.partners[:, component, None, :]
        if matrix.ndim == 4:
            indices = indices[None, ...]
        shifted = np.take_along_axis(matrix, indices, axis=-1)
        return matrix * diagonal[:, None, :] + shifted * offdiagonal[:, None, :]

    def forward(self, weights, word):
        factor = self.identity.copy()
        prefixes = []
        for index, (label, weight) in enumerate(zip(word, weights)):
            prefixes.append(factor)
            factor = self.layer(factor, label, weight, center=index == 16)
        return factor, prefixes

    def residuals(self, factor):
        vectors, singular_values, right_vectors = np.linalg.svd(factor, full_matrices=False)
        if np.any(singular_values <= 0):
            raise ArithmeticError("unresolved positive spectrum")
        eigenvalues = singular_values ** 2
        logarithms = 2 * np.log(singular_values)
        residuals = []
        differences = []
        diagonal_indices = np.arange(factor.shape[-1])
        left = eigenvalues[:, :, None]
        right = eigenvalues[:, None, :]
        for index, (repeats, observable) in enumerate(self.observables):
            polynomial = sum(left ** power * right ** (repeats - 1 - power) for power in range(repeats))
            if observable == "propagator":
                diagonal = np.exp(repeats * logarithms)
                difference = polynomial
            else:
                diagonal = expit(-repeats * logarithms)
                difference = -polynomial * diagonal[:, :, None] * diagonal[:, None, :]
            residual = -(vectors.conj().swapaxes(-1, -2) @ self.exact[index] @ vectors)
            residual[:, diagonal_indices, diagonal_indices] += diagonal
            residuals.append(residual)
            differences.append(difference)
        return vectors, np.array(residuals), np.array(differences)

    def evaluate(self, parameters, derivatives=True):
        weights, parameter_jacobian = self.decode(parameters)
        factor, prefixes = self.forward(weights, self.word)
        vectors, residuals, differences = self.residuals(factor)
        raw_squared = np.sum(np.abs(residuals) ** 2, axis=(-2, -1))
        squared_ratios = np.maximum(raw_squared, self.floor_squared) / self.baseline_squared
        if not derivatives:
            return squared_ratios.reshape(-1)
        basis_gradient = 2 * residuals * differences / self.baseline_squared[:, :, None, None]
        basis_gradient *= (raw_squared > self.floor_squared)[:, :, None, None]
        basis_gradient = (basis_gradient + basis_gradient.conj().swapaxes(-1, -2)) / 2
        propagator_gradient = vectors[None, ...] @ basis_gradient @ vectors.conj().swapaxes(-1, -2)[None, ...]
        adjoint = 2 * propagator_gradient @ factor[None, ...]
        weight_jacobian = np.zeros((len(self.observables), self.batch, 17))
        for index in range(16, -1, -1):
            tangent = self.layer(prefixes[index], self.word[index], weights[index], center=index == 16, derivative=True)
            weight_jacobian[:, :, index] = np.real(np.sum(adjoint.conj() * tangent[None, ...], axis=(-2, -1)))
            adjoint = self.layer(adjoint, self.word[index], weights[index], center=index == 16)
        jacobian = weight_jacobian.reshape(-1, 17) @ parameter_jacobian
        self.evaluations += 1
        return squared_ratios.reshape(-1), jacobian

    def get(self, parameters):
        if self.last_parameters is None or not np.array_equal(parameters, self.last_parameters):
            self.last_result = self.evaluate(parameters)
            self.last_parameters = parameters.copy()
        return self.last_result

    def metrics(self, squared):
        family_squared = np.array([np.mean(squared[mask]) for mask in self.family_masks])
        family_scores = 1 / np.sqrt(family_squared)
        core = float(np.exp(np.mean(np.log(family_scores))))
        worst = float(family_scores.min())
        maximum = float(np.sqrt(squared.max()))
        violation = max(self.targets["core_score_min"] / core, self.targets["worst_family_score_min"] / worst, maximum / self.targets["max_point_ratio_max"])
        return {"core_score":core,"worst_family_score":worst,"max_point_ratio":maximum,"family_scores":dict(zip(self.family_names,family_scores.tolist())),"maximum_gate_ratio":violation,"passes_model":violation <= 1.0}

    def loss(self, squared, jacobian, power):
        family_squared = np.array([np.mean(squared[mask]) for mask in self.family_masks])
        count = len(squared)
        family_count = len(self.family_masks)
        point_logs = 0.5 * power * np.log(squared)
        family_logs = power * (math.log(self.targets["worst_family_score_min"]) + 0.5 * np.log(family_squared)) + math.log(count / family_count)
        core_log = power * (math.log(self.targets["core_score_min"]) + 0.5 * np.mean(np.log(family_squared))) + math.log(count)
        logarithms = np.concatenate((point_logs, family_logs, [core_log]))
        normalization = logsumexp(logarithms)
        probabilities = np.exp(logarithms - normalization)
        derivative = probabilities[:count] / (2 * squared)
        for index, mask in enumerate(self.family_masks):
            derivative[mask] += (probabilities[count + index] + probabilities[-1] / family_count) / (2 * family_squared[index] * np.count_nonzero(mask))
        return float((normalization - math.log(3 * count)) / power), derivative @ jacobian


def check_gradient(model, parameters):
    squared, jacobian = model.evaluate(parameters)
    loss, analytic = model.loss(squared, jacobian, 16)
    records = []
    difference_columns = []
    increment = 1e-4
    for index in range(len(parameters)):
        displacement = np.zeros_like(parameters)
        displacement[index] = increment
        plus = model.evaluate(parameters + displacement, derivatives=False)
        minus = model.evaluate(parameters - displacement, derivatives=False)
        difference = (plus - minus) / (2 * increment)
        difference_columns.append(difference)
        plus_loss = model.loss(plus, jacobian, 16)[0]
        minus_loss = model.loss(minus, jacobian, 16)[0]
        numerical = (plus_loss - minus_loss) / (2 * increment)
        records.append({"coordinate":index,"analytic":float(analytic[index]),"central_difference":float(numerical),"absolute_error":float(abs(analytic[index]-numerical))})
    numerical_jacobian = np.array(difference_columns).T
    relative = float(np.linalg.norm(jacobian - numerical_jacobian) / max(np.linalg.norm(numerical_jacobian), 1e-30))
    objective_relative = float(np.linalg.norm(analytic - np.array([record['central_difference'] for record in records])) / max(np.linalg.norm(analytic),1e-30))
    report = {"method":"central differences before any optimization","increment":increment,"coordinates":records,"point_jacobian_relative_frobenius_error":relative,"objective_gradient_relative_error":objective_relative,"passed":relative < 5e-4 and objective_relative < 5e-4,"points":len(squared),"parameters":len(parameters)}
    save("gradient_check.json",report)
    print("GRADIENT_CHECK",json.dumps(report),flush=True)
    if not report['passed']:
        raise ArithmeticError("analytic gradient check failed; optimization was not started")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds",type=float,default=600)
    arguments = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU,(720,720))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    before = protected_hashes()
    save("protected_before.json",before)
    setup_started = time.monotonic()
    model = ExactModel()
    initial_weights = np.array([stage['coefficient'] for stage in model.initial_payload['stages'][:17]])
    initial = model.encode(initial_weights)
    initial_squared, initial_jacobian = model.get(initial)
    initial_metrics = model.metrics(initial_squared)
    save("initial_metrics.json",initial_metrics)
    print("INITIAL",json.dumps(initial_metrics),flush=True)
    check_gradient(model,initial)
    started_cpu = time.process_time()
    started_wall = time.monotonic()
    budget = min(600.0,arguments.seconds)
    best = {"parameters":initial.copy(),"metrics":initial_metrics}
    save("submission.json",model.payload(initial))
    history = []
    stages = []
    last_progress = started_wall
    phase = "initial"

    def tracked(parameters):
        nonlocal best,last_progress
        if time.process_time()-started_cpu > budget-2 or time.monotonic()-started_wall > budget-2:
            raise ComputeLimit()
        squared,jacobian = model.get(parameters)
        metrics = model.metrics(squared)
        if metrics['maximum_gate_ratio'] < best['metrics']['maximum_gate_ratio']:
            best = {"parameters":parameters.copy(),"metrics":metrics}
            save("submission.json",model.payload(parameters))
            save("best_model_report.json",metrics)
            history.append({"phase":phase,"cpu_seconds":time.process_time()-started_cpu,"evaluation":model.evaluations,**metrics})
        if time.monotonic()-last_progress > 15:
            print("PROGRESS",json.dumps({"phase":phase,"cpu_seconds":time.process_time()-started_cpu,"evaluations":model.evaluations,**best['metrics']}),flush=True)
            last_progress = time.monotonic()
        if metrics['core_score'] >= 1.805 and metrics['worst_family_score'] >= 1.355 and metrics['max_point_ratio'] <= 0.997:
            raise PassingMargin()
        return squared,jacobian

    stop = "search_completed"
    try:
        current = initial.copy()
        for power in (8,16,32):
            phase = "lbfgs_power_"+str(power)
            def objective(parameters):
                squared,jacobian = tracked(parameters)
                return model.loss(squared,jacobian,power)
            result = minimize(objective,current,method='L-BFGS-B',jac=True,bounds=[(-12,12)]*len(current),options={"maxiter":70,"maxfun":130,"ftol":2e-11,"gtol":1e-7,"maxls":20})
            current = result.x
            stages.append({"phase":phase,"message":str(result.message),"iterations":int(result.nit),"function_calls":int(result.nfev)})
        for restart in range(3):
            phase = "slsqp_minimax_"+str(restart)
            current = best['parameters'].copy()
            if restart:
                current += np.random.default_rng(28640801+restart).normal(0,0.035,len(current))
            squared,jacobian = tracked(current)
            vector = np.append(current,np.sqrt(squared.max())+0.01)
            cache_vector = None
            cache_constraints = None
            cache_jacobian = None
            def constraints(vector):
                nonlocal cache_vector,cache_constraints,cache_jacobian
                if cache_vector is not None and np.array_equal(cache_vector,vector):
                    return cache_constraints
                squared,jacobian = tracked(vector[:-1])
                ratios = np.sqrt(squared)
                family_squared = np.array([np.mean(squared[mask]) for mask in model.family_masks])
                family_jacobian = np.array([np.mean(jacobian[mask],axis=0) for mask in model.family_masks])
                family_gates = 1.355*np.sqrt(family_squared)
                core_gate = 1.805*np.exp(0.5*np.mean(np.log(family_squared)))
                values = np.concatenate((vector[-1]-ratios,1-family_gates,[1-core_gate]))
                derivative = np.zeros((len(values),len(vector)))
                derivative[:len(squared),:-1] = -jacobian/(2*ratios[:,None])
                derivative[:len(squared),-1] = 1
                derivative[len(squared):-1,:-1] = -1.355*family_jacobian/(2*np.sqrt(family_squared)[:,None])
                derivative[-1,:-1] = -0.5*core_gate*np.mean(family_jacobian/family_squared[:,None],axis=0)
                cache_vector,cache_constraints,cache_jacobian = vector.copy(),values,derivative
                return values
            def constraint_jacobian(vector):
                constraints(vector)
                return cache_jacobian
            result = minimize(lambda vector:float(vector[-1]),vector,jac=lambda vector:np.r_[np.zeros(len(vector)-1),1.0],method='SLSQP',bounds=[(-12,12)]*len(current)+[(0.05,5.0)],constraints={"type":"ineq","fun":constraints,"jac":constraint_jacobian},options={"maxiter":180,"ftol":2e-9,"disp":False})
            stages.append({"phase":phase,"message":str(result.message),"iterations":int(result.nit),"function_calls":int(result.nfev)})
    except ComputeLimit:
        stop = "bounded_compute_limit"
    except PassingMargin:
        stop = "passing_model_margin_found"
    optimization_cpu = time.process_time()-started_cpu
    optimization_wall = time.monotonic()-started_wall
    save("submission.json",model.payload(best['parameters']))
    summary = {"date":"2026-08-28","purpose":"private privileged generation-2 feasibility check, not fresh-agent evidence","initialization":"champions/generation_1/submission.json","initialization_sha256":hashlib.sha256((HERE/'initialization.json').read_bytes()).hexdigest(),"data":"all official frozen generation-2 hidden matrices; privileged and not exposed to the fresh agent","fixed_word":model.word,"parameters":len(initial),"coefficient_constraints":"per-component multiplicity-weighted softmax with 1e-5 floors, exact mirrored half-word, center multiplicity one","analytic_gradient":"positive-half product reverse differentiation; P-power polynomial divided differences and minus-polynomial*g_i*g_j for Green functions, residuals differentiated in the single-step P eigenbasis","optimization_cpu_budget_seconds":budget,"optimization_cpu_seconds":optimization_cpu,"optimization_wall_seconds":optimization_wall,"setup_and_gradient_check_wall_seconds":started_wall-setup_started,"threads":1,"stop":stop,"completed_stages":stages,"initial_metrics":initial_metrics,"best_metrics":best['metrics'],"history":history,"official_validation":"pending","protected_files_unchanged":protected_hashes()==before}
    save("search_summary.json",summary)
    assert summary['protected_files_unchanged']
    print("OPTIMIZATION_FINISHED",json.dumps({key:value for key,value in summary.items() if key not in ('history','fixed_word')}),flush=True)
    process = subprocess.run([sys.executable,'-B',str(ROOT/'evaluator/evaluate.py'),'--submission',str(HERE/'submission.json'),'--output',str(HERE/'official_report.json')],text=True,capture_output=True,timeout=200)
    (HERE/'official_stdout.log').write_text(process.stdout)
    (HERE/'official_stderr.log').write_text(process.stderr)
    if process.returncode:
        summary['official_validation'] = 'checker command failed: '+str(process.returncode)
    else:
        report = json.loads((HERE/'official_report.json').read_text())
        summary['official_validation'] = report
        print('OFFICIAL_REPORT',json.dumps(report),flush=True)
    summary['protected_files_unchanged'] = protected_hashes()==before
    save('search_summary.json',summary)
    assert summary['protected_files_unchanged']


if __name__ == '__main__':
    main()
