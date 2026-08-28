import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import numpy as np
import scipy
from scipy.optimize import least_squares
from scipy.spatial.distance import jensenshannon


AUDIT = Path(__file__).resolve().parent
REFERENCE = AUDIT.parent
PRIVATE = REFERENCE.parent
ROOT_PRIVATE = PRIVATE.parents[1] / 'private'
FROZEN = ROOT_PRIVATE / 'runs/pilot/submissions/concept_03_experiment.py'
POLICIES = ('juqst', 'paper', 'full', 'late_weighted')
DESCRIPTIONS = {
    'juqst': 'Pinned source: first crossing below 17*first/64 included; minimum 3.',
    'paper': 'Methods: first crossing below (first+1/16)/4 excluded; minimum 3.',
    'full': 'Same bounded two-parameter least squares, using every training depth.',
    'late_weighted': 'Same least squares with w(m)=(1+m/median(positive training depths))^-2; no tuning.',
}


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


reference = load_module('audit_reference', REFERENCE / 'solver.py')
evaluator = load_module('audit_evaluator', PRIVATE / 'evaluator.py')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def weights_for(depths, observed, policy):
    if policy in ('juqst', 'paper'):
        threshold = observed[0] * 17 / 64 if policy == 'juqst' else (observed[0] + 1 / 16) / 4
        crossed = observed < threshold
        stop = np.argmax(crossed, axis=0) + (policy == 'juqst')
        stop = np.where(crossed.any(axis=0), np.maximum(stop, 3), len(depths))
        return (np.arange(len(depths))[:, None] < stop).astype(float)
    if policy == 'full':
        return np.ones_like(observed)
    scale = np.median(depths[depths > 0])
    return np.broadcast_to((1 + depths[:, None] / scale) ** -2, observed.shape)


def amplitudes_for(depths, observed, rates, weights):
    basis = rates[None, :] ** depths[:, None]
    numerator = np.sum(weights * basis * observed, axis=0)
    denominator = np.maximum(np.sum(weights * basis * basis, axis=0), 1e-300)
    return np.clip(numerator / denominator, .01, 1.)


def fit(depths, modes, policy):
    observed = modes[:, 1:]
    weights = weights_for(depths, observed, policy)
    if policy == 'juqst':
        rates, amplitudes, stops = reference.fit_modes(depths, modes)
        assert np.array_equal(stops, weights.sum(axis=0))
        return rates, amplitudes, weights

    def objective(rates):
        amplitudes = amplitudes_for(depths, observed, rates, weights)
        residual = observed - amplitudes * rates[None, :] ** depths[:, None]
        return np.sum(weights * residual ** 2, axis=0)

    lower = np.full(observed.shape[1], .01)
    upper = np.ones_like(lower)
    ratio = (np.sqrt(5.) - 1.) / 2
    for iteration in range(65):
        left = upper - ratio * (upper - lower)
        right = lower + ratio * (upper - lower)
        keep_left = objective(left) < objective(right)
        lower = np.where(keep_left, lower, left)
        upper = np.where(keep_left, right, upper)
    rates = (lower + upper) / 2
    amplitudes = amplitudes_for(depths, observed, rates, weights)
    return np.r_[1., rates], np.r_[1., amplitudes], weights


def independent_diagnostics(probabilities, data):
    qubits = int(data['n'])
    bits = ((np.arange(len(probabilities))[:, None] >> np.arange(qubits)) & 1)

    def encode(indices):
        return bits[:, indices] @ (2 ** np.arange(len(indices) - 1, -1, -1))

    events = np.stack([bits[:, np.flatnonzero(block)].any(axis=1) for block in data['blocks']])
    means = events @ probabilities
    centered = events - means[:, None]
    covariance = (centered * probabilities) @ centered.T
    variance = np.diag(covariance)
    denominator = np.sqrt(variance[:, None] * variance)
    correlations = np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator > 0)
    information = []
    for query in data['conditional_queries']:
        groups = [np.flatnonzero(mask) for mask in query]
        joint = np.zeros(tuple(2 ** len(group) for group in groups))
        np.add.at(joint, tuple(encode(group) for group in groups), probabilities)
        given = joint.sum(axis=(0, 1), keepdims=True)
        numerator = joint * given
        denominator = joint.sum(axis=1, keepdims=True) * joint.sum(axis=0, keepdims=True)
        positive = joint > 0
        information.append(float(np.sum(joint[positive] * np.log(numerator[positive] / denominator[positive]))))
    remaining = set(range(qubits))
    while remaining:
        ready = {child for child in remaining if not remaining.intersection(np.flatnonzero(data['parents'][child]))}
        assert ready, 'parents must be a DAG'
        remaining -= ready
    model = np.ones(len(probabilities))
    zero_parent_configurations = 0
    for child, parent_mask in enumerate(data['parents']):
        parents = np.flatnonzero(parent_mask)
        labels = encode(parents)
        parent_mass = np.bincount(labels, weights=probabilities, minlength=2 ** len(parents))
        one_mass = np.bincount(labels, weights=probabilities * bits[:, child], minlength=len(parent_mass))
        conditional = np.divide(one_mass, parent_mass, out=np.full_like(parent_mass, .5), where=parent_mass > 0)
        zero_parent_configurations += int(np.sum(parent_mass == 0))
        model *= np.where(bits[:, child], conditional[labels], 1 - conditional[labels])
    assert abs(model.sum() - 1) < 1e-10
    output = dict(probabilities=probabilities, correlations=correlations,
                  conditional_information=np.asarray(information),
                  spatial_jsd=np.asarray(jensenshannon(probabilities, model, base=2)))
    official = reference.diagnostics(probabilities, data)
    differences = {key: float(np.max(np.abs(output[key] - official[key]))) for key in evaluator.KEYS}
    assert max(differences.values()) < 1e-10, differences
    checks = dict(max_absolute_differences=differences, unnormalized_dag_mass=float(model.sum()),
                  zero_parent_configurations=zero_parent_configurations)
    return output, checks


