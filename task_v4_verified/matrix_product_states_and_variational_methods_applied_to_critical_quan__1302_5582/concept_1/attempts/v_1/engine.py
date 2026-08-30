import time

import numpy as np
from scipy.linalg import eigh, svd

from contractor import hamiltonian_terms


class Budget:
    def __init__(self, request, wall_start=None):
        self.cpu = max(0.2, float(request['budget_seconds']) - 0.22)
        start = time.monotonic() if wall_start is None else wall_start
        self.wall = start + max(0.1, float(request['wall_seconds']) - 0.7)

    def expired(self, reserve=0.0):
        return time.process_time() >= self.cpu - reserve or time.monotonic() >= self.wall - reserve


def davidson(action, diagonal, initial, tolerance, iterations, budget):
    initial = initial / np.linalg.norm(initial)
    vectors = np.empty((len(initial), 24))
    images = np.empty_like(vectors)
    vectors[:, 0] = initial
    images[:, 0] = action(initial)
    count = 1
    best = initial
    energy = float(initial @ images[:, 0])
    for iteration in range(iterations):
        basis = vectors[:, :count]
        applied = images[:, :count]
        reduced = basis.T @ applied
        values, rotations = eigh(reduced, subset_by_index=[0, 0], check_finite=False)
        energy = values[0]
        coefficients = rotations[:, 0]
        best = basis @ coefficients
        residual = applied @ coefficients - energy * best
        if np.linalg.norm(residual) < tolerance or budget.expired(0.03):
            break
        denominator = np.maximum(diagonal - energy, 0.05)
        correction = residual / denominator
        correction -= basis @ (basis.T @ correction)
        correction -= basis @ (basis.T @ correction)
        norm = np.linalg.norm(correction)
        if norm < 1e-12:
            break
        correction /= norm
        if count == vectors.shape[1]:
            image = applied @ coefficients
            vectors[:, 0] = best
            images[:, 0] = image
            count = 1
        vectors[:, count] = correction
        images[:, count] = action(correction)
        count += 1
    return best, energy


def local_basis(request):
    onsite, position = hamiltonian_terms(request)
    symmetric = not any(request['field'])
    bases, charges, energies, positions = [], [], [], []
    dimension = request['local_dim']
    for local, coordinate in zip(onsite, position):
        if symmetric:
            values, vectors, parity = [], [], []
            for charge in (0, 1):
                indices = np.arange(charge, dimension, 2)
                eigenvalues, eigenvectors = eigh(local[np.ix_(indices, indices)], check_finite=False)
                embedded = np.zeros((dimension, len(indices)))
                embedded[indices] = eigenvectors
                values.extend(eigenvalues)
                vectors.append(embedded)
                parity.extend([charge] * len(indices))
            order = np.argsort(values)
            values = np.array(values)[order]
            basis = np.concatenate(vectors, axis=1)[:, order]
            parity = np.array(parity)[order]
        else:
            values, basis = eigh(local, check_finite=False)
            parity = np.zeros(dimension, dtype=int)
        bases.append(basis)
        charges.append(parity)
        energies.append(np.diag(values - values[0]))
        transformed = basis.T @ coordinate @ basis
        if symmetric:
            transformed[parity[:, None] == parity[None, :]] = 0
        positions.append(transformed)
    return bases, charges, energies, positions, symmetric


