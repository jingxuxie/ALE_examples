import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.linalg import cho_factor, cho_solve, cholesky, solve_triangular
from scipy.special import expit, softmax
from threadpoolctl import threadpool_limits


def extract(inputs, mean, basis):
    omega = inputs['omega_mev']
    observed, extras = [], []
    dimensions = basis.shape[1]
    selected = np.tril_indices(12, -1)
    for row in range(len(inputs['interaction'])):
        slots = np.flatnonzero(inputs['mask'][row])
        kernel = omega[None, :] ** 2 / (omega[None, :] ** 2 + inputs['nu_mev'][row, slots, None] ** 2)
        standard = inputs['noise_std'][row, slots]
        rho, length = inputs['noise_rho'][row], inputs['noise_length'][row]
        covariance = standard[:, None] * standard[None, :] * ((1-rho)*np.eye(len(slots)) + rho*np.exp(-np.abs(slots[:, None]-slots)/length))
        root = cholesky(covariance, lower=True)
        design = solve_triangular(root, kernel @ basis, lower=True)
        posterior = cho_solve(cho_factor(np.eye(dimensions) + design.T @ design), np.eye(dimensions))
        target = solve_triangular(root, inputs['interaction'][row, slots] - kernel @ mean, lower=True)
        observed.append(posterior @ design.T @ target)
        extras.append(np.r_[np.log(np.maximum(np.diag(posterior)[:24], 1e-8)), posterior[selected]])
    return np.array(observed), np.array(extras)


def predict(inputs):
    directory = Path(__file__).resolve().parent
    if len(inputs['interaction']) == 0:
        return np.empty((0, len(inputs['omega_mev'])))
    with np.load(directory / 'prior.npz') as archive:
        mean, basis = archive['mean'], archive['basis']
    observed, extra = extract(inputs, mean, basis)
    features = np.concatenate((observed, extra), axis=1).astype(np.float32)
    coupling = np.maximum((mean + observed @ basis.T).sum(1), .01)
    with open(directory / 'ensemble.json') as stream:
        settings = json.load(stream)
    compressed = None
    if settings.get('posterior') or settings.get('refinement'):
        from posterior import compressed_data
        compressed = compressed_data(inputs, coupling)
    probabilities = []
    weights = []
    posterior_raw = None
    for item in settings['networks']:
        path = directory / item['file']
        with np.load(path) as network:
            network_features = features
            if bool(network.get('normalized', False)):
                estimated = np.maximum(features[:, :40] @ basis.sum(0).astype(np.float32) + np.float32(mean.sum()), .1)
                network_features = np.concatenate((features[:, :40]/estimated[:, None], 1/estimated[:, None], features[:, 40:]), axis=1)
            hidden = (network_features @ network['transform']-network['center']) / network['scale']
            for layer in range(4):
                hidden = hidden @ network['weight%d'%layer].T + network['bias%d'%layer]
                if layer != 3:
                    hidden *= expit(hidden)
            kind = int(network['kind'])
            if item['file'] == settings.get('posterior', {}).get('network'):
                posterior_raw = hidden.copy()
            if kind == 0:
                probability = softmax(hidden, axis=1)
            elif kind == 1:
                probability = mixture_decode(hidden, inputs['omega_mev'])
                if settings.get('refinement'):
                    probability = refine_mixture(hidden, inputs['omega_mev'], compressed, **settings['refinement'])
            elif kind == 2:
                components = softmax(hidden[:, :768].reshape(-1, 4, 192), axis=-1)
                probability = (components * softmax(hidden[:, 768:], axis=1)[:, :, None]).sum(1)
            elif kind == 3:
                probability = expert_decode(hidden, inputs['omega_mev'])
            else:
                raise ValueError('Unsupported network type')
            probabilities.append(probability)
            weights.append(item['weight'])
    probability = np.average(probabilities, axis=0, weights=weights)
    if settings.get('posterior'):
        from posterior import predict as posterior_predict
        options = settings['posterior']
        posterior_probability = posterior_predict(inputs, posterior_raw, coupling, options.get('steps', 600), options.get('walkers', 16), compressed)
        probability = (1-options['weight'])*probability + options['weight']*posterior_probability
    blend = settings.get('moment_blend', 0)
    if blend:
        logomega = np.log(inputs['omega_mev'])
        current = probability @ logomega
        linear = (mean + observed @ basis.T) @ logomega / coupling
        target = current * (1-blend) + linear * blend
        for iteration in range(5):
            moment = probability @ logomega
            variance = probability @ (logomega**2) - moment**2
            probability *= np.exp(((target-moment)/np.maximum(variance, 1e-6))[:, None] * logomega)
            probability /= probability.sum(1)[:, None]
    return probability * coupling[:, None] * inputs['omega_mev'] / (2*inputs['domega_mev'])


