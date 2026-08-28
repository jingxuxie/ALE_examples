import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import time
import numpy as np
import scipy.linalg as la
from scipy.optimize import least_squares


def adjoint(matrix):
    return matrix.conj().swapaxes(-1, -2)


def hermitian(matrix):
    return (matrix + adjoint(matrix)) * .5


def norm_rows(matrix):
    return la.norm(matrix.reshape(len(matrix), -1), axis=1)


class Rational:
    def __init__(self, nodes, values, weights, error):
        self.nodes = nodes.copy()
        self.values = values.copy()
        self.weights = weights.copy()
        self.error = error

    def __call__(self, points):
        difference = points[:, None] - self.nodes
        exact = np.abs(difference) < 1e-14 * np.maximum(1, np.abs(points[:, None]))
        difference[exact] = 1
        basis = 1 / difference
        denominator = basis @ self.weights
        denominator[np.abs(denominator) < 1e-300] = 1e-300
        result = (basis @ (self.weights[:, None] * self.values.reshape(len(self.nodes), -1))) / denominator[:, None]
        rows, columns = np.nonzero(exact)
        result[rows] = self.values.reshape(len(self.nodes), -1)[columns]
        return result.reshape((len(points),) + self.values.shape[1:])

    def poles(self):
        count = len(self.nodes)
        matrix = np.zeros((count + 1, count + 1), complex)
        matrix[0, 1:] = self.weights
        matrix[1:, 0] = 1
        matrix[1:, 1:] = np.diag(self.nodes)
        metric = np.eye(count + 1)
        metric[0, 0] = 0
        roots = la.eigvals(matrix, metric, check_finite=False)
        return roots[np.isfinite(roots)]

    def pole_residues(self):
        roots = self.poles()
        basis = 1 / (roots[:,None]-self.nodes)
        derivative = -(basis**2)@self.weights
        numerator = basis@(self.weights[:,None]*self.values.reshape(len(self.nodes),-1))
        residues = numerator/derivative[:,None]
        return roots,residues


def rational_fit(nodes, values, rowweight=None, paired=False, mass=None, bound=1e-13, maximum=25):
    count = len(nodes)
    shape = values.shape[1:]
    values = values.reshape(count, -1)
    rowweight = np.ones(count) if rowweight is None else rowweight
    residual = values - np.mean(values, axis=0)
    selected = []
    history = []
    floor = max(1e-15, 2e-15 * np.max(la.norm(values, axis=1) * rowweight))
    best = np.inf
    stale = 0
    for order in range(min(maximum, count - 2)):
        errors = la.norm(residual, axis=1) * rowweight
        errors[selected] = -1
        selected.append(int(np.argmax(errors)))
        remaining = np.setdiff1d(np.arange(count), selected)
        support_nodes = nodes[selected]
        support_values = values[selected]
        if paired:
            support_nodes = np.stack([support_nodes, support_nodes.conj()], axis=1).ravel()
            positive_values = support_values.reshape((-1,) + shape)
            support_values = np.stack([positive_values, adjoint(positive_values)], axis=1).reshape(len(support_nodes), -1)
        basis = 1 / (nodes[remaining, None] - support_nodes)
        loewner = (values[remaining, :, None] - support_values.T[None, :, :]) * basis[:, None, :]
        loewner *= rowweight[remaining, None, None]
        loewner = loewner.reshape(-1, len(support_nodes))
        if mass is not None:
            extra = (support_values - mass.reshape(1, -1)) / support_nodes[:, None]
            loewner = np.r_[loewner, extra.T]
        if paired:
            transformed = np.c_[loewner[:, ::2] + loewner[:, 1::2], 1j * (loewner[:, ::2] - loewner[:, 1::2])]
            transformed = np.r_[transformed.real, transformed.imag]
            _, singular, right = la.svd(transformed, full_matrices=False, check_finite=False)
            parameters = right[-1]
            positive_weights = parameters[:len(selected)] + 1j * parameters[len(selected):]
            weights = np.stack([positive_weights, positive_weights.conj()], axis=1).ravel()
        else:
            _, singular, right = la.svd(loewner, full_matrices=False, check_finite=False)
            weights = right[-1].conj()
        denominator = basis @ weights
        denominator[np.abs(denominator) < 1e-300] = 1e-300
        fitted = (basis @ (weights[:, None] * support_values)) / denominator[:, None]
        residual = np.zeros_like(values)
        residual[remaining] = values[remaining] - fitted
        error = np.max(la.norm(residual, axis=1) * rowweight)
        model = Rational(support_nodes, support_values.reshape((-1,) + shape), weights, error)
        if not np.isfinite(error):
            break
        history.append(model)
        if error < best * .65:
            stale = 0
        else:
            stale += 1
        best = min(best, error)
        if error < floor or (stale >= 5 and best < max(bound * 20, floor * 20)):
            break
    return history