def optimizer_check(depths, modes, rates, amplitudes, weights):
    random = np.random.default_rng(190713022)
    indices = np.unique(np.r_[1, 2, 3, 7, 15, 31, 63, 127, random.choice(np.arange(1, len(rates)), 24, replace=False)])
    rate_differences = []
    objective_differences = []
    for mode in indices:
        root_weight = np.sqrt(weights[:, mode - 1])
        response = modes[:, mode]
        residual = lambda parameters: root_weight * (parameters[0] * parameters[1] ** depths - response)
        independent = least_squares(residual, [.8, .8], bounds=([.01, .01], [1., 1.]),
                                    ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=1000)
        assert independent.success
        rate_differences.append(abs(independent.x[1] - rates[mode]))
        objective_differences.append(abs(np.sum(residual(independent.x) ** 2)
                                         - np.sum(residual([amplitudes[mode], rates[mode]]) ** 2)))
    assert max(rate_differences) < 1e-5, max(rate_differences)
    assert max(objective_differences) < 1e-9, max(objective_differences)
    return dict(modes_checked=len(indices), max_rate_difference=float(max(rate_differences)),
                max_objective_difference=float(max(objective_differences)))


def score(output, target, scale):
    losses = evaluator.errors(output, target)
    components = scale / (scale + losses)
    return dict(score=float(components.mean()), components=dict(zip(evaluator.KEYS, components.tolist())),
                losses=dict(zip(evaluator.KEYS, losses.tolist())))


def run_submission(path, data, target):
    with tempfile.TemporaryDirectory(prefix='submission-', dir=AUDIT) as temporary:
        work = Path(temporary)
        shutil.copy2(path, work / 'solver.py')
        np.savez(work / 'input.npz', **data)
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', HOME=str(work), TMPDIR=str(work),
                           NUMBA_CACHE_DIR=str(work / 'cache'), XDG_CACHE_HOME=str(work / 'cache'))
        with (work / 'stdout.txt').open('w') as stdout, (work / 'stderr.txt').open('w') as stderr:
            child = subprocess.run([sys.executable, '-B', str(work / 'solver.py'), str(work / 'input.npz'),
                                    str(work / 'output.npz')], cwd=work, env=environment, stdout=stdout,
                                   stderr=stderr, timeout=120,
                                   preexec_fn=lambda: evaluator.restrict_solver(work, work))
        if child.returncode:
            raise RuntimeError((work / 'stderr.txt').read_text()[-2000:])
        output = evaluator.load_output(work / 'output.npz', target)
        evaluator.errors(output, target)
        return output