def bands_decode(omega, scale, power, centers, widths, skew, weights):
    acoustic = omega[None, :] * np.exp(-(omega[None, :]/scale[:, None])**power[:, None])
    standardized = (omega[None, :, None]-centers[:, None, :])/widths[:, None, :]
    optical = np.exp(-.5*standardized**2) * (1+skew[:, None, :]*np.tanh(standardized)) * (omega/(omega**2+4))[None, :, None]
    bands = np.concatenate((acoustic[:, :, None], optical), axis=-1)
    bands /= np.maximum(bands.sum(1, keepdims=True), 1e-20)
    return (bands*weights[:, None, :]).sum(-1)


def mixture_decode(params, omega):
    lower = np.array([2.5, 10, 20, 25, 40, 65])
    upper = np.array([15, 40, 55, 70, 100, 112])
    scale = 5+35*expit(params[:, 0])
    power = 1.8+2.7*expit(params[:, 1])
    centers = lower+(upper-lower)*expit(params[:, 2:8])
    widths = .8+18*expit(params[:, 8:14])
    skew = .5*np.tanh(params[:, 14:20])
    weights = softmax(params[:, 20:], axis=1)
    return bands_decode(omega, scale, power, centers, widths, skew, weights)


def refine_mixture(initial, omega, compressed, ridge=100, steps=10):
    matrices, targets = compressed
    initial = initial.astype(np.float64)
    params = initial.copy()
    dimensions = initial.shape[1]
    identity = np.eye(dimensions)
    perturbation = np.vstack((np.zeros((1, dimensions)), .002*identity))
    for iteration in range(steps):
        varied = params[:, None, :] + perturbation[None, :, :]
        probability = mixture_decode(varied.reshape(-1, dimensions), omega).reshape(len(params), dimensions+1, len(omega))
        forward = probability @ matrices.transpose(0, 2, 1)
        residual = forward[:, 0] - targets
        jacobian = (forward[:, 1:] - forward[:, :1]).transpose(0, 2, 1)/.002
        hessian = jacobian.transpose(0, 2, 1) @ jacobian + ridge*identity
        gradient = (jacobian.transpose(0, 2, 1) @ residual[:, :, None])[:, :, 0] + ridge*(params-initial)
        change = np.clip(np.linalg.solve(hessian, gradient[:, :, None])[:, :, 0], -.5, .5)
        objective = (residual**2).sum(1) + ridge*((params-initial)**2).sum(1)
        for rate in (1, .5, .25, .125):
            proposed = params-rate*change
            proposed_probability = mixture_decode(proposed, omega)
            proposed_forward = (matrices @ proposed_probability[:, :, None])[:, :, 0]
            cost = ((proposed_forward-targets)**2).sum(1) + ridge*((proposed-initial)**2).sum(1)
            accepted = cost < objective
            params[accepted] = proposed[accepted]
            objective[accepted] = cost[accepted]
    return mixture_decode(params, omega)


def expert_decode(raw, omega):
    acoustic_limits = [(7,17,2,4), (10,28,2,4), (7,20,2,4), (10,30,2,3.7)]
    center_limits = [([21,53],[45,93]), ([3,20,57],[12,46,100]), ([27,5,76],[58,18,105]), ([12,40,77],[40,74,105])]
    width_limits = [([2.5,3.5],[9,12]), ([1,2.5,3.5],[4,9,12]), ([1.5,1.5,2.5],[7,7,11]), ([4,4,4],[13,15,13])]
    offset = 0
    probabilities = []
    for code in range(4):
        count = 2 if code == 0 else 3
        size = 3+4*count
        params = raw[:, offset:offset+size]
        offset += size
        lower, upper, low_power, high_power = acoustic_limits[code]
        scale = lower+(upper-lower)*expit(params[:, 0])
        power = low_power+(high_power-low_power)*expit(params[:, 1])
        lower, upper = map(np.array, center_limits[code])
        centers = lower+(upper-lower)*expit(params[:, 2:2+count])
        if code == 2:
            centers = np.column_stack((centers[:, 0]-.5*centers[:, 1], centers[:, 0]+.5*centers[:, 1], centers[:, 2]))
        lower, upper = map(np.array, width_limits[code])
        widths = lower+(upper-lower)*expit(params[:, 2+count:2+2*count])
        skew = .35*np.tanh(params[:, 2+2*count:2+3*count])
        weights = softmax(params[:, 2+3*count:], axis=1)
        probabilities.append(bands_decode(omega, scale, power, centers, widths, skew, weights))
    return (np.stack(probabilities, axis=1)*softmax(raw[:, 56:], axis=1)[:, :, None]).sum(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as archive:
        inputs = dict(archive)
    with threadpool_limits(limits=1):
        prediction = predict(inputs)
    np.savez_compressed(args.output, alpha2f=prediction)


if __name__ == '__main__':
    main()
