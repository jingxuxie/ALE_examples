import time
from dataclasses import dataclass

import numpy as np
from scipy.linalg import svd
from scipy.sparse.linalg import ArpackNoConvergence, LinearOperator, eigsh

from eigensolver import davidson


@dataclass
class Model:
    charges: np.ndarray
    onsite: list
    operators: dict
    links: list
    family: str

    @property
    def length(self):
        return len(self.onsite)

    @property
    def dimension(self):
        return len(self.charges)


def make_model(case):
    family = case['family']
    length = case['length']
    if family == 'bose_hubbard':
        charges = np.arange(case['nmax'] + 1)
        number = np.diag(charges.astype(float))
        minus = np.diag(np.sqrt(charges[1:]), 1)
        operators = {'p': minus.T.copy(), 'm': minus, 'z': number}
        onsite = [0.5 * interaction * (number @ number - number) + potential * number
                  for interaction, potential in zip(case['interaction'], case['potential'])]
        links = [[] for _ in range(length - 1)]
        for bond in case['bonds']:
            left, right = sorted(bond['sites'])
            if right != left + 1:
                raise ValueError('Non-neighbor boson bond')
            links[left].extend([(-bond['hopping'], 'p', 'm'), (-bond['hopping'], 'm', 'p')])
    elif family == 'spin1_chain':
        charges = np.arange(-1, 2)
        number = np.diag(charges.astype(float))
        plus = np.diag(np.sqrt(2.0 - charges[:-1] * (charges[:-1] + 1)), -1)
        operators = {'p': plus, 'm': plus.T.copy(), 'z': number}
        onsite = [anisotropy * (number @ number) - field * number
                  for anisotropy, field in zip(case['single_ion'], case['field'])]
        links = [[] for _ in range(length - 1)]
        for bond in case['bonds']:
            left, right = sorted(bond['sites'])
            if right != left + 1:
                raise ValueError('Non-neighbor spin-one bond')
            links[left].extend([(bond['jxy'] / 2, 'p', 'm'),
                                (bond['jxy'] / 2, 'm', 'p'), (bond['jz'], 'z', 'z')])
    elif family == 'spinhalf_ladder':
        charges = np.array([-1, 0, 0, 1])
        number = np.diag([-0.5, 0.5])
        plus = np.array([[0., 0.], [1., 0.]])
        identity = np.eye(2)
        operators = {}
        for name, operator in [('p', plus), ('m', plus.T), ('z', number)]:
            operators[name + '0'] = np.kron(operator, identity)
            operators[name + '1'] = np.kron(identity, operator)
        onsite = []
        for rung in range(length // 2):
            matrix = np.zeros((4, 4))
            for leg in range(2):
                site = 2 * rung + leg
                local = operators['z' + str(leg)]
                matrix += case['single_ion'][site] * (local @ local) - case['field'][site] * local
            onsite.append(matrix)
        links = [[] for _ in range(length // 2 - 1)]
        for bond in case['bonds']:
            left, right = sorted(bond['sites'])
            left_rung, left_leg = divmod(left, 2)
            right_rung, right_leg = divmod(right, 2)
            terms = [(bond['jxy'] / 2, 'p', 'm'), (bond['jxy'] / 2, 'm', 'p'),
                     (bond['jz'], 'z', 'z')]
            for coefficient, left_name, right_name in terms:
                left_name += str(left_leg)
                right_name += str(right_leg)
                if left_rung == right_rung:
                    onsite[left_rung] += coefficient * (operators[left_name] @ operators[right_name])
                elif right_rung == left_rung + 1:
                    links[left_rung].append((coefficient, left_name, right_name))
                else:
                    raise ValueError('Non-neighbor rung bond')
    else:
        raise ValueError(family)
    return Model(charges, onsite, operators, links, family)


def groups(charges):
    return {int(charge): np.flatnonzero(charges == charge) for charge in np.unique(charges)}


class Block:
    def __init__(self, charges, hamiltonian, operators):
        self.charges = np.asarray(charges, dtype=int)
        self.hamiltonian = hamiltonian
        self.operators = operators


def vacuum(model):
    return Block(np.array([0]), np.zeros((1, 1)),
                 {name: np.zeros((1, 1)) for name in model.operators})


class Enlarged:
    def __init__(self, model, block, site, left):
        dimension = model.dimension
        old_dimension = len(block.charges)
        if left:
            self.charges = (block.charges[:, None] + model.charges[None, :]).ravel()
            link = model.links[site - 1] if site > 0 else []
            terms = [(coefficient, block.operators[left_name], model.operators[right_name])
                     for coefficient, left_name, right_name in link]
        else:
            self.charges = (model.charges[:, None] + block.charges[None, :]).ravel()
            link = model.links[site] if site < model.length - 1 else []
            terms = [(coefficient, block.operators[right_name], model.operators[left_name])
                     for coefficient, left_name, right_name in link]
        self.indices = groups(self.charges)
        factors = {}
        self.hamiltonian = {}
        for charge, indices in self.indices.items():
            if left:
                old, physical = np.divmod(indices, dimension)
            else:
                physical, old = np.divmod(indices, old_dimension)
            factors[charge] = old, physical
            old_index = np.ix_(old, old)
            physical_index = np.ix_(physical, physical)
            matrix = block.hamiltonian[old_index] * (physical[:, None] == physical[None, :])
            matrix += model.onsite[site][physical_index] * (old[:, None] == old[None, :])
            for coefficient, old_operator, physical_operator in terms:
                matrix += coefficient * old_operator[old_index] * physical_operator[physical_index]
            self.hamiltonian[charge] = matrix
        self.operators = {}
        for name, local in model.operators.items():
            rows, columns = np.nonzero(local)
            delta = int(model.charges[rows[0]] - model.charges[columns[0]]) if len(rows) else 0
            blocks = {}
            for charge, (old_in, physical_in) in factors.items():
                if charge + delta in factors:
                    old_out, physical_out = factors[charge + delta]
                    blocks[charge + delta, charge] = (
                        local[np.ix_(physical_out, physical_in)] * (old_out[:, None] == old_in[None, :]))
            self.operators[name] = blocks

    def project(self, isometries, new_charges):
        new_indices = groups(new_charges)
        dimension = len(new_charges)
        matrix = np.zeros((dimension, dimension))
        for charge, isometry in isometries.items():
            indices = new_indices[charge]
            matrix[np.ix_(indices, indices)] = isometry.T @ self.hamiltonian[charge] @ isometry
        operators = {}
        for name, blocks in self.operators.items():
            operator = np.zeros((dimension, dimension))
            for (out_charge, in_charge), block in blocks.items():
                if out_charge in isometries and in_charge in isometries:
                    operator[np.ix_(new_indices[out_charge], new_indices[in_charge])] = (
                        isometries[out_charge].T @ block @ isometries[in_charge])
            operators[name] = operator
        return Block(new_charges, matrix, operators)


class Effective:
    def __init__(self, left, right, link, sector):
        self.left = left
        self.right = right
        self.sector = sector
        self.charges = [charge for charge in left.indices if sector - charge in right.indices]
        self.shapes = [(len(left.indices[charge]), len(right.indices[sector - charge])) for charge in self.charges]
        sizes = [rows * columns for rows, columns in self.shapes]
        self.offsets = np.cumsum([0] + sizes)
        self.size = int(self.offsets[-1])
        self.hleft = [left.hamiltonian[charge] for charge in self.charges]
        self.hright = [right.hamiltonian[sector - charge].T.copy() for charge in self.charges]
        self.cross = []
        positions = {charge: position for position, charge in enumerate(self.charges)}
        for coefficient, left_name, right_name in link:
            for (out_charge, in_charge), left_operator in left.operators[left_name].items():
                if out_charge not in positions or in_charge not in positions:
                    continue
                key = (sector - out_charge, sector - in_charge)
                if key not in right.operators[right_name]:
                    continue
                right_operator = right.operators[right_name][key].T.copy()
                left_operator = coefficient * left_operator
                left_first = left_operator.shape[0] * right_operator.shape[0] * (
                    left_operator.shape[1] + right_operator.shape[1]) <= (
                    left_operator.shape[1] * right_operator.shape[1] * (
                        left_operator.shape[0] + right_operator.shape[0]))
                self.cross.append((positions[out_charge], positions[in_charge],
                                   left_operator, right_operator, left_first))

    def unpack(self, vector):
        return [vector[self.offsets[position]:self.offsets[position + 1]].reshape(shape)
                for position, shape in enumerate(self.shapes)]

    def matvec(self, vector):
        inputs = self.unpack(vector)
        result = np.empty_like(vector)
        outputs = self.unpack(result)
        for position, matrix in enumerate(inputs):
            outputs[position][:] = self.hleft[position] @ matrix + matrix @ self.hright[position]
        for destination, source, left_operator, right_operator, left_first in self.cross:
            if left_first:
                outputs[destination] += (left_operator @ inputs[source]) @ right_operator
            else:
                outputs[destination] += left_operator @ (inputs[source] @ right_operator)
        return result

    def initial(self, first, second, middle_charges):
        first_matrix = first.reshape(-1, first.shape[2])
        second_matrix = second.reshape(second.shape[0], -1)
        middle_groups = groups(middle_charges)
        vector = np.zeros(self.size)
        blocks = self.unpack(vector)
        for position, charge in enumerate(self.charges):
            if charge in middle_groups:
                middle = middle_groups[charge]
                blocks[position][:] = (
                    first_matrix[np.ix_(self.left.indices[charge], middle)] @
                    second_matrix[np.ix_(middle, self.right.indices[self.sector - charge])])
        norm = np.linalg.norm(vector)
        if norm < 1e-14:
            vector = np.random.default_rng(713).normal(size=self.size)
            norm = np.linalg.norm(vector)
        return vector / norm

    def optimize(self, initial, tolerance):
        return davidson(self, initial, tolerance, Effective.optimize_arpack)

    def optimize_arpack(self, initial, tolerance):
        if self.size <= 3:
            matrix = np.column_stack([self.matvec(vector) for vector in np.eye(self.size)])
            values, vectors = np.linalg.eigh(matrix)
            return float(values[0]), vectors[:, 0]
        operator = LinearOperator((self.size, self.size), matvec=self.matvec, dtype=np.float64)
        try:
            values, vectors = eigsh(operator, k=1, which='SA', v0=initial,
                                    tol=tolerance, ncv=min(16, self.size), maxiter=100)
            return float(values[0]), vectors[:, 0]
        except ArpackNoConvergence as error:
            if len(error.eigenvalues):
                return float(error.eigenvalues[0]), error.eigenvectors[:, 0]
            values, vectors = eigsh(operator, k=1, which='SA', v0=initial,
                                    tol=max(tolerance, 1e-7), ncv=min(32, self.size), maxiter=300)
            return float(values[0]), vectors[:, 0]

    def split(self, vector, maximum_bond, cutoff, move_right, first_shape, second_shape):
        decompositions = {}
        candidates = []
        for charge, matrix in zip(self.charges, self.unpack(vector)):
            left_vectors, singular, right_vectors = svd(matrix, full_matrices=False, check_finite=False,
                                                         lapack_driver='gesdd')
            decompositions[charge] = left_vectors, singular, right_vectors
            candidates.extend((float(value * value), charge, position) for position, value in enumerate(singular))
        candidates.sort(reverse=True)
        weights = np.array([candidate[0] for candidate in candidates])
        number = min(maximum_bond, len(candidates))
        discarded = np.maximum(0., weights.sum() - np.cumsum(weights))
        enough = np.flatnonzero(discarded <= cutoff)
        if len(enough):
            number = min(number, int(enough[0]) + 1)
        kept = {}
        for _, charge, position in candidates[:number]:
            kept[charge] = max(kept.get(charge, 0), position + 1)
        normalization = np.sqrt(weights[:number].sum())
        new_charges = np.concatenate([np.full(kept[charge], charge, dtype=int) for charge in sorted(kept)])
        new_groups = groups(new_charges)
        first = np.zeros((len(self.left.charges), number))
        second = np.zeros((number, len(self.right.charges)))
        isometries = {}
        for charge in sorted(kept):
            count = kept[charge]
            left_vectors, singular, right_vectors = decompositions[charge]
            left_vectors = left_vectors[:, :count]
            right_vectors = right_vectors[:count, :]
            singular = singular[:count] / normalization
            if move_right:
                first[np.ix_(self.left.indices[charge], new_groups[charge])] = left_vectors
                second[np.ix_(new_groups[charge], self.right.indices[self.sector - charge])] = singular[:, None] * right_vectors
                isometries[charge] = left_vectors
            else:
                first[np.ix_(self.left.indices[charge], new_groups[charge])] = left_vectors * singular[None, :]
                second[np.ix_(new_groups[charge], self.right.indices[self.sector - charge])] = right_vectors
                isometries[self.sector - charge] = right_vectors.T.copy()
        first = first.reshape(first_shape[0], first_shape[1], number)
        second = second.reshape(number, second_shape[1], second_shape[2])
        return first, second, new_charges, isometries, float(discarded[number - 1])


class State:
    def __init__(self, tensors, charges, sector):
        self.tensors = tensors
        self.charges = charges
        self.sector = sector

    def copy(self):
        return State([tensor.copy() for tensor in self.tensors],
                     [charge.copy() for charge in self.charges], self.sector)


def product_state(model, sector, orientation=1):
    length = model.length
    if model.family == 'bose_hubbard':
        occupations = [min(model.dimension - 1, max(0, sector // length))] * length
    elif model.family == 'spin1_chain':
        occupations = [2 if (site % 2 == 0) == (orientation > 0) else 0 for site in range(length)]
    else:
        occupations = [2 if (site % 2 == 0) == (orientation > 0) else 1 for site in range(length)]
    remaining = int(sector - sum(model.charges[occupation] for occupation in occupations))
    ordering = sorted(range(length), key=lambda site: abs(site - (length - 1) / 2))
    while remaining:
        changed = False
        for site in ordering:
            current = occupations[site]
            delta = 1 if remaining > 0 else -1
            options = np.flatnonzero(model.charges == model.charges[current] + delta)
            if len(options):
                occupations[site] = int(options[0])
                remaining -= delta
                changed = True
            if remaining == 0:
                break
        if not changed:
            raise ValueError('Unreachable conserved sector')
    tensors = []
    charges = [np.array([0])]
    for occupation in occupations:
        tensor = np.zeros((1, model.dimension, 1))
        tensor[0, occupation, 0] = 1.
        tensors.append(tensor)
        charges.append(charges[-1] + model.charges[occupation])
    return State(tensors, charges, int(sector))


def right_canonicalize(state, model):
    for site in range(model.length - 1, 0, -1):
        tensor = state.tensors[site]
        matrix = tensor.reshape(tensor.shape[0], -1)
        old_groups = groups(state.charges[site])
        column_charges = (state.charges[site + 1][None, :] - model.charges[:, None]).ravel()
        column_groups = groups(column_charges)
        transforms = []
        for charge, rows in old_groups.items():
            if charge not in column_groups:
                continue
            columns = column_groups[charge]
            submatrix = matrix[np.ix_(rows, columns)]
            left, singular, right = svd(submatrix, full_matrices=False, check_finite=False)
            keep = max(1, int(np.count_nonzero(singular > 1e-14)))
            transforms.append((charge, rows, columns, left[:, :keep] * singular[:keep], right[:keep]))
        new_charges = np.concatenate([np.full(item[4].shape[0], item[0], dtype=int) for item in transforms])
        new_tensor = np.zeros((len(new_charges), matrix.shape[1]))
        transfer = np.zeros((matrix.shape[0], len(new_charges)))
        offset = 0
        for charge, rows, columns, left, right in transforms:
            selected = np.arange(offset, offset + right.shape[0])
            new_tensor[np.ix_(selected, columns)] = right
            transfer[np.ix_(rows, selected)] = left
            offset += right.shape[0]
        state.tensors[site] = new_tensor.reshape(len(new_charges), tensor.shape[1], tensor.shape[2])
        previous = state.tensors[site - 1]
        state.tensors[site - 1] = (previous.reshape(-1, previous.shape[2]) @ transfer).reshape(
            previous.shape[0], previous.shape[1], len(new_charges))
        state.charges[site] = new_charges
    norm = np.linalg.norm(state.tensors[0])
    if norm < 1e-14:
        raise ValueError('Charge-shifting operator annihilated the state')
    state.tensors[0] /= norm


def shifted_state(ground, model, sector):
    state = ground.copy()
    difference = int(sector - state.sector)
    if difference == 0:
        return state
    delta = 1 if difference > 0 else -1
    names = ['p0', 'p1'] if model.family == 'spinhalf_ladder' else ['p']
    if delta < 0:
        names = [name.replace('p', 'm') for name in names]
    for step in range(abs(difference)):
        site = min(model.length - 1, max(0, (step + 1) * model.length // (abs(difference) + 1)))
        operator = model.operators[names[step % len(names)]]
        state.tensors[site] = np.einsum('st,atb->asb', operator, state.tensors[site])
        for bond in range(site + 1, model.length + 1):
            state.charges[bond] = state.charges[bond] + delta
        state.sector += delta
    try:
        right_canonicalize(state, model)
    except ValueError:
        return product_state(model, sector)
    return state


def build_right_blocks(model, state):
    blocks = [None] * (model.length + 1)
    blocks[-1] = vacuum(model)
    for site in range(model.length - 1, 0, -1):
        enlarged = Enlarged(model, blocks[site + 1], site, False)
        new_charges = state.sector - state.charges[site]
        new_groups = groups(new_charges)
        tensor = state.tensors[site].reshape(len(new_charges), -1).T
        isometries = {charge: tensor[np.ix_(enlarged.indices[charge], indices)]
                      for charge, indices in new_groups.items()}
        blocks[site] = enlarged.project(isometries, new_charges)
    return blocks


def run_dmrg(model, sector, schedule, deadline, initial=None, tolerance=2e-10, verbose=False):
    if model.length == 1:
        indices = np.flatnonzero(model.charges == sector)
        values, vectors = np.linalg.eigh(model.onsite[0][np.ix_(indices, indices)])
        tensor = np.zeros((1, model.dimension, 1))
        tensor[0, indices, 0] = vectors[:, 0]
        return float(values[0]), State([tensor], [np.array([0]), np.array([sector])], sector), []
    state = product_state(model, sector) if initial is None else initial.copy()
    right_blocks = build_right_blocks(model, state)
    left_blocks = [None] * (model.length + 1)
    left_blocks[0] = vacuum(model)
    history = []
    energy = None
    for sweep, requested_bond in enumerate(schedule):
        maximum_bond = requested_bond
        if history:
            remaining = deadline - time.monotonic()
            previous_duration = history[-1][3]
            if remaining < 1.3 * previous_duration:
                break
            previous_bond = max(tensor.shape[2] for tensor in state.tensors)
            affordable = int(previous_bond * (remaining / (1.5 * previous_duration)) ** (1 / 2.6))
            maximum_bond = min(maximum_bond, max(previous_bond, affordable))
        sweep_start = time.monotonic()
        previous_state = state.copy() if history else None
        truncation = 0.
        local_tolerance = 2e-8 if sweep < 2 else (2e-10 if sweep < 4 else 1e-12)
        if sweep >= 4 and history:
            local_tolerance = max(1e-12, min(1e-9, 1e-5 * np.sqrt(history[-1][2])))
        for move_right in [True, False]:
            positions = range(model.length - 1) if move_right else range(model.length - 2, -1, -1)
            for site in positions:
                if previous_state is not None and time.monotonic() > deadline:
                    return history[-1][0], previous_state, history
                left = Enlarged(model, left_blocks[site], site, True)
                right = Enlarged(model, right_blocks[site + 2], site + 1, False)
                effective = Effective(left, right, model.links[site], sector)
                initial_vector = effective.initial(state.tensors[site], state.tensors[site + 1],
                                                   state.charges[site + 1])
                energy, vector = effective.optimize(initial_vector, local_tolerance)
                first, second, charges, isometries, discarded = effective.split(
                    vector, maximum_bond, 2e-14, move_right,
                    state.tensors[site].shape, state.tensors[site + 1].shape)
                state.tensors[site] = first
                state.tensors[site + 1] = second
                state.charges[site + 1] = charges
                truncation = max(truncation, discarded)
                if move_right:
                    left_blocks[site + 1] = left.project(isometries, charges)
                else:
                    right_blocks[site + 1] = right.project(isometries, sector - charges)
        duration = time.monotonic() - sweep_start
        history.append((energy, maximum_bond, truncation, duration))
        if verbose:
            import sys
            print('sector', sector, 'sweep', sweep + 1, 'bond', maximum_bond, 'energy', energy,
                  'discarded', truncation, 'seconds', round(duration, 2), file=sys.stderr, flush=True)
        if len(history) >= 6:
            if abs(history[-1][0] - history[-2][0]) < tolerance and (
                    truncation < 2e-12 or maximum_bond >= schedule[-1]):
                break
        if time.monotonic() + 1.25 * duration > deadline:
            break
    return energy, state, history


class Measurements:
    def __init__(self, model, state):
        self.model = model
        self.blocks = []
        self.identity = np.eye(model.dimension)
        for site, tensor in enumerate(state.tensors):
            left_groups = groups(state.charges[site])
            right_groups = groups(state.charges[site + 1])
            blocks = {}
            for left_charge, rows in left_groups.items():
                for physical, local_charge in enumerate(model.charges):
                    right_charge = left_charge + int(local_charge)
                    if right_charge in right_groups:
                        columns = right_groups[right_charge]
                        blocks[left_charge, physical] = np.ascontiguousarray(tensor[:, physical, :][np.ix_(rows, columns)])
            self.blocks.append(blocks)
        self.left = [{(0, 0): np.ones((1, 1))}]
        for site in range(model.length):
            self.left.append(self.propagate(self.left[-1], site, self.identity))
        self.normalization = sum(float(np.trace(matrix)) for key, matrix in self.left[-1].items() if key[0] == key[1])

    def propagate(self, environment, site, operator):
        result = {}
        rows, columns = np.nonzero(operator)
        blocks = self.blocks[site]
        charges = self.model.charges
        for row, column in zip(rows, columns):
            coefficient = operator[row, column]
            for (bra_charge, ket_charge), matrix in environment.items():
                bra = blocks.get((bra_charge, row))
                ket = blocks.get((ket_charge, column))
                if bra is None or ket is None:
                    continue
                key = (bra_charge + int(charges[row]), ket_charge + int(charges[column]))
                contribution = coefficient * (bra.T @ matrix @ ket)
                if key in result:
                    result[key] += contribution
                else:
                    result[key] = contribution
        return result

    def measure(self, environment, site, operator):
        value = 0.
        rows, columns = np.nonzero(operator)
        blocks = self.blocks[site]
        charges = self.model.charges
        for row, column in zip(rows, columns):
            coefficient = operator[row, column]
            for (bra_charge, ket_charge), matrix in environment.items():
                if bra_charge + charges[row] != ket_charge + charges[column]:
                    continue
                bra = blocks.get((bra_charge, row))
                ket = blocks.get((ket_charge, column))
                if bra is not None and ket is not None:
                    value += coefficient * np.sum(bra * (matrix @ ket))
        return float(value / self.normalization)


def correlations(case, model, state):
    if not case['observables']:
        return []
    measurements = Measurements(model, state)
    identity = measurements.identity
    requests = {}
    result = [0.] * len(case['observables'])
    means = {}
    for position, observable in enumerate(case['observables']):
        first, last = observable['sites']
        kind = observable['kind']
        middle = identity
        coefficient = 1.
        subtract = 0.
        if model.family == 'spinhalf_ladder':
            first, first_leg = divmod(first, 2)
            last, last_leg = divmod(last, 2)
            if kind == 'zz':
                first_operator = model.operators['z' + str(first_leg)]
                last_operator = model.operators['z' + str(last_leg)]
            elif kind == 'xx':
                first_operator = model.operators['p' + str(first_leg)]
                last_operator = model.operators['m' + str(last_leg)]
                coefficient = 0.5
            else:
                raise ValueError(kind)
        elif kind in ['zz', 'string', 'density_connected']:
            first_operator = last_operator = model.operators['z']
            if kind == 'string':
                middle = np.diag(np.cos(np.pi * model.charges))
                coefficient = -1.
            elif kind == 'density_connected':
                for site in [first, last]:
                    if site not in means:
                        means[site] = measurements.measure(measurements.left[site], site, first_operator)
                subtract = means[first] * means[last]
        elif kind == 'one_body':
            first_operator = model.operators['p']
            last_operator = model.operators['m']
        else:
            raise ValueError(kind)
        if first == last:
            result[position] = coefficient * measurements.measure(
                measurements.left[first], first, first_operator @ last_operator) - subtract
            continue
        key = (first, first_operator.tobytes(), middle.tobytes())
        if key not in requests:
            requests[key] = first_operator, middle, {}
        destinations = requests[key][2]
        destinations.setdefault(last, []).append((position, last_operator, coefficient, subtract))
    for (first, _, _), (first_operator, middle, destinations) in requests.items():
        environment = measurements.propagate(measurements.left[first], first, first_operator)
        final_site = max(destinations)
        for site in range(first + 1, final_site + 1):
            for position, last_operator, coefficient, subtract in destinations.get(site, []):
                result[position] = coefficient * measurements.measure(environment, site, last_operator) - subtract
            if site < final_site:
                environment = measurements.propagate(environment, site, middle)
    return result
