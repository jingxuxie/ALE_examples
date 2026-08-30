import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import json
import time
import numpy as np
import torch
from scipy.optimize import minimize
from scipy.special import expit
from threadpoolctl import threadpool_limits
from search import ROOT, NAMES, baseline, load_instances, stage_exp, write_submission, evaluate
torch.set_num_threads(1)
torch.set_default_dtype(torch.float64)
threadpool_limits(1)


class Objective:
    def __init__(self, instances=None):
        if instances is None:
            instances = load_instances()
        self.instances = instances
        public_names = {instance[0] for instance in load_instances()}
        self.public_mask = torch.tensor([instance[0] in public_names for instance in instances])
        self.groups = []
        baseline_word, baseline_coeff = baseline()
        for size in sorted(set(matrices.shape[-1] for _, _, matrices in instances)):
            indices, matrices_list, steps, exact_props, exact_greens, denominators = [], [], [], [], [], []
            for instance_index, (_, _, matrices) in enumerate(instances):
                if matrices.shape[-1] != size:
                    continue
                eigenvalues, eigenvectors = np.linalg.eigh(matrices.sum(axis=0))
                for step_index, step in enumerate([.4, .6, .8, 1.]):
                    indices.append(instance_index * 4 + step_index)
                    matrices_list.append(matrices)
                    steps.append(step)
                    left = np.eye(size, dtype=complex)
                    for stage in range(17):
                        left = left @ stage_exp(matrices, baseline_word[stage], step * baseline_coeff[stage] * (.5 if stage == 16 else 1.))
                    vectors, singular, _ = np.linalg.svd(left)
                    product = left @ left.conj().T
                    prop_list, green_list, denominator_list = [], [], []
                    for repetitions in [1, 4]:
                        exact_prop = (eigenvectors * np.exp(repetitions * step * eigenvalues)) @ eigenvectors.conj().T
                        exact_green = (eigenvectors * expit(-repetitions * step * eigenvalues)) @ eigenvectors.conj().T
                        prop_list.append(exact_prop)
                        green_list.append(exact_green)
                        approx_prop = np.linalg.matrix_power(product, repetitions)
                        approx_green = (vectors * expit(-2 * repetitions * np.log(singular))) @ vectors.conj().T
                        denominator_list.append([np.linalg.norm(approx_prop - exact_prop) ** 2, np.linalg.norm(approx_green - exact_green) ** 2])
                    exact_props.append(prop_list)
                    exact_greens.append(green_list)
                    denominators.append(denominator_list)
            matrices_batch = np.array(matrices_list)
            amplitudes = np.sqrt(np.sum(abs(matrices_batch[:, :4]) ** 2, axis=-2))
            partners = np.argmax(abs(matrices_batch[:, :4]), axis=-2)
            phases = np.take_along_axis(matrices_batch[:, :4], partners[..., None, :], axis=-2)[..., 0, :] / amplitudes
            self.groups.append({'indices': torch.tensor(indices), 'size': size, 'amplitudes': torch.tensor(amplitudes), 'partners': torch.tensor(partners), 'phases': torch.tensor(phases), 'potentials': torch.tensor(matrices_batch[:, 4].diagonal(axis1=-2, axis2=-1).real), 'steps': torch.tensor(steps), 'exact_props': torch.tensor(np.array(exact_props)), 'exact_greens': torch.tensor(np.array(exact_greens)), 'denominators': torch.tensor(np.array(denominators))})

    def ratios(self, word, values):
        all_ratios = torch.zeros((len(self.instances) * 4, 2, 2), dtype=torch.float64)
        for group in self.groups:
            batch = len(group['steps'])
            size = group['size']
            left = torch.eye(size, dtype=torch.complex128).expand(batch, size, size)
            for index, component in enumerate(word):
                time_value = values[index] * group['steps'][:, None]
                if component == 4:
                    left = left * torch.exp(time_value * group['potentials'])[:, None, :]
                else:
                    angles = time_value * group['amplitudes'][:, component]
                    partners = group['partners'][:, component, None, :].expand(batch, size, size)
                    swapped = torch.gather(left, 2, partners)
                    left = left * torch.cosh(angles)[:, None, :] + swapped * (torch.sinh(angles) * group['phases'][:, component])[:, None, :]
            vectors, singular, _ = torch.linalg.svd(left)
            product = left @ left.mH
            powers = [product, product @ product @ product @ product]
            ratios = []
            for repetition_index, repetitions in enumerate([1, 4]):
                propagator = powers[repetition_index]
                green = (vectors * torch.sigmoid(-2 * repetitions * torch.log(singular))[:, None, :]) @ vectors.mH
                prop_error = torch.sum(abs(propagator - group['exact_props'][:, repetition_index]) ** 2, dim=(-2, -1))
                green_error = torch.sum(abs(green - group['exact_greens'][:, repetition_index]) ** 2, dim=(-2, -1))
                ratios.append(torch.stack([prop_error, green_error], dim=-1) / group['denominators'][:, repetition_index])
            all_ratios = all_ratios.index_copy(0, group['indices'], torch.stack(ratios, dim=1))
        return all_ratios.reshape(len(self.instances), 16)

    def optimize(self, word, initial, seconds=180, penalty=.0, label='refined'):
        constraint = (np.arange(5)[:, None] == word).astype(float)
        start = time.time()
        calls = 0
        best = 1e100
        best_values = initial.copy()
        def objective(values):
            nonlocal calls, best, best_values
            parameters = torch.tensor(values, requires_grad=True)
            ratios = self.ratios(word, parameters)
            family_losses = ratios.reshape(8, -1).mean(dim=1)
            if penalty == -3:
                instance_max = .02 * torch.logsumexp(ratios / .02, dim=1)
                loss = torch.sigmoid((instance_max - .90) / .06).mean() + .03 * family_losses.mean()
                loss = loss + 100 * torch.sum(torch.relu(ratios[self.public_mask] - .98 ** 2) ** 2)
                loss = loss + 100 * torch.relu(torch.log(family_losses).mean() + 2 * np.log(1.9)) ** 2
            elif penalty < 0:
                loss = .02 * torch.logsumexp(ratios.reshape(-1) / .02, dim=0) + .3 * family_losses.mean()
                if penalty == -2:
                    loss = loss + 100 * torch.relu(torch.log(family_losses).mean() + 2 * np.log(1.9)) ** 2
            else:
                loss = family_losses.mean() + penalty * torch.mean(torch.relu(ratios - .65) ** 2)
            loss.backward()
            calls += 1
            if loss.item() < best and np.max(abs(constraint @ values - .5)) < 1e-10:
                best = loss.item()
                best_values = values.copy()
                if calls % 10 == 1:
                    print('opt', calls, round(time.time() - start, 2), best, (1 / torch.sqrt(family_losses)).detach().numpy().round(4), float(torch.sqrt(ratios.max())), flush=True)
                write_submission(np.r_[word, word[-2::-1]], np.r_[values[:16], values[16] * 2, values[15::-1]], name=label + '.json')
            if time.time() - start > seconds:
                raise TimeoutError()
            return loss.item(), parameters.grad.numpy()
        try:
            result = minimize(objective, initial, jac=True, method='SLSQP', bounds=[(1e-5 if index != 16 else 5e-6, .5) for index in range(17)], constraints={'type': 'eq', 'fun': lambda values: constraint @ values - .5, 'jac': lambda values: constraint}, options={'ftol': 1e-11, 'maxiter': 250})
            print(result.message, result.fun, 'calls', calls, 'time', time.time() - start, flush=True)
        except TimeoutError:
            print('timed out', calls, flush=True)
        return best_values


if __name__ == '__main__':
    import sys
    artifact = json.loads((ROOT / sys.argv[1]).read_text())
    word = np.array([NAMES.index(stage['component']) for stage in artifact['stages'][:17]])
    values = np.array([stage['coefficient'] for stage in artifact['stages'][:17]])
    values[16] /= 2
    objective = Objective()
    ratios = objective.ratios(word, torch.tensor(values)).detach().numpy()
    print('initial', 1 / np.sqrt(ratios.reshape(8, -1).mean(axis=1)), np.sqrt(ratios.max()), flush=True)
    values = objective.optimize(word, values, seconds=float(sys.argv[2]), penalty=float(sys.argv[3]) if len(sys.argv) > 3 else 0., label=sys.argv[4] if len(sys.argv) > 4 else 'refined')
    evaluate(np.r_[word, word[-2::-1]], np.r_[values[:16], values[16] * 2, values[15::-1]], verbose=True)
