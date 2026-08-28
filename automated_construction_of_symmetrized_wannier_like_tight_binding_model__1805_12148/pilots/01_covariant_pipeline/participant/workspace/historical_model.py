"""Historical TBmodels dense subset; see HISTORY.md for provenance."""

from __future__ import annotations

import collections as co
import itertools
import re
import typing as ty
import warnings

import numpy as np
import scipy.linalg as la

from dense_support import sp

HoppingType = ty.Dict[ty.Tuple[int, ...], ty.Any]


class Model:
    def set_sparse(self, sparse=False):
        if sparse:
            raise ValueError("This historical extraction supports dense matrices only.")
        self._sparse = False
        self._matrix_type = np.array

    def _array_cast(self, value):
        return np.asarray(value)

    def __init__(
        self,
        *,
        on_site: ty.Optional[ty.Sequence[float]] = None,
        hop: ty.Optional[HoppingType] = None,
        size: ty.Optional[int] = None,
        dim: ty.Optional[int] = None,
        occ: ty.Optional[int] = None,
        pos: ty.Optional[ty.Sequence[ty.Sequence[float]]] = None,
        uc: ty.Optional[np.ndarray] = None,
        contains_cc: bool = True,
        cc_check_tolerance: float = 1e-12,
        sparse: bool = False,
    ):
        if hop is None:
            hop = dict()

        # ---- SPARSITY ----
        self._sparse: bool
        self._matrix_type: ty.Callable[..., ty.Any]
        self.set_sparse(sparse)

        # ---- SIZE ----
        self._init_size(size=size, on_site=on_site, hop=hop, pos=pos)

        # ---- DIMENSION ----
        self._init_dim(dim=dim, hop=hop, pos=pos, uc=uc)

        # ---- UNIT CELL ----
        self.uc = None if uc is None else np.array(uc)  # implicit copy

        # ---- HOPPING TERMS AND POSITIONS ----
        self._init_hop_pos(
            on_site=on_site,
            hop=hop,
            pos=pos,
            contains_cc=contains_cc,
            cc_check_tolerance=cc_check_tolerance,
        )

        # ---- CONSISTENCY CHECK FOR SIZE ----
        self._check_size_hop()

        # ---- CONSISTENCY CHECK FOR DIM ----
        self._check_dim()

        # ---- OCCUPATION NR ----
        self.occ = None if (occ is None) else int(occ)

    def _init_size(self, size, on_site, hop, pos):
        """
        Sets the size of the system (number of orbitals).
        """
        if size is not None:
            self.size = size
        elif on_site is not None:
            self.size = len(on_site)
        elif pos is not None:
            self.size = len(pos)
        elif hop:
            self.size = next(iter(hop.values())).shape[0]
        else:
            raise ValueError(
                "Empty hoppings dictionary supplied and no size, on-site energies or positions given. Cannot determine the size of the system."
            )

    def _init_dim(self, dim, hop, pos, uc):
        r"""
        Sets the system's dimensionality.
        """
        if dim is not None:
            self.dim = dim
        elif pos is not None:
            self.dim = len(pos[0])
        elif hop:
            self.dim = len(next(iter(hop.keys())))
        elif uc is not None:
            self.dim = len(uc[0])
        else:
            raise ValueError(
                "No dimension specified and no positions, hoppings, or unit cell are given. The dimensionality of the system cannot be determined."
            )

        self._zero_vec = tuple([0] * self.dim)

    def _init_hop_pos(self, on_site, hop, pos, contains_cc, cc_check_tolerance):
        """
        Sets the hopping terms and positions, mapping the positions to the UC (and changing the hoppings accordingly) if necessary.
        """
        # The double-constructor is needed to avoid a double-constructor in the sparse to-array
        # but still allow for the dtype argument.
        hop = {
            tuple(key): self._matrix_type(self._matrix_type(value), dtype=complex)
            for key, value in hop.items()
        }

        # positions
        if pos is None:
            self.pos = np.zeros((self.size, self.dim))
        elif len(pos) == self.size and all(len(p) == self.dim for p in pos):
            pos, hop = self._map_to_uc(pos, hop)
            self.pos = np.array(pos)  # implicit copy
        else:
            if len(pos) != self.size:
                raise ValueError(
                    "Invalid argument for 'pos': The number of positions must be the same as the size (number of orbitals) of the system."
                )
            raise ValueError(
                "Invalid argument for 'pos': The length of each position must be the same as the dimensionality of the system."
            )

        if contains_cc:
            hop = self._reduce_hop(hop, cc_check_tolerance=cc_check_tolerance)
        else:
            hop = self._map_hop_positive_R(hop)
        # use partial instead of lambda to allow for pickling
        self.hop = co.defaultdict(self._empty_matrix)
        for R, h_mat in hop.items():
            if not np.any(h_mat):
                continue
            self.hop[R] = self._matrix_type(h_mat)
        # add on-site terms
        if on_site is not None:
            if len(on_site) != self.size:
                raise ValueError(
                    "The number of on-site energies {} does not match the size of the system {}".format(
                        len(on_site), self.size
                    )
                )
            self.hop[self._zero_vec] += 0.5 * self._matrix_type(np.diag(on_site))

    def _map_to_uc(self, pos, hop):
        """
        hoppings in csr format
        """
        uc_offsets = [np.array(np.floor(p), dtype=int) for p in pos]
        # ---- common case: already mapped into the UC ----
        if all([all(o == 0 for o in offset) for offset in uc_offsets]):
            return pos, hop

        # ---- uncommon case: handle mapping ----
        new_pos = [np.array(p) % 1 for p in pos]
        new_hop = co.defaultdict(
            lambda: np.zeros((self.size, self.size), dtype=complex)
        )
        for R, hop_mat in hop.items():
            hop_mat = np.array(hop_mat)
            for i0, row in enumerate(hop_mat):
                for i1, t in enumerate(row):
                    if t != 0:
                        R_new = tuple(
                            np.array(R, dtype=int) + uc_offsets[i1] - uc_offsets[i0]
                        )
                        new_hop[R_new][i0][i1] += t
        new_hop = {key: self._matrix_type(value) for key, value in new_hop.items()}
        return new_pos, new_hop

    @staticmethod
    def _reduce_hop(hop, cc_check_tolerance):
        """
        Reduce the full hoppings representation (with cc) to the reduced one (without cc, zero-terms halved).
        """
        # Consistency checks
        failed_R = []
        res = dict()
        for R, mat in hop.items():
            equiv_mat = hop.get(tuple(-x for x in R), np.zeros(mat.shape)).T.conjugate()
            diff_norm = la.norm(mat - equiv_mat)
            if diff_norm > cc_check_tolerance:
                failed_R.append((R, diff_norm))

            avg_mat = (mat + equiv_mat) / 2

            try:
                if R[np.nonzero(R)[0][0]] > 0:
                    res[R] = avg_mat
            # Case R = 0
            except IndexError:
                res[R] = avg_mat / 2

        if failed_R:
            raise ValueError(
                "The provided hoppings do not correspond to a hermitian Hamiltonian. hoppings[-R] = hoppings[R].H is not fulfilled for the following values:\n"
                + "\n".join(
                    f"R={R}, delta_norm={diff_norm}"
                    for R, diff_norm in sorted(failed_R, key=lambda val: -val[1])
                )
            )

        return res

    def _map_hop_positive_R(self, hop: HoppingType) -> HoppingType:
        """
        Maps hoppings with a negative first non-zero index in R to their positive counterpart.
        """
        new_hop: HoppingType = co.defaultdict(self._empty_matrix)
        for R, mat in hop.items():
            try:
                if R[np.nonzero(R)[0][0]] > 0:
                    new_hop[R] += mat
                else:
                    minus_R = tuple(-x for x in R)
                    new_hop[minus_R] += mat.transpose().conjugate()
            except IndexError:
                # make sure the zero term is also hermitian
                # This only really needed s.t. the representation is unique.
                # The Hamiltonian is anyway made hermitian later.
                new_hop[R] += 0.5 * mat + 0.5 * mat.conjugate().transpose()
        return new_hop

    def _check_size_hop(self):
        """
        Consistency check for the size of the hopping matrices.
        """
        for h_mat in self.hop.values():
            if not h_mat.shape == (self.size, self.size):
                raise ValueError(
                    "Hopping matrix of shape {0} found, should be ({1},{1}).".format(
                        h_mat.shape, self.size
                    )
                )

    def _check_dim(self):
        """Consistency check for the dimension of the hoppings and unit cell. The position is checked in _init_hop_pos"""
        for key in self.hop.keys():
            if len(key) != self.dim:
                raise ValueError(
                    "The length of R = {} does not match the dimensionality of the system ({})".format(
                        key, self.dim
                    )
                )
        if self.uc is not None:
            if self.uc.shape != (self.dim, self.dim):
                raise ValueError(
                    "Inconsistend dimension of the unit cell: {}, does not match the dimensionality of the system ({})".format(
                        self.uc.shape, self.dim
                    )
                )

    @classmethod
    def from_hop_list(
        cls,
        *,
        hop_list: ty.Iterable[ty.Tuple[complex, int, int, ty.Tuple[int, ...]]] = (),
        size: ty.Optional[int] = None,
        **kwargs,
    ) -> "Model":
        """
        Create a :class:`.Model` from a list of hopping terms.

        Parameters
        ----------
        hop_list :
            List of hopping terms. Each hopping term has the form
            [t, orbital_1, orbital_2, R], where

                * ``t``: strength of the hopping
                * ``orbital_1``: index of the first involved orbital
                * ``orbital_2``: index of the second involved orbital
                * ``R``: lattice vector of the unit cell containing the second orbital.
        size :
            Number of states. Defaults to the length of the on-site energies given, if such are given.
        kwargs :
            Any :class:`.Model` keyword arguments.
        """
        if size is None:
            try:
                size = len(kwargs["on_site"])
            except KeyError as exc:
                raise ValueError(
                    "No on-site energies and no size given. The size of the system cannot be determined."
                ) from exc

        class _hop:
            """
            POD for hoppings
            """

            def __init__(self):
                self.data = []
                self.row_idx = []
                self.col_idx = []

            def append(self, data, row_idx, col_idx):
                self.data.append(data)
                self.row_idx.append(row_idx)
                self.col_idx.append(col_idx)

        # create data, row_idx, col_idx for setting up the CSR matrices
        hop_list_dict: ty.Mapping[ty.Tuple[int, ...], _hop] = co.defaultdict(_hop)
        R: ty.Tuple[int, ...]
        for t, i, j, R in hop_list:
            R_vec = tuple(R)
            hop_list_dict[R_vec].append(t, i, j)

        # creating CSR matrices
        hop_dict = dict()
        for key, val in hop_list_dict.items():
            hop_dict[key] = sp.csr(
                (val.data, (val.row_idx, val.col_idx)),
                dtype=complex,
                shape=(size, size),
            )

        return cls(size=size, hop=hop_dict, **kwargs)

    @staticmethod
    def _read_hr(iterator, ignore_orbital_order=False):
        r"""
        read the number of wannier functions and the hopping entries
        from *hr.dat and converts them into the right format
        """
        next(iterator)  # skip first line
        num_wann = int(next(iterator))
        nrpts = int(next(iterator))

        # get degeneracy points
        deg_pts = []
        # order in zip important because else the next data element is consumed
        for _, line in zip(range(int(np.ceil(nrpts / 15))), iterator):
            deg_pts.extend(int(x) for x in line.split())
        assert len(deg_pts) == nrpts

        num_wann_square = num_wann ** 2

        def to_entry(line, i):
            """Turns a line (string) into a hop_list entry"""
            entry = line.split()
            orbital_a = int(entry[3]) - 1
            orbital_b = int(entry[4]) - 1
            # test consistency of orbital numbers
            if not ignore_orbital_order:
                if not (orbital_a == i % num_wann) and (
                    orbital_b == (i % num_wann_square) // num_wann
                ):
                    raise ValueError(f"Inconsistent orbital numbers in line '{line}'")
            return [
                (float(entry[5]) + 1j * float(entry[6]))
                / (deg_pts[i // num_wann_square]),
                orbital_a,
                orbital_b,
                [int(x) for x in entry[:3]],
            ]

        # skip random empty lines
        lines_nonempty = (l for l in iterator if l.strip())
        hop_list = (to_entry(line, i) for i, line in enumerate(lines_nonempty))

        return num_wann, hop_list

    def _empty_matrix(self):
        """Returns an empty matrix, either sparse or dense according to the current setting. The size is determined by the system's size"""
        return self._matrix_type(np.zeros((self.size, self.size), dtype=complex))

    @property
    def _input_kwargs(self):
        return dict(
            hop=self.hop,
            pos=self.pos,
            occ=self.occ,
            uc=self.uc,
            contains_cc=False,
            sparse=self._sparse,
        )

    def hamilton(
        self,
        k: ty.Union[ty.Sequence[float], ty.Sequence[ty.Sequence[float]]],
        convention: int = 2,
    ) -> np.ndarray:
        """
        Calculates the Hamilton matrix for a given k-point or list of
        k-points.

        Parameters
        ----------
        k :
            The k-point at which the Hamiltonian is evaluated. If a list
            of k-points is given, the result will be the corresponding
            list of Hamiltonians.
        convention :
            Choice of convention to calculate the Hamilton matrix. See
            explanation in `the PythTB documentation
            <http://www.physics.rutgers.edu/pythtb/_downloads/pythtb-formalism.pdf>`_ .
            Valid choices are 1 or 2.
        """
        if convention not in [1, 2]:
            raise ValueError(
                "Invalid value '{}' for 'convention': must be either '1' or '2'".format(
                    convention
                )
            )
        k_array = np.array(k, ndmin=1)
        if k_array.ndim == 1:
            single_point = True
            k_array = k_array.reshape((1, -1))
        else:
            single_point = False
        H = np.zeros((k_array.shape[0], self.size, self.size), dtype=complex)
        tmp_array = np.empty_like(H)
        for R, hop in self.hop.items():
            # When the hopping matrices are very large, allocating new
            # arrays for the result of this multiplication (which is
            # of size len(k_array) * self.size**2) becomes expensive.
            # To avoid this, we reuse the same temporary array - even
            # if this is _slightly_ slower for single k-point calculations.
            np.multiply(
                np.exp(2j * np.pi * np.dot(k_array, R)).reshape((-1, 1, 1)),
                self._array_cast(hop)[np.newaxis, :, :],
                out=tmp_array,
            )
            H += tmp_array
        H += H.conjugate().transpose((0, 2, 1))
        if convention == 1:
            pos_exponential = np.array(
                [[np.exp(2j * np.pi * np.dot(k_array, p)) for p in self.pos]]
            ).transpose((2, 0, 1))
            H = pos_exponential.conjugate().transpose((0, 2, 1)) * H * pos_exponential

        if single_point:
            return H[0]
        return H

    def slice_orbitals(self, slice_idx: ty.List[int]) -> "Model":
        """
        Returns a new model with only the orbitals as given in the
        ``slice_idx``. This can also be used to re-order the orbitals.

        Parameters
        ----------
        slice_idx :
            Orbital indices that will be in the resulting model.
        """
        new_pos = self.pos[tuple(slice_idx), :]
        new_hop = {
            key: np.array(val)[np.ix_(slice_idx, slice_idx)]
            for key, val in self.hop.items()
        }
        return Model(**co.ChainMap(dict(hop=new_hop, pos=new_pos), self._input_kwargs))

    def supercell(  # pylint: disable=too-many-locals
        self, size: ty.Sequence[int]
    ) -> "Model":
        """Generate a model for a supercell of the current unit cell.

        Parameters
        ----------
        size :
            The size of the supercell, given as integer multiples of the
            current lattice vectors
        """
        size_array = np.array(size).astype(dtype=int, casting="safe")
        if size_array.shape != (self.dim,):
            raise ValueError(
                "The given 'size' has incorrect shape {}, should be {}.".format(
                    size_array.shape, (self.dim,)
                )
            )
        volume_multiplier = np.prod(size_array)
        new_occ = None if self.occ is None else volume_multiplier * self.occ
        if self.uc is None:
            new_uc = None
        else:
            new_uc = (self.uc.T * size_array).T

        # the new positions, normalized to the supercell
        new_pos: ty.List[np.ndarray] = []
        reduced_pos = np.array([p / size_array for p in self.pos])
        uc_offsets = list(
            np.array(offset)
            for offset in itertools.product(*[range(n) for n in size_array])
        )
        for current_uc_offset in uc_offsets:
            new_pos.extend(reduced_pos + (current_uc_offset / size_array))

        new_size = self.size * volume_multiplier
        new_hop: HoppingType = co.defaultdict(
            lambda: np.zeros((new_size, new_size), dtype=complex)
        )

        # Can be used to get the orbital offset of a given unit cell
        # by taking the inner product with the unit cell position.
        uc_idx_multiplier = (
            np.array([np.prod(size[i:], dtype=int) for i in range(1, len(size) + 1)])
            * self.size
        )

        for uc1_idx, uc1_pos in enumerate(uc_offsets):
            uc1_idx_offset = uc1_idx * self.size

            for R, hop_mat in self.hop.items():
                hop_mat = self._array_cast(hop_mat)

                # position of the uc of orbital 2, not mapped inside supercell
                full_uc2_pos = uc1_pos + R
                # mapped into the supercell
                uc2_pos = full_uc2_pos % size_array
                uc2_idx_offset = np.inner(uc_idx_multiplier, uc2_pos)

                # R in terms of supercells
                new_R = np.array(np.floor(full_uc2_pos / size_array), dtype=int)

                new_hop[tuple(new_R)][
                    uc1_idx_offset : uc1_idx_offset + self.size,
                    uc2_idx_offset : uc2_idx_offset + self.size,
                ] += hop_mat

        return Model(
            **co.ChainMap(
                dict(
                    hop=new_hop,
                    occ=new_occ,
                    uc=new_uc,
                    size=new_size,
                    pos=new_pos,
                    contains_cc=False,
                ),
                self._input_kwargs,
            )
        )

    def change_unit_cell(  # pylint: disable=too-many-branches
        self,
        *,
        uc: ty.Optional[ty.Sequence[ty.Sequence[float]]] = None,
        offset: ty.Sequence[float] = (0, 0, 0),
        cartesian: bool = False,
    ) -> "Model":
        """Return a model with a different unit cell of the same volume.

        Creates a model with a changed unit cell - with a different
        shape and / or origin. The new unit cell must be compatible
        with the current lattice, and have the same volume.

        Parameters
        ----------
        uc :
            The new unit cell shape. Lattice vectors are given as rows
            in a (dim x dim) matrix. If no unit cell is given, the
            current unit cell shape is kept.
        offset :
            The position of the new unit cell origin, relative to the old
            one.
        cartesian :
            Specifies if the offset and unit cell are in cartesian or
            reduced coordinates. Reduced coordinates are with respect to
            the *old* unit cell.
        """
        # Validate inputs w.r.t. model properties
        # Note: this is affected by issue #76
        if self.pos is None:
            raise ValueError(
                "Cannot change the unit cell: model positions are not defined."
            )

        if cartesian:
            if self.uc is None:
                raise ValueError(
                    "Cannot change unit cell in cartesian coordinates: model does not have a unit cell."
                )
            # convert to reduced coordinates
            if uc is None:
                new_uc = self.uc
                uc_reduced = np.eye(self.dim)
            else:
                new_uc = np.array(uc)
                uc_reduced = la.solve(self.uc.T, new_uc.T).T
            offset_reduced = la.solve(self.uc.T, np.array(offset).T).T
        else:
            if uc is None:
                uc_reduced = np.eye(self.dim)
            else:
                uc_reduced = np.array(uc)
            if self.uc is None:
                new_uc = None
            else:
                new_uc = (self.uc.T @ uc_reduced.T).T
            offset_reduced = np.array(offset)

        # check that the reduced unit cell is compatible with the
        # current lattice
        if not np.allclose(np.round(uc_reduced), uc_reduced):
            raise ValueError(
                "The new unit cell must be compatible with the current lattice. "
                "It must be an integer combination of previous lattice vectors, "
                f"but in reduced coordinates it is:\n{uc_reduced}"
            )
        uc_reduced = np.round(uc_reduced).astype(int)
        if la.det(uc_reduced) != 1:
            raise ValueError(
                "The determinant of the unit cell in reduced coordinates must "
                f"be 1, but it is {la.det(uc_reduced)} instead."
            )

        # apply offset to positions
        new_pos = self.pos - offset_reduced

        # rotate positions
        new_pos = la.solve(uc_reduced.T, new_pos.T).T

        # rotate hopping matrices
        new_hop = {}
        for R, hop_mat in self.hop.items():
            new_R = la.solve(uc_reduced.T, R)
            assert np.allclose(np.round(new_R), new_R)
            new_R = tuple(new_R.astype(int))
            new_hop[new_R] = hop_mat

        return Model(
            **co.ChainMap(dict(uc=new_uc, pos=new_pos, hop=new_hop), self._input_kwargs)
        )

    @staticmethod
    def _async_parse(iterator, chunksize=1):
        mapping = dict()
        stopped = False
        while True:
            # get the desired key
            key = yield
            while True:
                try:
                    # key found
                    yield mapping.pop(key)
                    break
                except KeyError as e:
                    if stopped:
                        # avoid infinte loop in true KeyError
                        raise e
                    for _ in range(chunksize):
                        try:
                            # parse new data
                            newkey, newval = next(iterator)
                            mapping[newkey] = newval
                        except StopIteration:
                            stopped = True
                            break

    @staticmethod
    def _read_wsvec(iterator):
        # skip comment line
        next(iterator)
        for first_line in iterator:
            *R, o1, o2 = (int(x) for x in first_line.split())
            # in our convention, orbital indices start at 0.
            key = (o1 - 1, o2 - 1, tuple(R))
            N = int(next(iterator))
            val = [
                tuple(int(x) for x in next(iterator).split())
                for _ in range(N)
            ]
            yield key, val

    @staticmethod
    def _read_xyz(iterator):
        """Reads the content of a .xyz file"""
        # This functionality exists within pymatgen, so it might make sense
        # to use that if we anyway want pymatgen as a dependency.
        N = int(next(iterator))
        next(iterator)  # skip comment line
        wannier_centres = []
        atom_positions = []
        AtomPosition = co.namedtuple('AtomPosition', ['kind', 'pos'])
        for l in iterator:
            kind, *pos = l.split()
            pos = tuple(float(x) for x in pos)
            if kind == 'X':
                wannier_centres.append(pos)
            else:
                atom_positions.append(AtomPosition(kind=kind, pos=pos))
        assert len(wannier_centres) + len(atom_positions) == N
        return wannier_centres, atom_positions

    @staticmethod
    def _read_win(iterator):
        lines = (l.split('!')[0] for l in iterator)
        lines = (l.strip() for l in lines)
        lines = (l for l in lines if l)
        lines = (l.lower() for l in lines)

        split_token = re.compile('[ :=]+')

        mapping = {}
        for l in lines:
            if l.startswith('begin'):
                key = split_token.split(l[5:].strip(' :='), 1)[0]
                val = []
                while True:
                    l = next(lines)
                    if l.startswith('end'):
                        end_key = split_token.split(l[3:].strip(' :='), 1)[0]
                        assert end_key == key
                        break
                    else:
                        val.append(l)
                mapping[key] = val
            else:
                key, val = split_token.split(l, 1)
                mapping[key] = val

        # here we can continue parsing the individual keys as needed
        if 'unit_cell_cart' in mapping:
            uc_input = mapping['unit_cell_cart']
            # handle the case when the unit is explicitly given
            if len(uc_input) == 4:
                unit, *uc_input = uc_input
                # unit = unit[0]
            else:
                unit = 'ang'
            val = [[float(x) for x in split_token.split(line)]
                   for line in uc_input]
            val = np.array(val).reshape(3, 3)
            if unit == 'bohr':
                val *= 0.52917721092
            mapping['unit_cell_cart'] = val

        return mapping
