import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
import argparse
import time
import numpy as np
from scipy.linalg import cho_factor, cho_solve, eigh
from scipy.sparse import coo_matrix
from scipy.optimize import minimize


def prepare(data):
    source, target = data['source'], data['target']
    velocities, probes = data['velocities'], data['probes']
    count = len(velocities)
    weights = (data['channels'] @ data['mixing'].T).T.copy()
    degrees = np.array([
        np.bincount(source, weights=row, minlength=count)
        + np.bincount(target, weights=row, minlength=count)
        for row in weights
    ])
    probe_diff = (probes[source] - probes[target]) ** 2
    dissipation = weights @ probe_diff
    drives = []
    importance = np.zeros(len(source))
    for temp, (row, degree) in enumerate(zip(weights, degrees)):
        matrix = np.full((count, count), 1.0 / count)
        matrix[source, target] -= row
        matrix[target, source] -= row
        matrix[np.diag_indices(count)] += degree
        factor = cho_factor(matrix, check_finite=False)
        response = cho_solve(factor, velocities, check_finite=False)
        conductivity = velocities.T @ response
        eigenvalues, eigenvectors = eigh(conductivity, check_finite=False)
        transform = eigenvectors / np.sqrt(eigenvalues)[None, :]
        drives.append(velocities @ transform)
        response = response @ transform
        difference = response[source] - response[target]
        importance += 0.25 * row * np.sum(difference ** 2, axis=1) / 3
        inverse = cho_solve(factor, np.eye(count), check_finite=False)
        resistance = inverse.diagonal()[source] + inverse.diagonal()[target] - 2 * inverse[source, target]
        importance += 0.60 * row * np.maximum(resistance, 0) / (count - 1)
        importance += 0.15 * row * (probe_diff @ (1 / dissipation[temp])) / probes.shape[1]
    return source, target, weights, degrees, probe_diff, dissipation, np.array(drives), importance


class TimeLimit(Exception):
    pass


def spanning_forest(count, source, target, order):
    parent = np.arange(count)
    size = np.ones(count, dtype=int)
    retained = []
    for edge in order:
        source_root = int(source[edge])
        target_root = int(target[edge])
        while source_root != parent[source_root]:
            parent[source_root] = parent[parent[source_root]]
            source_root = parent[source_root]
        while target_root != parent[target_root]:
            parent[target_root] = parent[parent[target_root]]
            target_root = parent[target_root]
        if source_root != target_root:
            if size[source_root] < size[target_root]:
                source_root, target_root = target_root, source_root
            parent[target_root] = source_root
            size[source_root] += size[target_root]
            retained.append(edge)
            if len(retained) == count - 1:
                break
    return np.array(retained, dtype=int)