class DMRG:
    def __init__(self, request, budget, initialization='product'):
        self.request = request
        self.budget = budget
        self.bases, self.physical, self.onsite, self.position, self.symmetric = local_basis(request)
        self.symmetric = self.symmetric and request['sector'] != 'any'
        self.length = request['n_sites']
        self.dimension = request['local_dim']
        self.coupling = request['coupling']
        self.generator = np.random.default_rng(int(request['seed']) % (2 ** 64))
        self.tensors = []
        self.charges = [np.zeros(1, dtype=int)]
        occupied = np.zeros(self.length, dtype=int)
        if request['sector'] != 'any':
            levels = [[np.flatnonzero(parity == charge)[0] for charge in (0, 1)] for parity in self.physical]
            costs = np.array([0., np.inf])
            history = []
            for site, local_levels in enumerate(levels):
                candidates = np.array([[costs[total ^ charge] + self.onsite[site][local_levels[charge], local_levels[charge]]
                                        for charge in (0, 1)] for total in (0, 1)])
                history.append(np.argmin(candidates, axis=1))
                costs = np.min(candidates, axis=1)
            total = int(request['sector'] == 'odd')
            for site in range(self.length - 1, -1, -1):
                charge = history[site][total]
                occupied[site] = levels[site][charge]
                total ^= charge
        charge = 0
        for site in range(self.length):
            tensor = np.zeros((1, self.dimension, 1))
            tensor[0, occupied[site], 0] = 1
            self.tensors.append(tensor)
            charge ^= int(self.physical[site][occupied[site]])
            self.charges.append(np.array([charge]))
        if initialization == 'cat':
            self.seed_cat()
        self.left = [None] * (self.length + 1)
        self.right = [None] * (self.length + 1)
        self.left[0] = (np.zeros((1, 1)), np.zeros((1, 1)))
        self.right[self.length] = (np.zeros((1, 1)), np.zeros((1, 1)))
        for site in range(self.length - 1, -1, -1):
            self.update_right(site)

    def hartree(self, sign):
        means = sign * np.sqrt(np.maximum(0.2, -6 * np.array(self.request['mass2']) / np.array(self.request['lambda4'])))
        vectors = [None] * self.length
        for iteration in range(60):
            previous = means.copy()
            sites = range(self.length) if iteration % 2 == 0 else range(self.length - 1, -1, -1)
            for site in sites:
                field = 0.
                if site:
                    field += self.coupling[site - 1] * means[site - 1]
                if site + 1 < self.length:
                    field += self.coupling[site] * means[site + 1]
                _, basis = eigh(self.onsite[site] - field * self.position[site], subset_by_index=[0, 0], check_finite=False)
                vector = basis[:, 0]
                vectors[site] = vector
                means[site] = vector @ self.position[site] @ vector
            if np.max(np.abs(means - previous)) < 1e-8:
                break
        return vectors, means

    def seed_cat(self):
        positive, means = self.hartree(1)
        if self.symmetric:
            if np.max(np.abs(means)) < 0.01:
                return
            total = 1 if self.request['sector'] == 'odd' else 0
            self.charges = [np.array([0])] + [np.array([0, 1]) for _ in range(self.length - 1)] + [np.array([total])]
            self.tensors = []
            for site, vector in enumerate(positive):
                allowed = self.charges[site][:, None, None] ^ self.physical[site][None, :, None] ^ self.charges[site + 1][None, None, :]
                self.tensors.append(np.where(allowed == 0, vector[None, :, None], 0.))
        else:
            negative, _ = self.hartree(-1)
            if min(self.request['field']) < 0 < max(self.request['field']):
                aligned, _ = self.hartree(np.where(np.array(self.request['field']) < 0, -1, 1))
                candidates = [positive, negative, aligned]
                def product_energy(vectors):
                    coordinates = [vector @ position @ vector for vector, position in zip(vectors, self.position)]
                    value = sum(vector @ local @ vector for vector, local in zip(vectors, self.onsite))
                    return value - sum(coupling * first * second for coupling, first, second in zip(self.coupling, coordinates[:-1], coordinates[1:]))
                candidates.sort(key=product_energy)
                positive = candidates[0]
                negative = min(candidates[1:], key=lambda vectors: np.prod([abs(first @ second) for first, second in zip(positive, vectors)]))
            overlaps = np.prod([abs(first @ second) for first, second in zip(positive, negative)])
            if overlaps > 0.999:
                if not any(self.request['field']):
                    self.tensors = []
                    for site in range(self.length):
                        _, vector = eigh(self.onsite[site] - 0.01 * self.position[site], subset_by_index=[0, 0], check_finite=False)
                        self.tensors.append(vector.reshape(1, self.dimension, 1))
                return
            self.charges = [np.array([0])] + [np.array([0, 0]) for _ in range(self.length - 1)] + [np.array([0])]
            self.tensors = []
            for site, (first, second) in enumerate(zip(positive, negative)):
                if site == 0:
                    tensor = np.stack((first, 0.9 * second), axis=1)[None, :, :]
                elif site + 1 == self.length:
                    tensor = np.stack((first, second), axis=0)[:, :, None]
                else:
                    tensor = np.zeros((2, self.dimension, 2))
                    tensor[0, :, 0] = first
                    tensor[1, :, 1] = second
                self.tensors.append(tensor)
        for site in range(self.length - 1, 0, -1):
            self.move_center(site, -1)
        self.tensors[0] /= np.linalg.norm(self.tensors[0])

    def reflect_if_better(self):
        if self.symmetric:
            return False
        for site in range(self.length - 1, -1, -1):
            self.update_right(site)
        previous = self.right[0][0].item()
        old_tensors = self.tensors
        self.tensors = [np.einsum('ps,asb->apb', basis.T @ (((-1.) ** np.arange(self.dimension))[:, None] * basis), tensor, optimize=True)
                        for basis, tensor in zip(self.bases, old_tensors)]
        for site in range(self.length - 1, -1, -1):
            self.update_right(site)
        reflected = self.right[0][0].item()
        if reflected < previous - 1e-10:
            return True
        self.tensors = old_tensors
        for site in range(self.length - 1, -1, -1):
            self.update_right(site)
        return False

    def enlarged_left(self, site):
        energy, position = self.left[site]
        identity = np.eye(energy.shape[0])
        local_identity = np.eye(self.dimension)
        enlarged = np.kron(energy, local_identity) + np.kron(identity, self.onsite[site])
        if site:
            enlarged -= self.coupling[site - 1] * np.kron(position, self.position[site])
        return enlarged, np.kron(identity, self.position[site])

    def enlarged_right(self, site):
        energy, position = self.right[site + 1]
        identity = np.eye(energy.shape[0])
        local_identity = np.eye(self.dimension)
        enlarged = np.kron(self.onsite[site], identity) + np.kron(local_identity, energy)
        if site + 1 < self.length:
            enlarged -= self.coupling[site] * np.kron(self.position[site], position)
        return enlarged, np.kron(self.position[site], identity)

    def update_left(self, site):
        energy, position = self.enlarged_left(site)
        tensor = self.tensors[site].reshape(-1, self.tensors[site].shape[2])
        self.left[site + 1] = (tensor.T @ energy @ tensor, tensor.T @ position @ tensor)

    def update_right(self, site):
        energy, position = self.enlarged_right(site)
        tensor = self.tensors[site].reshape(self.tensors[site].shape[0], -1)
        self.right[site] = (tensor @ energy @ tensor.T, tensor @ position @ tensor.T)

    def pair(self, site, direction, cap, tolerance, iterations):
        first, second = self.tensors[site:site + 2]
        left_size, dimension, middle = first.shape
        right_size = second.shape[2]
        starting = first.reshape(-1, middle) @ second.reshape(middle, -1)
        left_energy, left_position = self.enlarged_left(site)
        right_energy, right_position = self.enlarged_right(site + 1)
        coupling = self.coupling[site]
        if self.symmetric:
            left_parity = (self.charges[site][:, None] ^ self.physical[site][None, :]).ravel()
            right_parity = (self.physical[site + 1][:, None] ^ self.charges[site + 2][None, :]).ravel()
            left_indices = [np.flatnonzero(left_parity == charge) for charge in (0, 1)]
            right_indices = [np.flatnonzero(right_parity == charge) for charge in (0, 1)]
        else:
            left_indices = [np.arange(starting.shape[0])]
            right_indices = [np.arange(starting.shape[1])]
        shapes = [(len(left), len(right)) for left, right in zip(left_indices, right_indices)]
        sizes = [left * right for left, right in shapes]
        offsets = np.cumsum([0] + sizes)
        left_blocks = [left_energy[np.ix_(indices, indices)] for indices in left_indices]
        right_blocks = [right_energy[np.ix_(indices, indices)] for indices in right_indices]
        cross_left, cross_right = [], []
        for block in range(len(shapes)):
            other = 1 - block if self.symmetric else block
            cross_left.append(left_position[np.ix_(left_indices[block], left_indices[other])])
            cross_right.append(right_position[np.ix_(right_indices[other], right_indices[block])])

        def action(vector):
            blocks = [vector[offsets[index]:offsets[index + 1]].reshape(shape) for index, shape in enumerate(shapes)]
            result = np.empty_like(vector)
            for index, matrix in enumerate(blocks):
                other = 1 - index if self.symmetric else index
                applied = left_blocks[index] @ matrix + matrix @ right_blocks[index].T
                applied -= coupling * (cross_left[index] @ blocks[other] @ cross_right[index])
                result[offsets[index]:offsets[index + 1]] = applied.ravel()
            return result

        initial = np.concatenate([starting[np.ix_(left, right)].ravel() for left, right in zip(left_indices, right_indices)])
        if coupling == 0:
            initial += 1e-4 * self.generator.standard_normal(initial.size)
        diagonal = np.concatenate([(np.diag(left_block)[:, None] + np.diag(right_block)[None, :]).ravel()
                                   for left_block, right_block in zip(left_blocks, right_blocks)])
        if not self.symmetric:
            diagonal -= coupling * (np.diag(left_position)[:, None] * np.diag(right_position)[None, :]).ravel()
        vector, energy = davidson(action, diagonal, initial, tolerance, iterations, self.budget)
        decompositions = []
        entries = []
        for index, shape in enumerate(shapes):
            matrix = vector[offsets[index]:offsets[index + 1]].reshape(shape)
            if not matrix.size:
                decompositions.append(None)
                continue
            left_vectors, values, right_vectors = svd(matrix, full_matrices=False, check_finite=False, lapack_driver='gesdd')
            decompositions.append((left_vectors, values, right_vectors))
            entries.extend((value, index, level) for level, value in enumerate(values))
        entries.sort(reverse=True)
        kept = entries[:cap]
        kept = [entry for entry in kept if entry[0] > 1e-13]
        rank = len(kept)
        left_tensor = np.zeros((left_size * dimension, rank))
        right_tensor = np.zeros((rank, dimension * right_size))
        norm = np.sqrt(sum(value * value for value, _, _ in kept))
        for column, (value, block, level) in enumerate(kept):
            left_vectors, _, right_vectors = decompositions[block]
            left_tensor[left_indices[block], column] = left_vectors[:, level] * (value / norm if direction < 0 else 1)
            right_tensor[column, right_indices[block]] = right_vectors[level] * (value / norm if direction > 0 else 1)
        self.tensors[site] = left_tensor.reshape(left_size, dimension, rank)
        self.tensors[site + 1] = right_tensor.reshape(rank, dimension, right_size)
        self.charges[site + 1] = np.array([block for _, block, _ in kept])
        return energy

    def sweep(self, cap, tolerance=1e-7, iterations=60):
        energy = np.inf
        for direction in (1, -1):
            sites = range(self.length - 1) if direction > 0 else range(self.length - 2, -1, -1)
            for site in sites:
                if self.budget.expired(0.06):
                    return energy, False
                energy = self.pair(site, direction, cap, tolerance, iterations)
                if direction > 0:
                    self.update_left(site)
                else:
                    self.update_right(site + 1)
        return energy, True

    def single(self, site, tolerance):
        tensor = self.tensors[site]
        shape = tensor.shape
        left_energy, left_position = self.enlarged_left(site)
        right_energy, right_position = self.right[site + 1]
        coupling = self.coupling[site] if site + 1 < self.length else 0.
        matrix_shape = (shape[0] * shape[1], shape[2])
        if self.symmetric:
            parity = self.charges[site][:, None, None] ^ self.physical[site][None, :, None] ^ self.charges[site + 1][None, None, :]
            indices = np.flatnonzero(parity.ravel() == 0)
        else:
            indices = np.arange(tensor.size)

        def action(vector):
            matrix = np.zeros(tensor.size)
            matrix[indices] = vector
            matrix = matrix.reshape(matrix_shape)
            result = left_energy @ matrix + matrix @ right_energy.T
            result -= coupling * (left_position @ matrix @ right_position.T)
            return result.ravel()[indices]

        diagonal = np.diag(left_energy)[:, None] + np.diag(right_energy)[None, :]
        diagonal -= coupling * (np.diag(left_position)[:, None] * np.diag(right_position)[None, :])
        vector, energy = davidson(action, diagonal.ravel()[indices], tensor.ravel()[indices], tolerance, 50, self.budget)
        result = np.zeros(tensor.size)
        result[indices] = vector
        self.tensors[site] = result.reshape(shape)
        return energy

    def move_center(self, site, direction):
        tensor = self.tensors[site]
        left, physical, right = tensor.shape
        if direction > 0:
            matrix = tensor.reshape(left * physical, right)
            row_parity = (self.charges[site][:, None] ^ self.physical[site][None, :]).ravel()
            column_parity = self.charges[site + 1]
        else:
            matrix = tensor.reshape(left, physical * right).T
            row_parity = (self.physical[site][:, None] ^ self.charges[site + 1][None, :]).ravel()
            column_parity = self.charges[site]
        orthogonal = np.zeros_like(matrix)
        triangular = np.zeros((matrix.shape[1], matrix.shape[1]))
        for charge in range(2 if self.symmetric else 1):
            rows = np.flatnonzero(row_parity == charge) if self.symmetric else np.arange(matrix.shape[0])
            columns = np.flatnonzero(column_parity == charge) if self.symmetric else np.arange(matrix.shape[1])
            if not len(columns):
                continue
            block, factor = np.linalg.qr(matrix[np.ix_(rows, columns)], mode='reduced')
            orthogonal[np.ix_(rows, columns)] = block
            triangular[np.ix_(columns, columns)] = factor
        if direction > 0:
            self.tensors[site] = orthogonal.reshape(left, physical, right)
            self.tensors[site + 1] = np.tensordot(triangular, self.tensors[site + 1], axes=(1, 0))
        else:
            self.tensors[site] = orthogonal.T.reshape(left, physical, right)
            self.tensors[site - 1] = np.tensordot(self.tensors[site - 1], triangular.T, axes=(2, 0))

    def refine(self, tolerance=1e-9):
        energy = np.inf
        for direction in (1, -1):
            sites = range(self.length) if direction > 0 else range(self.length - 1, -1, -1)
            for site in sites:
                if self.budget.expired(0.06):
                    return energy, False
                energy = self.single(site, tolerance)
                if direction > 0 and site + 1 < self.length:
                    self.move_center(site, direction)
                    self.update_left(site)
                elif direction < 0 and site:
                    self.move_center(site, direction)
                    self.update_right(site)
        return energy, True

    def output(self):
        return [np.einsum('ps,asb->apb', basis, tensor, optimize=True)
                for basis, tensor in zip(self.bases, self.tensors)]