def cross_validate(data, modes, policy, target, submission):
    depths = data['depths']
    low_order = np.asarray([label.bit_count() <= 2 for label in range(1, modes.shape[1])])
    folds = []
    for held_out, depth in enumerate(depths):
        training = np.arange(len(depths)) != held_out
        training_depths = depths[training]
        training_modes = modes[training]
        record = dict(depth=int(depth))
        if policy == 'frozen_submission':
            training_data = dict(data, counts=data['counts'][training], depths=training_depths)
            probabilities = run_submission(submission, training_data, target)['probabilities']
            weights = np.ones_like(training_modes[:, 1:])
        else:
            rates, amplitudes, weights = fit(training_depths, training_modes, policy)
            probabilities = reference.simplex(reference.walsh(rates) / len(rates))
            residual = amplitudes[1:] * rates[1:] ** depth - modes[held_out, 1:]
            record.update(raw_mse=float(np.mean(residual ** 2)), raw_low_order_mse=float(np.mean(residual[low_order] ** 2)))
        physical_rates = reference.walsh(probabilities)[1:]
        for name, amplitude_weights in (('physical_policy', weights), ('physical_common', np.ones_like(weights))):
            amplitudes = amplitudes_for(training_depths, training_modes[:, 1:], physical_rates, amplitude_weights)
            residual = amplitudes * physical_rates ** depth - modes[held_out, 1:]
            record[name + '_mse'] = float(np.mean(residual ** 2))
            record[name + '_low_order_mse'] = float(np.mean(residual[low_order] ** 2))
        folds.append(record)
    summary = {}
    for key in folds[0]:
        if key.endswith('_mse'):
            values = np.asarray([fold[key] for fold in folds])
            summary[key] = float(values.mean())
            summary[key.replace('_mse', '_rmse')] = float(np.sqrt(values.mean()))
            if 'low_order' not in key:
                summary[key.replace('_mse', '_first3_rmse')] = float(np.sqrt(values[:3].mean()))
                summary[key.replace('_mse', '_last3_rmse')] = float(np.sqrt(values[-3:].mean()))
                summary[key.replace('_mse', '_interior_rmse')] = float(np.sqrt(values[1:-1].mean()))
    return dict(summary=summary, folds=folds, nonconstant_modes=modes.shape[1] - 1,
                low_order_modes=int(low_order.sum()))


def self_check():
    random = np.random.default_rng(190713022)
    probabilities = random.dirichlet(np.ones(16))
    probabilities[8:] = 0
    probabilities /= probabilities.sum()
    query = np.zeros((2, 3, 4), dtype=np.uint8)
    query[0, 0, 0] = query[0, 1, 1] = query[0, 1, 2] = query[0, 2, 3] = 1
    query[1, 0, 0] = query[1, 1, 1] = 1
    data = dict(n=np.asarray(4), blocks=np.eye(4), conditional_queries=query,
                parents=np.triu(np.ones((4, 4), dtype=np.uint8), 1))
    data['parents'][0, 1] = 0
    output, check = independent_diagnostics(probabilities, data)
    assert check['zero_parent_configurations'] > 0
    assert 0 < output['spatial_jsd'] < 1
    labels = np.arange(16)
    parity = np.asarray([[(-1.) ** int(left & right).bit_count() for left in labels] for right in labels])
    walsh_error = float(np.max(np.abs(parity @ probabilities - reference.walsh(probabilities))))
    assert walsh_error < 1e-14
    return dict(diagnostics=check, direct_walsh_max_error=walsh_error)


