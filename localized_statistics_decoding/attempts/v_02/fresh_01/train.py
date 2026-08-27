import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, softmax


class Calibration:
    def __init__(self, metadata, setting, syndrome):
        self.groups = metadata['rate_groups']
        self.setting = setting
        self.syndrome = syndrome
        self.samples, self.length = setting.shape
        self.tables = []
        self.width = 1 << max(probe['num_detectors'] for probe in metadata['probes'])
        probes = {probe['id']: probe for probe in metadata['probes']}
        for control in metadata['settings']:
            probe = probes[control['probe']]
            faults = probe['faults']
            patterns = ((np.arange(1 << len(faults))[:, None] >> np.arange(len(faults))) & 1).astype(float)
            counts = np.stack([patterns[:, [index for index, fault in enumerate(faults) if fault['rate_group'] == group]].sum(axis=1)
                               for group in range(self.groups)], axis=1)
            packed = np.zeros(len(patterns), dtype=np.int64)
            for index, fault in enumerate(faults):
                support = sum(1 << detector for detector in fault['detectors'])
                packed ^= patterns[:, index].astype(np.int64) * support
            groups = np.array([fault['rate_group'] for fault in faults])
            bias = np.array([fault['bias'] for fault in faults])
            self.tables.append((control['dose'], counts, patterns @ bias, packed, groups, bias))
        self.observation = setting * self.width + syndrome

    def unpack(self, parameters, modes, kind):
        offset_end = modes * self.groups
        offsets = parameters[:offset_end].reshape(modes, self.groups)
        slopes = parameters[offset_end:offset_end + self.groups]
        initial = softmax(parameters[offset_end + self.groups:offset_end + self.groups + modes])
        if kind == 'hmm':
            transition = softmax(parameters[offset_end + self.groups + modes:].reshape(modes, modes), axis=1)
        else:
            transition = np.tile(initial, (modes, 1))
        return offsets, slopes, initial, transition

    def evaluate(self, parameters, modes, kind, gradient=True, per_sequence=False):
        offsets, slopes, initial, transition = self.unpack(parameters, modes, kind)
        emissions = np.empty((len(self.tables), self.width, modes))
        derivatives = np.empty((len(self.tables), self.width, modes, self.groups)) if gradient else None
        for setting_index, (dose, counts, bias_energy, packed, groups, bias) in enumerate(self.tables):
            for mode in range(modes):
                group_logits = offsets[mode] + dose * slopes
                logits = group_logits[groups] + bias
                weights = np.exp(counts @ group_logits + bias_energy - np.logaddexp(0, logits).sum())
                probability = np.bincount(packed, weights=weights, minlength=self.width)
                emissions[setting_index, :, mode] = probability
                if gradient:
                    average = np.bincount(groups, weights=expit(logits), minlength=self.groups)
                    for group in range(self.groups):
                        derivatives[setting_index, :, mode, group] = np.bincount(
                            packed, weights=weights * (counts[:, group] - average[group]), minlength=self.width)
        selected = emissions.reshape(-1, modes)[self.observation]
        forward = np.empty_like(selected)
        scales = np.empty((self.samples, self.length))
        forward[:, 0] = selected[:, 0] * initial
        scales[:, 0] = forward[:, 0].sum(axis=1)
        forward[:, 0] /= scales[:, 0, None]
        for shot in range(1, self.length):
            forward[:, shot] = (forward[:, shot - 1] @ transition) * selected[:, shot]
            scales[:, shot] = forward[:, shot].sum(axis=1)
            forward[:, shot] /= scales[:, shot, None]
        likelihood = np.log(scales).sum()
        if not gradient:
            return np.log(scales).sum(axis=1) if per_sequence else likelihood
        backward = np.ones_like(selected)
        transition_counts = np.zeros((modes, modes))
        for shot in range(self.length - 2, -1, -1):
            suffix = selected[:, shot + 1] * backward[:, shot + 1] / scales[:, shot + 1, None]
            backward[:, shot] = suffix @ transition.T
            transition_counts += transition * (forward[:, shot].T @ suffix)
        posterior = forward * backward
        offset_gradient = np.zeros_like(offsets)
        slope_gradient = np.zeros_like(slopes)
        for mode in range(modes):
            weighted_counts = np.bincount(self.observation.ravel(), weights=posterior[:, :, mode].ravel(),
                                          minlength=len(self.tables) * self.width).reshape(len(self.tables), self.width)
            weighted_counts /= np.maximum(emissions[:, :, mode], 1e-300)
            for setting_index, table in enumerate(self.tables):
                score = weighted_counts[setting_index] @ derivatives[setting_index, :, mode]
                offset_gradient[mode] += score
                slope_gradient += table[0] * score
        if kind == 'hmm':
            initial_gradient = posterior[:, 0].sum(axis=0) - self.samples * initial
            transition_gradient = transition_counts - transition_counts.sum(axis=1, keepdims=True) * transition
            result = np.concatenate([offset_gradient.ravel(), slope_gradient, initial_gradient, transition_gradient.ravel()])
        else:
            initial_gradient = posterior.sum(axis=(0, 1)) - self.samples * self.length * initial
            result = np.concatenate([offset_gradient.ravel(), slope_gradient, initial_gradient])
        return -likelihood / self.samples, -result / self.samples

    def starting_point(self, modes, kind, seed):
        generator = np.random.default_rng(seed)
        offsets = np.linspace(-3.7, -1.3, modes)[:, None] + generator.normal(0, 0.4, (modes, self.groups))
        if modes == 1:
            offsets[:] = -2.5
        slopes = np.full(self.groups, 0.5) + generator.normal(0, 0.15, self.groups)
        initial = np.zeros(modes)
        parts = [offsets.ravel(), slopes, initial]
        if kind == 'hmm':
            parts.append((np.eye(modes) * 2.5).ravel())
        return np.concatenate(parts)

    def fit(self, modes, kind, seed, start=None, iterations=250):
        if start is None:
            start = self.starting_point(modes, kind, seed)
        bounds = [(-10, 5)] * (modes * self.groups) + [(-5, 5)] * self.groups
        bounds += [(-12, 12)] * (len(start) - len(bounds))
        started = time.monotonic()
        result = minimize(self.evaluate, start, args=(modes, kind), jac=True, method='L-BFGS-B', bounds=bounds,
                          options={'maxiter': iterations, 'ftol': 1e-11, 'gtol': 1e-6, 'maxls': 30})
        print(json.dumps({'modes': modes, 'kind': kind, 'seed': seed, 'nll_per_sequence': result.fun,
                          'iterations': result.nit, 'success': bool(result.success), 'seconds': time.monotonic() - started}), flush=True)
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--calibration', required=True)
    parser.add_argument('--records', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--quick', action='store_true')
    arguments = parser.parse_args()
    metadata = json.loads(Path(arguments.calibration).read_text())
    records = np.load(arguments.records)
    setting, syndrome = records['setting'].astype(int), records['syndrome'].astype(int)
    permutation = np.random.default_rng(7143).permutation(len(setting))
    split = int(0.8 * len(setting))
    training_indices, holdout_indices = permutation[:split], permutation[split:]
    training = Calibration(metadata, setting[training_indices], syndrome[training_indices])
    holdout = Calibration(metadata, setting[holdout_indices], syndrome[holdout_indices])
    fits = []
    hypotheses = [(1, 'iid'), (2, 'iid'), (3, 'iid'), (2, 'hmm'), (3, 'hmm')]
    for modes, kind in hypotheses:
        candidates = [training.fit(modes, kind, seed=seed) for seed in (range(1) if arguments.quick or modes == 1 else range(3))]
        best = min(candidates, key=lambda result: result.fun)
        test_likelihood = holdout.evaluate(best.x, modes, kind, gradient=False)
        summary = {'modes': modes, 'kind': kind, 'training_nll_per_sequence': float(best.fun),
                   'holdout_nll_per_sequence': float(-test_likelihood / len(holdout_indices)),
                   'parameters': best.x.tolist()}
        print(json.dumps(summary), flush=True)
        fits.append(summary)
        Path(arguments.output).with_name('calibration_comparison.json').write_text(json.dumps(fits, indent=2) + '\n')
    chosen = min(fits, key=lambda result: result['holdout_nll_per_sequence'])
    modes, kind = chosen['modes'], chosen['kind']
    complete = Calibration(metadata, setting, syndrome)
    final = complete.fit(modes, kind, seed=0, start=np.array(chosen['parameters']), iterations=350)
    offsets, slopes, initial, transition = complete.unpack(final.x, modes, kind)
    order = np.argsort(offsets.mean(axis=1))
    model = {'offsets': offsets[order].tolist(), 'slopes': slopes.tolist(), 'initial': initial[order].tolist(),
             'transition': transition[order][:, order].tolist(), 'kind': kind,
             'training_nll_per_sequence': float(final.fun), 'sequence_split_seed': 7143}
    Path(arguments.output).write_text(json.dumps(model, indent=2) + '\n')
    print(json.dumps(model), flush=True)


if __name__ == '__main__':
    main()