def spectral_green(points, energies, residues):
    return np.einsum('nk,kij->nij', 1 / (points[:, None] - energies), residues, optimize=True)


def matrix_root(matrix, inverse=False):
    eigenvalues,vectors = la.eigh(hermitian(matrix))
    if inverse:
        weights = np.zeros_like(eigenvalues)
        selected = eigenvalues > max(eigenvalues[-1]*1e-13,1e-15)
        weights[selected] = 1/np.sqrt(eigenvalues[selected])
    else:
        weights = np.sqrt(np.maximum(eigenvalues,0))
    return (vectors*weights)@vectors.conj().T


def block_candidate(nodes, values, moments, points, bound, debug=False):
    dimension = values.shape[-1]
    identity = np.eye(dimension)
    target_root = matrix_root(moments[2]-moments[1]@moments[1])
    candidates = []
    for count,limit in [(28,4),(36,4),(28,8),(36,8)]:
        available = np.flatnonzero(np.abs(nodes)<limit)
        if len(available)<16:
            available = np.arange(min(24,len(nodes)))
        local = np.unique(np.r_[np.arange(min(8,len(available))),np.round(np.geomspace(9,len(available),count-8)-1).astype(int)])
        sample = available[local]
        sample_nodes = nodes[sample]
        sample_values = values[sample]
        difference = sample_nodes[:,None]-sample_nodes.conj()[None,:]
        conjugate = adjoint(sample_values)
        overlap = -(sample_values[:,None]-conjugate[None,:])/difference[:,:,None,None]
        generator = -(sample_nodes[:,None,None,None]*sample_values[:,None]-sample_nodes.conj()[None,:,None,None]*conjugate[None,:])/difference[:,:,None,None]
        overlap = overlap.transpose(0,2,1,3).reshape(len(sample)*dimension,-1)
        generator = generator.transpose(0,2,1,3).reshape(len(sample)*dimension,-1)
        coupling = sample_values.reshape(-1,dimension)
        dynamic_coupling = (sample_nodes[:,None,None]*sample_values-identity).reshape(-1,dimension)
        overlap = np.block([[identity,coupling.conj().T],[coupling,overlap]])
        generator = np.block([[moments[1],dynamic_coupling.conj().T],[dynamic_coupling,generator]])
        coupling = np.r_[identity,coupling]
        normalization = 1/np.sqrt(np.maximum(np.diag(overlap).real,1e-20))
        overlap = hermitian(normalization[:,None]*overlap*normalization[None,:])
        generator = hermitian(normalization[:,None]*generator*normalization[None,:])
        coupling = normalization[:,None]*coupling
        eigenvalues,vectors = la.eigh(overlap,check_finite=False)
        ranks = [int(np.sum(eigenvalues>eigenvalues[-1]*10.**(-exponent))) for exponent in range(8,16)]
        if debug:
            print('ranks',count,ranks,flush=True)
        for rank in set(ranks):
            if ranks.count(rank)<3 or rank<dimension:
                continue
            retained = np.arange(len(eigenvalues)-rank,len(eigenvalues))
            whitening = (vectors[:,retained]/np.sqrt(eigenvalues[retained])).conj().T
            energies,rotation = la.eigh(hermitian(whitening@generator@whitening.conj().T))
            projection = rotation.conj().T@whitening@coupling
            residues = np.einsum('ki,kj->kij',projection.conj(),projection)
            if np.max(np.abs(energies))>1.02:
                if debug:
                    print('outside',rank,energies[[0,-1]],flush=True)
                continue
            inverse_mass = matrix_root(np.sum(residues,axis=0),inverse=True)
            residues = inverse_mass@residues@inverse_mass
            old_first = hermitian(np.einsum('k,kij->ij',energies,residues))
            old_second = hermitian(np.einsum('k,kij->ij',energies**2,residues))
            if debug:
                print('uncorrected',np.max(norm_rows(spectral_green(nodes,energies,residues)-values)),la.norm(old_first-moments[1]),la.norm(old_second-moments[2]),flush=True)
            correction = target_root@matrix_root(old_second-old_first@old_first,inverse=True)
            def response(locations):
                original = spectral_green(locations,energies,residues)
                dynamic = locations[:,None,None]*identity-old_first-np.linalg.inv(original)
                return np.linalg.inv(locations[:,None,None]*identity-moments[1]-correction@dynamic@correction.conj().T)
            fitted = response(nodes)
            error = np.max(norm_rows(fitted-values))
            plain_error = np.max(norm_rows(spectral_green(nodes,energies,residues)-values))
            plain = plain_error < error
            error = min(error,plain_error)
            threshold = max(bound*dimension*150,2e-11*max(1,np.max(norm_rows(values))))
            if debug:
                print('block error',rank,error,threshold,flush=True)
            if error<threshold:
                prediction = spectral_green(points,energies,residues) if plain else response(points)
                candidates.append((error,prediction))
    return min(candidates,key=lambda item:item[0])[1] if candidates else None