def main():
    parser = argparse.ArgumentParser(description='Read-only four-acquisition author audit; writes only beside this script.')
    parser.add_argument('--submission', type=Path, help='Optional final frozen root-private pilot submission; never a live attempt.')
    parser.add_argument('--output', default='results.json', help='JSON filename inside policy_audit only.')
    args = parser.parse_args()
    destination = (AUDIT / args.output).resolve()
    if destination.parent != AUDIT or destination.suffix != '.json':
        parser.error('--output must be a JSON file directly inside policy_audit')
    if args.submission is not None:
        args.submission = args.submission.resolve(strict=True)
        if args.submission != FROZEN.resolve():
            parser.error('--submission must name the final frozen concept_03_experiment.py, not a live attempt')
    protected = [REFERENCE / 'solver.py', REFERENCE / 'build.py', PRIVATE / 'evaluator.py',
                 REFERENCE / 'PROVENANCE.md', REFERENCE / 'manifest.json',
                 PRIVATE.parent / 'participant/TASK.md', PRIVATE.parent / 'participant/input/FORMAT.md']
    manifest = json.loads((REFERENCE / 'manifest.json').read_text())
    cases = [case for case in manifest if case['id'] in ('single_0', 'mixed_a_0', 'mixed_b_0', 'mixed_c_0')]
    assert len(cases) == 4
    protected += [PRIVATE / case[key] for case in cases for key in ('input', 'reference')]
    hashes = {str(path.relative_to(PRIVATE.parent.parent)): digest(path) for path in protected}
    source_manifest = json.loads((ROOT_PRIVATE / 'sources_manifest.json').read_text())
    result = dict(policy_descriptions=DESCRIPTIONS, numpy_version=np.__version__, scipy_version=scipy.__version__,
                  self_check=self_check(), protected_sha256=hashes, script_sha256=digest(Path(__file__)),
                  research_audit_sha256=digest(ROOT_PRIVATE / 'RESEARCH_AUDIT.md'),
                  source_pins={key: source_manifest[key] for key in ('1907.13022.pdf', 'Juqst.jl')},
                  submission=None if args.submission is None else dict(path=str(args.submission), sha256=digest(args.submission)),
                  cases=[])
    policies = POLICIES + (() if args.submission is None else ('frozen_submission',))
    started = time.monotonic()
    for case in cases:
        data = load_arrays(PRIVATE / case['input'])
        target = load_arrays(PRIVATE / case['reference'])
        assert digest(PRIVATE / case['input']) == case['sha256']
        histograms = data['counts'] / data['counts'].sum(axis=1, keepdims=True)
        modes = reference.walsh(histograms)
        baseline = dict(probabilities=histograms[0], correlations=np.eye(len(data['blocks'])),
                        conditional_information=np.zeros(len(data['conditional_queries'])), spatial_jsd=np.asarray(0.))
        weak_losses = evaluator.errors(baseline, target)
        scale = .12 * weak_losses + np.asarray([.001, .001, .00001, .0005])
        case_record = dict(id=case['id'], source=case['source'], depths=data['depths'].tolist(),
                           shots=data['counts'].sum(axis=1).tolist(),
                           scales=dict(zip(evaluator.KEYS, scale.tolist())),
                           weak_losses=dict(zip(evaluator.KEYS, weak_losses.tolist())),
                           optimistic_binomial_parity_rmse=float(np.sqrt(np.mean((1 - modes[:, 1:] ** 2)
                                                                 / data['counts'].sum(axis=1)[:, None]))),
                           policies={})
        reference_stops = weights_for(data['depths'], modes[:, 1:], 'juqst').sum(axis=0)
        paper_stops = weights_for(data['depths'], modes[:, 1:], 'paper').sum(axis=0)
        case_record['paper_vs_juqst_changed_windows'] = int(np.sum(reference_stops != paper_stops))
        for policy in policies:
            policy_started = time.monotonic()
            if policy == 'frozen_submission':
                output = run_submission(args.submission, data, target)
                independent, checks = independent_diagnostics(output['probabilities'], data)
                checks['submission_internal_diagnostic_errors'] = {
                    key: float(np.max(np.abs(output[key] - independent[key]))) for key in evaluator.KEYS[1:]}
                consistency_losses = evaluator.errors(output, independent)
                record = dict(diagnostics_check=checks,
                              self_consistency_losses=dict(zip(evaluator.KEYS[1:], consistency_losses[1:].tolist())),
                              recomputed_from_submission_p=score(independent, target, scale))
            else:
                rates, amplitudes, weights = fit(data['depths'], modes, policy)
                probabilities = reference.simplex(reference.walsh(rates) / len(rates))
                output, checks = independent_diagnostics(probabilities, data)
                record = dict(optimizer_check=optimizer_check(data['depths'], modes, rates, amplitudes, weights),
                              diagnostics_check=checks,
                              selected_depths_mean=float(np.mean(np.sum(weights > 0, axis=0))),
                              weight_sum_mean=float(weights.sum(axis=0).mean()),
                              full_fit_raw_rmse=float(np.sqrt(np.mean((amplitudes[None, 1:]
                                                        * rates[None, 1:] ** data['depths'][:, None] - modes[:, 1:]) ** 2))))
            record.update(score(output, target, scale))
            if policy == 'juqst':
                assert record['score'] > 1 - 1e-10
            record['identity_probability'] = float(output['probabilities'][0])
            record['nonzero_probabilities'] = int(np.sum(output['probabilities'] > 0))
            record['spatial_jsd'] = float(output['spatial_jsd'])
            record['cv'] = cross_validate(data, modes, policy, target, args.submission)
            record['seconds'] = time.monotonic() - policy_started
            case_record['policies'][policy] = record
            print(json.dumps(dict(case=case['id'], policy=policy, score=record['score'],
                                  components=record['components'], cv=record['cv']['summary'],
                                  seconds=record['seconds'])), flush=True)
        result['cases'].append(case_record)
        destination.write_text(json.dumps(result, indent=2) + '\n')
    result['aggregate'] = {}
    for policy in policies:
        records = [case['policies'][policy] for case in result['cases']]
        result['aggregate'][policy] = dict(mean_score=float(np.mean([record['score'] for record in records])),
            mean_components={key: float(np.mean([record['components'][key] for record in records])) for key in evaluator.KEYS},
            pooled_cv_rmse={key.replace('_mse', '_rmse'): float(np.sqrt(np.mean([record['cv']['summary'][key]
                              for record in records]))) for key in records[0]['cv']['summary'] if key.endswith('_mse')})
    result['protected_files_unchanged'] = all(digest(path) == hashes[str(path.relative_to(PRIVATE.parent.parent))]
                                               for path in protected)
    assert result['protected_files_unchanged']
    if args.submission is not None:
        assert digest(args.submission) == result['submission']['sha256']
    result['seconds'] = time.monotonic() - started
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(aggregate=result['aggregate'], seconds=result['seconds'])), flush=True)


if __name__ == '__main__':
    main()
