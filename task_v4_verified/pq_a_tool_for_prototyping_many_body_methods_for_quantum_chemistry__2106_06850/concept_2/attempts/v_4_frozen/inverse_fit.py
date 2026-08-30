import json
import time
import argparse
from pathlib import Path
import numpy as np
from scipy.linalg import null_space
from scipy.optimize import minimize
from search_model import oracle, axes, hbase, haxes, hfbase, hfaxes, structured
from api import artifact

parser = argparse.ArgumentParser()
parser.add_argument('--states', default='limits_kinematic_best.npz')
parser.add_argument('--prefix', default='inverse')
arguments = parser.parse_args()
states = np.load(arguments.states)
values = states['values']
active = states['active']
exact_active = states['exact_active']
selection = np.arange(120) if len(active) == 18 else np.array(structured)
count = len(active)
amplitudes = np.zeros(18)
amplitudes[active] = values[:count]
multipliers = np.zeros(18)
multipliers[active] = values[count:2*count]
exact = oracle.ref.copy()
exact[exact_active] = values[2*count:]
exact /= np.linalg.norm(exact)
orthogonal = null_space(exact.reshape(1,-1))


def linear_constraints(hamiltonian):
    residual, jacobian, transformed, _, _ = oracle.equations(hamiltonian, amplitudes)
    lambda_residual = transformed[0, oracle.targets] + jacobian.T @ multipliers
    exact_residual = hamiltonian @ exact - (exact @ hamiltonian @ exact) * exact
    return np.concatenate((residual[active], lambda_residual[active], exact_residual[exact_active]))


offset = linear_constraints(hbase)
linear = np.array([linear_constraints(haxes[index]) for index in selection]).T
initial = np.linalg.lstsq(linear, -offset, rcond=1e-11)[0]
null = null_space(linear, rcond=1e-11)
print('rank', len(selection)-null.shape[1], 'residual', np.linalg.norm(linear@initial+offset), 'norm',np.linalg.norm(initial),flush=True)
started = time.monotonic()


def report(parameters):
    coefficients = initial + null @ parameters
    hamiltonian = hbase + np.einsum('k,kij->ij',coefficients,haxes[selection])
    real_hf, imag_hf = hfbase + np.einsum('k,kbij->bij',coefficients,hfaxes[selection])
    residual,jacobian,transformed,positive,inverse = oracle.equations(hamiltonian,amplitudes)
    exact_energy = exact @ hamiltonian @ exact
    gap = np.linalg.eigvalsh(orthogonal.T @ (hamiltonian-exact_energy*np.eye(20)) @ orthogonal)[0]
    error = transformed[0,0] - exact_energy
    matrix = np.einsum('k,kij->ij',coefficients,axes[selection])
    metric = np.array([gap, np.linalg.eigvalsh(real_hf)[0], np.linalg.eigvalsh(imag_hf)[0], error, np.max(abs(matrix)), np.linalg.norm(matrix), np.linalg.cond(jacobian), min(np.linalg.eigvals(jacobian).real)])
    return metric, matrix


def constraints(parameters):
    gap, real_hf, imag_hf,error, maximum,norm,condition,eom = report(parameters)[0]
    return np.array([gap-.1001, real_hf-.0501, imag_hf-.0501, (.000099-abs(error))*1000, 1.499-maximum, (6.999-norm), (99-condition)/100, eom-.0501])


print('initial',report(np.zeros(null.shape[1]))[0].tolist(),flush=True)
def callback(parameters):
    callback.count += 1
    if callback.count % 25 == 0:
        print('progress',callback.count,report(parameters)[0].tolist(),flush=True)
callback.count=0
answer=minimize(lambda parameters:np.linalg.norm(initial+null@parameters)**2, np.zeros(null.shape[1]), method='SLSQP',constraints={'type':'ineq','fun':constraints}, callback=callback,options={'maxiter':2000,'ftol':1e-10})
metrics,matrix=report(answer.x)
print('END',answer.message, metrics.tolist(), 'margin',min(constraints(answer.x)), 'seconds',time.monotonic()-started,flush=True)
Path(f'{arguments.prefix}.json').write_text(json.dumps(artifact(matrix,amplitudes),indent=2))