def fit_real_residues(nodes, values, energies, moments, rowweight=None):
    basis = 1 / (nodes[:, None] - energies)
    system = np.r_[basis.real, basis.imag]
    target = np.concatenate([hermitian(values), hermitian(values / 1j)]).reshape(len(nodes) * 2, -1)
    if rowweight is not None:
        system *= np.tile(rowweight,2)[:,None]
        target *= np.tile(rowweight,2)[:,None]
    constraints = np.array([energies ** order for order in range(len(moments))])
    constant = np.array(moments).reshape(len(moments), -1)
    particular = la.lstsq(constraints, constant, lapack_driver='gelsy')[0]
    nullspace = la.null_space(constraints)
    coefficients = la.lstsq(system @ nullspace, target - system @ particular, lapack_driver='gelsy')[0]
    residues = particular + nullspace @ coefficients
    residual = system @ residues - target
    return residues.reshape((-1,) + values.shape[1:]), residual


def refine_poles(nodes, values, energies, moments, rowweight=None):
    def objective(locations):
        residues, residual = fit_real_residues(nodes, values, locations, moments, rowweight)
        return np.r_[residual.real.ravel(), residual.imag.ravel()] * 1e6
    solution = least_squares(objective, energies, ftol=2e-12, xtol=2e-12, gtol=1e-10,
                             max_nfev=24, diff_step=1e-5)
    residues, residual = fit_real_residues(nodes, values, solution.x, moments, rowweight)
    return solution.x, residues, la.norm(residual)