def optimize(request, wall_start=None):
    budget = Budget(request, wall_start)
    engine = DMRG(request, budget, 'cat')
    cap = request['bond_cap']
    previous = np.inf
    for sweep_index in range(2 if request['budget_seconds'] <= 8 else 8):
        active = min(cap, 4 if sweep_index == 0 else cap)
        tolerance = 2e-5 if sweep_index == 0 else 2e-8
        energy, complete = engine.sweep(active, tolerance, 70)
        if not complete:
            break
        if sweep_index == 0 and request['sector'] == 'any' and request['budget_seconds'] > 8 and not budget.expired(3.):
            alternative = DMRG(request, budget, 'product')
            _, alternative_complete = alternative.sweep(active, tolerance, 70)
            if alternative_complete:
                engine.reflect_if_better()
                alternative.reflect_if_better()
                engine.update_right(0)
                alternative.update_right(0)
                if alternative.right[0][0].item() < engine.right[0][0].item():
                    engine = alternative
                energy = engine.right[0][0].item()
        if sweep_index > 1 and abs(previous - energy) < 1e-8 * request['n_sites']:
            break
        previous = energy
    if complete:
        if not budget.expired(0.2):
            engine.reflect_if_better()
        previous = np.inf
        for sweep_index in range(20):
            energy, complete = engine.refine()
            if not complete or abs(previous - energy) < 2e-11 * request['n_sites']:
                break
            previous = energy
    return engine.output()