class Compressor:
    def __init__(self, data, seconds=75.0):
        self.start = time.monotonic()
        self.deadline = self.start + seconds
        self.source, self.target, self.weights, self.degrees, self.probe_diff, self.dissipation, self.drives, self.importance = prepare(data)
        self.count = len(data['velocities'])
        self.temperatures = len(self.weights)
        self.budget = int(data['budget'])
        self.rng = np.random.default_rng(29)
        priority = -np.log(self.rng.random(len(self.source))) / self.importance
        indices = np.argpartition(priority,self.budget-1)[:self.budget]
        threshold = priority[indices].max()
        self.scale = np.minimum(1e7, 1 / (-np.expm1(-self.importance*threshold)))
        forest = spanning_forest(self.count, self.source, self.target, indices[np.argsort(-self.importance[indices])])
        if len(forest) != self.count - 1:
            connected_forest = spanning_forest(self.count, self.source, self.target, np.concatenate([forest, np.argsort(-self.importance)]))
            additions = np.setdiff1d(connected_forest, indices)
            removable = np.setdiff1d(indices, forest)
            remove = removable[np.argsort(-priority[removable])[:len(additions)]]
            indices = np.concatenate([np.setdiff1d(indices, remove), additions])
        self.upper = np.triu_indices(3)
        self.symmetric_scale = np.array([1,np.sqrt(2),np.sqrt(2),1,np.sqrt(2),1])
        self.identity = np.eye(3)
        self.degree_target = np.ones(self.temperatures*self.count)/np.sqrt(self.count)
        self.probe_target = np.ones(self.temperatures*self.probe_diff.shape[1])
        self.set_support(indices,np.ones(self.budget))
        self.best_error = np.inf
        self.best_indices = self.indices.copy()
        self.best_values = self.values.copy()

    def set_support(self,indices,values):
        self.indices = indices
        self.values = values
        self.selected_source = self.source[indices]
        self.selected_target = self.target[indices]
        self.selected_weights = self.weights[:,indices]*self.scale[indices]
        rows = np.concatenate([self.selected_source[None,:]+self.count*np.arange(self.temperatures)[:,None],self.selected_target[None,:]+self.count*np.arange(self.temperatures)[:,None]],axis=1).ravel()
        columns = np.tile(np.arange(len(indices)),2*self.temperatures)
        entries = np.concatenate([self.selected_weights/self.degrees[:,self.selected_source],self.selected_weights/self.degrees[:,self.selected_target]],axis=1).ravel()/np.sqrt(self.count)
        self.degree_matrix = coo_matrix((entries,(rows,columns)),shape=(self.temperatures*self.count,len(indices))).tocsr()
        self.probe_matrix = (self.selected_weights[:,None,:]*self.probe_diff[indices].T[None,:,:]/self.dissipation[:,:,None]).reshape(-1,len(indices))
        self.degree_diagonal = np.asarray(self.degree_matrix.power(2).sum(axis=0)).ravel()

    def evaluate(self,values):
        residuals,gradients,responses,conductivities = [],[],[],[]
        for temp in range(self.temperatures):
            weights = self.selected_weights[temp]*values
            degree = np.bincount(self.selected_source,weights=weights,minlength=self.count)+np.bincount(self.selected_target,weights=weights,minlength=self.count)
            matrix = np.full((self.count,self.count),1/self.count)
            matrix[self.selected_source,self.selected_target] -= weights
            matrix[self.selected_target,self.selected_source] -= weights
            matrix[np.diag_indices(self.count)] += degree
            try:
                response = cho_solve(cho_factor(matrix, check_finite=False),self.drives[temp], check_finite=False)
            except np.linalg.LinAlgError:
                return np.inf, None, None, np.inf
            conductivity = self.drives[temp].T @ response-self.identity
            difference = response[self.selected_source]-response[self.selected_target]
            gradient = -self.selected_weights[temp][None,:]*(difference[:,self.upper[0]]*difference[:,self.upper[1]]).T*self.symmetric_scale[:,None]
            residuals.extend(conductivity[self.upper]*self.symmetric_scale)
            gradients.append(gradient)
            responses.append(response)
            conductivities.append(conductivity)
        self.responses = np.array(responses)
        self.conductivities = np.array(conductivities)
        degree_residual = self.degree_matrix @ values-self.degree_target
        probe_residual = self.probe_matrix @ values-self.probe_target
        residuals = np.array(residuals)
        loss = np.dot(degree_residual,degree_residual)+np.dot(probe_residual,probe_residual)+np.dot(residuals,residuals)
        error = max(np.sqrt(np.sum(degree_residual.reshape(self.temperatures,-1)**2,axis=1)).max(),np.abs(probe_residual).max(),np.abs(np.linalg.eigvalsh(self.conductivities)).max())
        if error < self.best_error:
            self.best_error = error
            self.best_indices = self.indices.copy()
            self.best_values = values.copy()
        return loss,residuals,np.vstack(gradients),error

    def fit(self,iterations,regularizer):
        initial_loss,nonlinear_residual,gradient,initial_error = self.evaluate(self.values)
        fit_matrix = np.vstack([self.probe_matrix,gradient])
        fit_target = np.concatenate([self.probe_target,gradient @ self.values-nonlinear_residual])
        diagonal = self.degree_diagonal+np.sum(fit_matrix**2,axis=0)
        precondition = 1/np.sqrt(diagonal)
        previous = self.values.copy()
        evaluations = 0
        def objective(candidate):
            nonlocal evaluations
            evaluations += 1
            if evaluations % 16 == 0 and time.monotonic() > self.deadline:
                raise TimeLimit()
            candidate = candidate*precondition
            residual = fit_matrix @ candidate-fit_target
            degree_residual = self.degree_matrix @ candidate-self.degree_target
            delta = candidate-previous
            loss = np.dot(residual,residual)+np.dot(degree_residual,degree_residual)+regularizer*np.dot(delta,delta)
            derivative = 2*(fit_matrix.T @ residual+self.degree_matrix.T @ degree_residual+regularizer*delta)*precondition
            return loss,derivative
        bounds = [(1e-10 / entry, 1e9 / (scale * entry)) for entry, scale in zip(precondition, self.scale[self.indices])]
        result = minimize(objective,self.values/precondition,jac=True,method='L-BFGS-B',bounds=bounds,options={'maxiter':iterations,'maxcor':20,'ftol':1e-14,'gtol':1e-9})
        candidate = result.x*precondition
        for fraction in [1,0.5,0.25,0.125,0.0625]:
            trial = previous+fraction*(candidate-previous)
            loss,_,_,error = self.evaluate(trial)
            if loss < initial_loss:
                self.values = trial
                break
        else:
            self.evaluate(previous)

    def exchange(self):
        removable = np.flatnonzero(self.values < 1e-5)
        forest = spanning_forest(self.count, self.selected_source, self.selected_target, np.argsort(-self.values*self.scale[self.indices]*self.importance[self.indices]))
        removable = np.setdiff1d(removable, forest)
        replacements = min(len(removable),self.budget//6)
        if replacements == 0:
            return
        remove = removable[np.argsort(self.values[removable])[:replacements]]
        degree_error = (self.degree_matrix @ self.values-self.degree_target).reshape(self.temperatures,self.count)/np.sqrt(self.count)
        probe_error = (self.probe_matrix @ self.values-self.probe_target).reshape(self.dissipation.shape)
        gradient = np.zeros(len(self.source))
        diagonal = np.zeros(len(self.source))
        for temp in range(self.temperatures):
            row = self.weights[temp]
            source_feature = row/self.degrees[temp,self.source]
            target_feature = row/self.degrees[temp,self.target]
            gradient += source_feature*degree_error[temp,self.source]+target_feature*degree_error[temp,self.target]
            diagonal += (source_feature**2+target_feature**2)/self.count
            feature = row[:,None]*self.probe_diff/self.dissipation[temp][None,:]
            gradient += feature @ probe_error[temp]
            diagonal += np.sum(feature**2,axis=1)
            difference = self.responses[temp,self.source]-self.responses[temp,self.target]
            gradient -= row*np.sum((difference @ self.conductivities[temp])*difference,axis=1)
            diagonal += row**2*np.sum(difference**2,axis=1)**2
        priority = gradient/np.sqrt(diagonal)
        priority[self.indices] = np.inf
        order = np.argsort(priority)
        additions = []
        added_degree = np.zeros(self.count,dtype=int)
        for edge in order:
            if not np.isfinite(priority[edge]):
                break
            source,target = self.source[edge],self.target[edge]
            if added_degree[source] >= 4 or added_degree[target] >= 4:
                continue
            additions.append(edge)
            added_degree[source] += 1
            added_degree[target] += 1
            if len(additions) == replacements:
                break
        retained = np.ones(len(self.indices),dtype=bool)
        retained[remove[:len(additions)]] = False
        self.set_support(np.concatenate([self.indices[retained],np.array(additions,dtype=int)]),np.concatenate([self.values[retained],np.full(len(additions),1e-10)]))


def compress(data,steps=40,iterations=500,exchange=True):
    if len(data['source']) <= int(data['budget']):
        return np.arange(len(data['source'])), np.ones(len(data['source']))
    solver = Compressor(data)
    for step in range(steps):
        if time.monotonic() > solver.deadline - 0.3:
            break
        regularizer = max(1e-9,1e-6*0.4**step)
        try:
            solver.fit(iterations,regularizer)
        except TimeLimit:
            break
        if solver.best_error < 0.00015:
            break
        if exchange and step >= 3 and step % 3 == 0 and step < steps - 4 and time.monotonic() < solver.deadline - 3:
            solver.exchange()
    return solver.best_indices,np.minimum(1e9,solver.best_values*solver.scale[solver.best_indices])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as catalogue:
        data = dict(catalogue)
    indices,multipliers = compress(data)
    with open(args.output, 'wb') as handle:
        np.savez(handle,indices=indices,multipliers=multipliers)


if __name__ == '__main__':
    main()