def discrete_candidate(nodes, values, moments, points, bound, rowweight=None):
    history = rational_fit(nodes, values, rowweight=rowweight, paired=True, maximum=28, bound=bound)
    candidates = []
    dimension = values.shape[-1]
    minimum = min(model.error for model in history)
    for model in history:
        if model.error > max(minimum * 20, bound * dimension * 4, 2e-13):
            continue
        roots = model.poles()
        roots = np.sort(roots.real[(np.abs(roots.imag) < 2e-5) & (np.abs(roots.real) < 1.02)])
        roots = roots[np.r_[True, np.diff(roots) > 1e-6]]
        if len(roots) < 1 or len(roots) > 38:
            continue
        residues, residual = fit_real_residues(nodes, values, roots, moments, rowweight)
        eigenvalues = np.linalg.eigvalsh(hermitian(residues))
        negative = -np.minimum(eigenvalues, 0).sum()
        rank_excess = np.abs(eigenvalues[:, :-1]).sum()
        error = la.norm(residual)
        if negative < dimension * .003 and rank_excess < dimension * .01:
            candidates.append((error, roots, residues))
    if not candidates:
        return None, history
    candidates.sort(key=lambda entry: entry[0])
    error, roots, residues = candidates[0]
    if error > max(bound * dimension * np.sqrt(len(nodes)) * 50, 1e-8):
        return None, history
    roots, residues, error = refine_poles(nodes, values, roots, moments, rowweight)
    eigenvalues, vectors = np.linalg.eigh(hermitian(residues))
    negative = -np.minimum(eigenvalues, 0).sum()
    rank_excess = np.abs(eigenvalues[:, :-1]).sum()
    if negative > dimension * 3e-5 or rank_excess > dimension * .001:
        return None, history
    if error > max(bound * dimension * np.sqrt(len(nodes)) * 10, 2e-10):
        return None, history
    residues = (vectors * np.maximum(eigenvalues, 0)[:, None, :]) @ adjoint(vectors)
    mass = hermitian(np.sum(residues,axis=0))
    mass_values,mass_vectors = la.eigh(mass)
    inverse_mass = (mass_vectors/np.sqrt(np.maximum(mass_values,1e-15)))@mass_vectors.conj().T
    residues = inverse_mass@residues@inverse_mass
    prediction = spectral_green(points, roots, residues)
    check_models = rational_fit(nodes, values, rowweight=rowweight, bound=bound, maximum=34)
    check_error = min(model.error for model in check_models)
    checks = [model for model in check_models if model.error < max(check_error*20,bound*dimension*5,2e-13)]
    confirmed = False
    for model in checks:
        disagreement = la.norm(model(points)-prediction)/max(la.norm(prediction),1e-15)
        if disagreement > .003:
            continue
        check_roots,check_residues = model.pole_residues()
        weights = la.norm(check_residues,axis=1)
        valid = np.isfinite(weights)&(np.abs(check_roots)<1.2)
        off_axis = np.abs(check_roots.imag) > np.min(points.imag)*.01
        fraction = np.sum(weights[valid&off_axis])/max(np.sum(weights[valid]),1e-15)
        if fraction < .01:
            confirmed = True
            break
    if not confirmed:
        return None, history
    return prediction, history


def conformal(points, interval):
    center = (interval[0] + interval[1]) / 2
    radius = (interval[1] - interval[0]) / 2
    scaled = (points - center) / radius
    branch = np.sqrt(scaled - 1) * np.sqrt(scaled + 1)
    return 1 / (scaled + branch)


def estimate_interval(nodes, values, first_moment):
    dimension = values.shape[-1]
    available = np.flatnonzero(np.abs(nodes) < 12)
    if len(available) < 12:
        available = np.arange(len(nodes))
    sample = available[np.unique(np.round(np.linspace(0, len(available) - 1, min(32, len(available)))).astype(int))]
    nodes = nodes[sample]
    values = values[sample]
    difference = nodes[:, None] - nodes.conj()[None, :]
    conjugate = adjoint(values)
    overlap = -(values[:, None] - conjugate[None, :]) / difference[:, :, None, None]
    generator = -(nodes[:, None, None, None] * values[:, None] - nodes.conj()[None, :, None, None] * conjugate[None, :]) / difference[:, :, None, None]
    overlap = overlap.transpose(0, 2, 1, 3).reshape(len(nodes) * dimension, -1)
    generator = generator.transpose(0, 2, 1, 3).reshape(len(nodes) * dimension, -1)
    coupling = values.reshape(-1, dimension)
    dynamic_coupling = (nodes[:, None, None] * values - np.eye(dimension)).reshape(-1, dimension)
    overlap = np.block([[np.eye(dimension), coupling.conj().T], [coupling, overlap]])
    generator = np.block([[first_moment, dynamic_coupling.conj().T], [dynamic_coupling, generator]])
    coupling = np.r_[np.eye(dimension), coupling]
    normalization = 1 / np.sqrt(np.maximum(np.diag(overlap).real, 1e-20))
    overlap = hermitian(normalization[:, None] * overlap * normalization[None, :])
    generator = hermitian(normalization[:, None] * generator * normalization[None, :])
    coupling *= normalization[:, None]
    eigenvalues, vectors = la.eigh(overlap, check_finite=False)
    retained = eigenvalues > max(eigenvalues[-1] * 1e-13, -eigenvalues[0] * 30)
    whitening = (vectors[:, retained] / np.sqrt(eigenvalues[retained])).conj().T
    energies, rotation = la.eigh(hermitian(whitening @ generator @ whitening.conj().T))
    projection = rotation.conj().T @ whitening @ coupling
    weights = np.sum(np.abs(projection) ** 2, axis=1)
    energies = energies[(weights > 1e-5) & (np.abs(energies) < 1.02)]
    if len(energies) < 4:
        return (-1., 1.)
    lower = energies[0] - (energies[1] - energies[0]) / 8
    upper = energies[-1] + (energies[-1] - energies[-2]) / 8
    return (max(lower, -1.), min(upper, 1.))


def project_loss(dynamic):
    real_part = hermitian(dynamic)
    loss = hermitian(1j * dynamic)
    eigenvalues, vectors = np.linalg.eigh(loss)
    positive = (vectors * np.maximum(eigenvalues, 0)[:, None, :]) @ adjoint(vectors)
    return real_part - 1j * positive


def continue_matrix(nodes, values, moments, points, bound, debug=False, metadata=None):
    started = time.monotonic()
    dimension = values.shape[-1]
    identity = np.eye(dimension)
    static = hermitian(moments[1])
    covariance = hermitian(moments[2] - static @ static)
    eigenvalues, vectors = la.eigh(covariance)
    selected = eigenvalues > max(eigenvalues[-1] * 1e-11, 2e-14)
    if not np.any(selected):
        if metadata is not None:
            metadata['discrete'] = True
        return np.linalg.inv(points[:, None, None] * identity - static)
    root = vectors[:, selected] * np.sqrt(eigenvalues[selected])
    inverse_root = (vectors[:, selected] / np.sqrt(eigenvalues[selected])).conj().T
    discrete, history = discrete_candidate(nodes, values, moments, points, bound)
    if discrete is not None:
        if metadata is not None:
            metadata['discrete'] = True
        if debug:
            print('discrete', time.monotonic() - started, flush=True)
        return discrete
    block = block_candidate(nodes,values,moments,points,bound)
    if block is not None:
        if metadata is not None:
            metadata['discrete'] = True
            metadata['block'] = True
        return block
    inverse_data = np.linalg.inv(values)
    dynamic_data = nodes[:, None, None] * identity - static - inverse_data
    transformed = inverse_root @ dynamic_data @ inverse_root.conj().T
    amplification = np.linalg.norm(inverse_root @ inverse_data, ord=2, axis=(-2, -1))
    amplification *= np.linalg.norm(inverse_data @ inverse_root.conj().T, ord=2, axis=(-2, -1))
    transformed_weight = 1 / np.maximum(amplification, .05)
    dynamic_mask = np.abs(nodes)<8
    if np.sum(dynamic_mask)<16:
        dynamic_mask = np.ones(len(nodes),bool)
    dynamic_discrete,dynamic_history = discrete_candidate(nodes[dynamic_mask],transformed[dynamic_mask],
        [np.eye(transformed.shape[-1])],points,bound,rowweight=transformed_weight[dynamic_mask])
    if dynamic_discrete is not None:
        if metadata is not None:
            metadata['discrete'] = True
        if debug:
            print('discrete self energy',time.monotonic()-started,flush=True)
        return np.linalg.inv(points[:,None,None]*identity-static-root@dynamic_discrete@root.conj().T)
    models = []
    data_scale = max(np.max(norm_rows(values)), 1)
    estimated = estimate_interval(nodes, values, static)
    intervals = [(estimated[0] - .004, estimated[1] + .004),
                 (estimated[0] - .025, estimated[1] + .025),
                 (-1., 1.), (-1.2, 1.2)]
    if debug:
        print('interval', estimated, flush=True)
    configurations = []
    for is_dynamic in [False, True]:
        for interval in intervals:
            for subset in [0, 1]:
                configurations.append((is_dynamic, interval, subset, True))
        configurations.append((is_dynamic, None, 0, False))
        configurations.append((is_dynamic, None, 1, False))
    for is_dynamic, interval, subset, divided in configurations:
        mask = np.ones(len(nodes), bool)
        if is_dynamic:
            mask &= np.abs(nodes) < 10
        if subset:
            mask &= (np.arange(len(nodes)) % 4 != 2) | (np.arange(len(nodes)) < 4)
        if np.sum(mask) < 16:
            mask = np.ones(len(nodes), bool)
        train_nodes = nodes[mask]
        train_values = transformed[mask] if is_dynamic else values[mask]
        rowweight = transformed_weight[mask] if is_dynamic else np.ones(np.sum(mask))
        mass = None
        if interval is not None:
            train_nodes = conformal(train_nodes, interval)
            if divided:
                train_values = train_values / train_nodes[:, None, None]
                rowweight = rowweight * np.abs(train_nodes)
                mass = np.eye(train_values.shape[-1]) * 4 / (interval[1] - interval[0])
        fitted_models = rational_fit(train_nodes, train_values, rowweight, interval is not None,
                                     mass, bound, maximum=24 if interval else 30)
        records = []
        def recover(model, locations):
            coordinate = conformal(locations, interval) if interval else locations
            result = model(coordinate)
            if interval and divided:
                result *= coordinate[:, None, None]
            if is_dynamic:
                result = np.linalg.inv(locations[:, None, None] * identity - static - root @ result @ root.conj().T)
            return result
        for model in fitted_models:
            if model.error > max(bound * 100, 1e-8):
                continue
            fitted = recover(model, nodes)
            error = np.sqrt(np.mean(norm_rows(fitted - values) ** 2))
            records.append((error, model))
        if not records:
            continue
        best_error = min(record[0] for record in records)
        if metadata is not None:
            metadata['residual'] = min(metadata.get('residual',np.inf),best_error)
        admissible = [record for record in records if record[0] < max(best_error * 4, data_scale * 4e-15)]
        admissible.sort(key=lambda record: (len(record[1].nodes), record[0]))
        for error, model in admissible[:2]:
            prediction = recover(model, points)
            if not np.all(np.isfinite(prediction)):
                continue
            dynamic = points[:, None, None] * identity - static - np.linalg.inv(prediction)
            loss_eigenvalues = np.linalg.eigvalsh(hermitian(1j * dynamic))
            negative = la.norm(np.minimum(loss_eigenvalues, 0)) / max(la.norm(loss_eigenvalues), 1e-15)
            if negative > .1 or np.max(norm_rows(prediction)) > dimension * 3 / np.min(points.imag):
                continue
            weight = (1 if interval else .2) / (1 + (negative / .002) ** 2)
            weight *= (max(error, data_scale * 2e-15) / (data_scale * 2e-15)) ** -.18
            if debug:
                print('model',is_dynamic,interval,subset,len(model.nodes),'error',error,'negative',negative,'weight',weight,flush=True)
            models.append((dynamic, prediction, weight))
        if time.monotonic() - started > 75:
            break
    if not models:
        model = min(history, key=lambda item: item.error)
        prediction = model(points)
        dynamic = points[:, None, None] * identity - static - np.linalg.inv(prediction)
    else:
        dynamics = np.array([model[0] for model in models])
        predictions = np.array([model[1] for model in models])
        weights = np.array([model[2] for model in models])
        weights /= np.sum(weights)
        green_scale = np.maximum(np.median(np.linalg.norm(predictions,axis=(-2,-1)),axis=0), .05)
        sigma_scale = np.maximum(np.median(np.linalg.norm(dynamics,axis=(-2,-1)),axis=0), .05)
        distance = np.linalg.norm(dynamics[:,None]-dynamics[None,:],axis=(-2,-1)) / sigma_scale
        distance += np.linalg.norm(predictions[:,None]-predictions[None,:],axis=(-2,-1)) / green_scale
        central = np.argmin(np.einsum('abn,b->an',distance,weights),axis=0)
        location = np.arange(len(points))
        dynamic = dynamics[central,location]
        prediction = predictions[central,location]
        radius = np.maximum(np.median(distance[central,:,location],axis=1),1e-5)
        for iteration in range(4):
            residual = np.linalg.norm(dynamics-dynamic,axis=(-2,-1)) / sigma_scale
            residual += np.linalg.norm(predictions-prediction,axis=(-2,-1)) / green_scale
            robust_weights = weights[:,None] / np.maximum(1,residual/radius)
            robust_weights /= np.sum(robust_weights,axis=0)
            dynamic = np.einsum('an,anij->nij',robust_weights,dynamics)
            prediction = np.einsum('an,anij->nij',robust_weights,predictions)
    dynamic = project_loss(dynamic)
    if debug:
        print('elapsed',time.monotonic()-started,'models',len(models),flush=True)
    return np.linalg.inv(points[:,None,None]*identity-static-dynamic)
