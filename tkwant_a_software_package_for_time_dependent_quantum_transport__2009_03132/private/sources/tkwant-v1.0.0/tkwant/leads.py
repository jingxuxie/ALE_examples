# -*- coding: utf-8 -*-
# Copyright 2016-2019 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Tools for dealing with time-dependent infinite, periodic leads.

Also contains tools for dealing with boundary conditions that simulate
the effect of leads when solving the time-dependent Schrödinger equation.
"""

import abc
import bisect
import functools as ft
import collections
import inspect
import cmath
from math import ceil
import numpy as np
from scipy import sparse as sp
from scipy.optimize import brentq

import kwant
import kwantspectrum
import tinyarray as ta
from . import _common, _logging


__all__ = ['add_voltage', 'SimpleBoundary', 'MonomialAbsorbingBoundary',
           'GenericAbsorbingBoundary', 'automatic_boundary',
           'AbsorbingReflectionSolver', 'AnalyzeReflection',
           'AnalyzeReflectionMonomial']


# set module logger
logger = _logging.make_logger(name=__name__)
log_func = _logging.log_func(logger)


# TODO: change this when Kwant can have further than nearest-neighbor
#       hoppings in leads
@log_func
def add_voltage(syst, lead, phase):
    r"""Add a time-dependent voltage to a lead.

    Add a lead unit cell to the ``syst`` where ``lead`` is
    attached, and couple this to ``syst`` with a time-dependent
    hopping that effectively adds a voltage to the lead.

    Parameters
    ----------
    syst : `kwant.builder.Builder`
        The central system, with its leads already attached.
        Modified on return.
    lead : int
        The number of the lead on which to apply the voltage.
    phase : callable
        Function specifying the anti-derivative of the voltage.
        Takes takes the same extra arguments as the
        Hamiltonian value functions, starting with the time.
        Returns either a scalar or a one-dimensional sequence:
        one element per orbital on a site. Must return 0
        (or a sequence of zeros) at time 0.

    Returns
    -------
    tuple
        The sites added to the system.

    Raises
    ------
    ValueError
        If the ``phase`` argument is not callable, or if sites in the
        lead interface belong to different domains

    Notes
    -----
    Formally, this function adds a single lead cell to the
    system and attaches the previous lead interface to it with
    a hopping :math:`(1 \otimes \exp[iX(t)])V`, where V is the hopping
    between lead unit cells, 1 is the unit matrix over the interface sites
    and X(t) is a square diagonal matrix over the orbitals on
    one site, specified by the ``phase`` parameter.  This
    corresponds to adding a voltage X'(t) to each site in the
    lead. In the most common case of 1 orbital per site X(t) is
    a scalar.

    This function only works if the lead was attached with ``attach_lead``,

    If any exceptions are raised in this function there are no
    guarantees that the system was not modified.
    """
    if not isinstance(syst, kwant.builder.Builder):
        raise TypeError('"syst" must be an instance of ``kwant.builder.Builder``'
                        '(not a finalized system)')

    lead_builder = syst.leads[lead].builder
    interface = syst.leads[lead].interface
    sym = lead_builder.symmetry
    interface_dom = sym.which(interface[0])
    # check for valid inputs
    if not callable(phase):
        raise ValueError('Phase function is not callable')
    # sanity check that interface sites are all in the same domain,
    # in any case, if this is not true Kwant will not be able to
    # finalise the system
    if not all(sym.which(s) == interface_dom for s in interface):
        raise ValueError('Some interface sites belong to different domains')
    # check that there are not hoppings > nearest neighbor cells
    for hopping in lead_builder.hoppings():
        if not -1 <= sym.which(hopping[1])[0] <= 1:
            msg = ('The following hopping connects non-neighboring lead '
                   'unit cells. Only nearest-cell hoppings are allowed '
                   '(consider increasing the lead period).\n{0}')
            raise ValueError(msg.format(hopping))

    # phase *from* the system *to* the lead (new cell)
    # called with a hopping and whether this is *from* the system *to*
    # the lead (new cell) or vice versa, returns a hopping value function

    # map sites to domain of the new cell
    def move(x):
        return sym.act(interface_dom + 1, sym.act(-sym.which(x), x))

    # copy over sites
    for site in lead_builder.H:
        syst[move(site)] = lead_builder[site]

    # copy over hoppings
    for (to_site, from_site), value in lead_builder.hopping_value_pairs():
        if sym.which(to_site) == sym.which(from_site):  # intra-cell hopping
            syst[move(to_site), move(from_site)] = value
        else:  # inter-cell hopping
            system_to_lead = sym.which(to_site)[0] > sym.which(from_site)[0]
            if system_to_lead:
                from_site = sym.act(interface_dom - sym.which(from_site), from_site)
                to_site = move(to_site)
            else:
                to_site = sym.act(interface_dom - sym.which(to_site), to_site)
                from_site = move(from_site)
            syst[to_site, from_site] = _make_time_dependent_hopping(phase, value, system_to_lead)

    syst.leads[lead].interface = tuple(map(move, interface))
    return tuple(map(move, lead_builder.H))


# ---------- Boundary Conditions

def _return_true(x):
    return True


class _TimeIsValid:
    # Do not allow us to evolve beyond tmax
    def __init__(self, tmax):
        self.tmax = tmax

    def __call__(self, time):
        return time < self.tmax


class EvaluatedBoundary(collections.namedtuple('_System', ['hamiltonian',
                                                           'to_slices',
                                                           'from_slices',
                                                           'solution_is_valid',
                                                           'time_is_valid'])):
    """Boundary conditions evaluated for a lead.

    Parameters
    ----------
    hamiltonian : `~scipy.sparse.coo_matrix`
        The Hamiltonian matrix of the boundary conditions evaluated over
        the lead.
    to_slices, from_slices : sequence of `tinyarray.array`
        Each array contains a pair of integers: a slice into ``hamiltonian``
        which we wish to connect *to* (or *from*) the Hamiltonian of the
        central region.
    solution_is_valid : callable
        Function that takes a 1D array of the same size as ``hamiltonian``
        (i.e the solution inside the boundary conditions), and returns
        True if there are no spurious reflections detected.
    time_is_valid : sequence of callable
        Function that takes a float (time) and returns True if the
        boundary conditions will remain valid up till this time.

    Notes
    -----
    ``to_slices`` and ``from_slices`` are used when constructing the
    Hamiltonian for the central system + boundary conditions. Usually The first
    slices will be over the first cell of the lead. Subsequent entries in
    ``from_slices`` can be used, for example, when constructing two "copies" of
    a boundary where the second copy should be affected by what happens in the
    central region, but should not itself have any back-action on the central
    region (see section C of [1] for details).

    [1]: http://arxiv.org/abs/1510.05967
    """


class BoundaryBase(metaclass=abc.ABCMeta):
    """ABC boundary conditions for the time-dependent Schrödinger equation."""

    @abc.abstractmethod
    def __call__(self, lead, params=None):
        """Generate boundary conditions for a single lead.

        These boundary condition matrices must be formatted such that
        they can be coupled to the central system Hamiltonian via
        ``lead.inter_cell_hopping`` in the first ``lead.n_cells``
        orbitals of the matrix corresponding to ``lead``.

        Parameters
        ----------
        lead : `~kwant.system.InfiniteSystem`
            The lead for which to generate boundary conditions.
        params : dict, optional
            Extra parameters for Hamiltonian value functions.

        Returns
        -------
        `_EvaluatedBoundary`
        """
        pass


class SimpleBoundary(BoundaryBase):
    """Boundary conditions consisting of N lead unit cells.

    Parameters
    ----------
    num_cells : int, optional
        The number of lead unit cells to add. Mutually exclusive with
        ``tmax``.
    tmax : float, optional
        The maximum time up to which we wish to simulate with these
        boundary conditions. Mutually exclusive with ``num_cells``
    """

    def __init__(self, num_cells=None, tmax=None):
        self.num_total_cells = self.tmax = None

        if num_cells is not None:
            if num_cells <= 0:
                raise ValueError('Number of unit cells must be positive.')
            self.num_total_cells = int(num_cells)

        if tmax is not None:
            if tmax <= 0:
                raise ValueError('Maximum time must be positive.')
            self.tmax = float(tmax + 1)  # 1 to prevent rounding problems

        if self.num_total_cells is None and self.tmax is None:
            raise TypeError('Either `num_cells` or `tmax` must be provided.')
        elif self.num_total_cells is not None and self.tmax is not None:
            raise TypeError('`num_cells` and `tmax` are mutually exclusive.')

    def __call__(self, lead, params=None):
        H_cell = lead.cell_hamiltonian(params=params, sparse=True)
        V_cell = lead.inter_cell_hopping(params=params, sparse=True)
        V_cell = _make_square_matrix(V_cell)
        cell_norbs = H_cell.shape[0]

        # twice the spectral norm of V_cell gives max velocity
        max_velocity = (2 * np.linalg.norm(V_cell.todense(), ord=2))

        tmax = self.tmax or self.num_total_cells / max_velocity
        # add 1 to prevent off-by-one error due to inter-cell hoppings
        num_cells = (self.num_total_cells
                     or int(np.ceil(self.tmax * max_velocity)) + 1)

        assert tmax is not None

        H = _make_block_tridiagonal(H_cell, V_cell,
                                    V_cell.conjugate().transpose(),
                                    num_cells)

        # With these boundary conditions there is no way to explicitly
        # check if the solution is good for a given lead_psi.
        solution_is_valid = _return_true
        time_is_valid = _TimeIsValid(tmax)

        return EvaluatedBoundary(hamiltonian=H,
                                 to_slices=[ta.array([0, cell_norbs])],
                                 from_slices=[ta.array([0, cell_norbs])],
                                 solution_is_valid=solution_is_valid,
                                 time_is_valid=time_is_valid)


class AbsorbingBoundary(SimpleBoundary):

    def __call__(self, lead, params=None):
        # get the regular boundary conditions by calling superclass
        simple_boundary = super().__call__(lead, params)

        # make diagonal matrix with entries increasing as we go to further into
        # the lead, but with entries constant over a given cell.
        bc_diags = [self._absorb(cell) for cell in range(self.num_cells)]
        bc_diags = [0] * self.num_buffer_cells + bc_diags  # add buffer cells
        cell_norbs = _get_slice(lead, lead.cell_size).start
        S = sp.kron(sp.diags(bc_diags, offsets=0), sp.eye(cell_norbs))
        H = simple_boundary.hamiltonian - 1j * S

        # With these boundary conditions there is no way to explicitly
        # check if the solution is good for a given lead_psi.
        solution_is_valid = _return_true

        # apriori there is no "max time" with absorbing boundary conditions
        time_is_valid = _return_true

        return EvaluatedBoundary(hamiltonian=H,
                                 to_slices=simple_boundary.to_slices,
                                 from_slices=simple_boundary.from_slices,
                                 solution_is_valid=solution_is_valid,
                                 time_is_valid=time_is_valid)

    @abc.abstractmethod
    def _absorb(self, cell):
        """Return the absorbing potential in the given cell."""
        pass


class MonomialAbsorbingBoundary(AbsorbingBoundary):
    """Absorbing boundary conditions consisting of N lead unit cells.

    The absorbing region has an imaginary potential applied to it.
    The magnitude of the imaginary potential grows according to
    ``n**degree`` where ``n`` is the index (starting from 0) of the
    lead cell counting from the central region.

    Parameters
    ----------
    num_cells : int
        The number of lead unit cells over which the absorbing potential
        increases.
    strength : float
        The strength of the boundary conditions. Formally
        this is the area underneath the monomial curve.
    degree : int
        The degree of the absorbing monomial.
    num_buffer_cells : int, optional
        If provided, adds this many lead cells to the start
        of the boundary conditions with no absorbing potential
        applied.
    """

    def __init__(self, num_cells, strength, degree, num_buffer_cells=0):
        if num_cells < 0:
            raise ValueError('Cannot add a negative number of absorbing cells')
        if num_buffer_cells < 0:
            raise ValueError('Cannot add a negative number of buffer cells')
        if degree < 0:
            raise ValueError('Absorbing boundary conditions cannot be given '
                             'by a monomial of negative degree.')
        super().__init__(num_cells + num_buffer_cells)
        self.num_cells = int(num_cells)
        self.strength = strength
        self.degree = int(degree)
        self.num_buffer_cells = int(num_buffer_cells)

    def _absorb(self, cell):
        n = self.degree
        return (n + 1) * self.strength * (cell**n / self.num_cells**(n + 1))


class GenericAbsorbingBoundary(AbsorbingBoundary):
    """Make an absorbing boundary from a user provided-absorbing potential.

    Parameters
    ----------
    imaginary_potential : callable
        User-provided absorbing potential.
    num_cells : int
        The number of lead unit cells over which the absorbing potential
        increases.
    num_buffer_cells : int, optional
        If provided, adds this many lead cells to the start
        of the boundary conditions with no absorbing potential applied.
    """

    def __init__(self, num_cells, imaginary_potential, num_buffer_cells=0):

        if not callable(imaginary_potential):
            raise ValueError('Absorbing potential is not callable')
        if num_cells < 0:
            raise ValueError('Cannot add a negative number of absorbing cells')
        if num_buffer_cells < 0:
            raise ValueError('Cannot add a negative number of buffer cells')

        super().__init__(num_cells + num_buffer_cells)
        self.num_cells = int(num_cells)
        self.num_buffer_cells = int(num_buffer_cells)
        self._imaginary_potential = imaginary_potential

    def _absorb(self, cell):
        return self._imaginary_potential(cell / self.num_cells) / self.num_cells


# TODO: add boundary conditions with a second "copy" that we can use to tell
#       if our solution has any spurious reflection.


# ---------- Internal functions
# TODO: move these to Cython

def _set_signature(func, params):
    """Set the signature of 'func'.

    Parameters
    ----------
    func : callable
    params: sequence of str
        Parameter names to put in the signature. These will be added as
        'POSITIONAL_ONLY' type parameters.
    """
    params = [inspect.Parameter(name, inspect.Parameter.POSITIONAL_ONLY)
              for name in params]
    func.__signature__ = inspect.Signature(params)


class _PhaseFactor:
    def __init__(self, phase):
        self.phase = phase

    def __call__(self, args):
        try:
            val = np.asarray(self.phase(*args))
            # if a scalar, `diag` will not work
            if len(val.shape) == 0:
                return cmath.exp(1j * val)
            return np.diag(np.exp(1j * val))
        except Exception as exc:
            msg = 'Error while evaluating user-supplied '\
                  'phase function "{}": '.format(self.phase.__name__)
            if exc.args:
                msg += str(exc.args[0])
            raise RuntimeError(msg) from exc


class _CallableHoppingSystemToLead:

    def __init__(self, phase_factor, old_hopping, len_hopp, mapping):

        self.phase_factor = phase_factor
        self.old_hopping = old_hopping
        self.len_hopp = len_hopp
        self.mapping = mapping

    def __call__(self, i, j, *args):
        old_hopping_args = args[:self.len_hopp]
        phase_args = tuple(map(lambda i: args[i], self.mapping))
        return np.dot(self.phase_factor(phase_args),
                      self.old_hopping(i, j, *old_hopping_args))


class _CallableHoppingLeadToSystem:

    def __init__(self, phase_factor, old_hopping, len_hopp, mapping):

        self.phase_factor = phase_factor
        self.old_hopping = old_hopping
        self.len_hopp = len_hopp
        self.mapping = mapping

    def __call__(self, i, j, *args):
        old_hopping_args = args[:self.len_hopp]
        phase_args = tuple(map(lambda i: args[i], self.mapping))
        return np.dot(self.old_hopping(i, j, *old_hopping_args),
                      self.phase_factor(phase_args).conjugate())


class _StaticHoppingSystemToLead:

    def __init__(self, phase_factor, old_hopping):

        self.phase_factor = phase_factor
        self.old_hopping = old_hopping

    def __call__(self, i, j, *args):
        return np.dot(self.phase_factor(args), self.old_hopping)


class _StaticHoppingLeadToSystem:

    def __init__(self, phase_factor, old_hopping):

        self.phase_factor = phase_factor
        self.old_hopping = old_hopping

    def __call__(self, i, j, *args):
        return np.dot(self.old_hopping, self.phase_factor(args).conjugate())


def _make_time_dependent_hopping(phase, old_hopping, system_to_lead):
    """Return a time-dependent hopping function.
    """
    phase_factor = _PhaseFactor(phase)

    phase_signature = kwant._common.get_parameters(phase)

    if callable(old_hopping):

        old_hopping_signature = kwant._common.get_parameters(old_hopping)
        # strip off the two site parameters that are always present
        hopping_signature = old_hopping_signature[:2]
        hopping_parameter_signature = old_hopping_signature[2:]
        len_hopp = len(hopping_parameter_signature)

        # we arrange the arguments of new_hoppings such, that the first len_hopp
        # arguments are directly the parameters of the old hopping function
        # and for the remaining elements, we have a mapping array,
        # that mapps the input to the phase_factor function.
        # note that the args of the new_hopping function are unique,
        # whereas arguments might be present in both, the phase_factor
        # function as well as the old_hoppings.
        new_signature = hopping_parameter_signature + phase_signature
        unique, indices, inverse = np.unique(new_signature,
                                             return_index=True, return_inverse=True)
        inv_indices2 = np.argsort(indices)
        indices2 = np.argsort(inv_indices2)

        # mapping of new_hopping args to the phase function
        mapping = indices2[inverse[-len(phase_signature):]]

        new_hopping_signature = hopping_signature + tuple(unique[inv_indices2])

        if system_to_lead:
            new_hopping = _CallableHoppingSystemToLead(phase_factor, old_hopping, len_hopp, mapping)
        else:
            new_hopping = _CallableHoppingLeadToSystem(phase_factor, old_hopping, len_hopp, mapping)
    else:

        new_hopping_signature = ('_site0_', '_site1_') + phase_signature

        if system_to_lead:
            new_hopping = _StaticHoppingSystemToLead(phase_factor, old_hopping)
        else:
            new_hopping = _StaticHoppingLeadToSystem(phase_factor, old_hopping)

    _set_signature(new_hopping, new_hopping_signature)

    return new_hopping


def _make_block_tridiagonal(D, L, U, n):
    """Make a sparse block-tridiagonal matrix.

    Use ``D`` for the diagonal, ``L`` for the lower
    diagonal, and ``U`` for the upper diagonal. All
    three matrices must be square and have the same shape.

    Parameters
    ----------
    D, L, U : `~scipy.sparse.spmatrix`
        The diagonals, lower diagonals, and upper diagonals.
    n : int
        The number of copies of ``diag`` on the diagonal.

    Returns
    -------
    `~scipy.sparse.lil_matrix`
    """
    if D.shape != L.shape or D.shape != U.shape:
        raise ValueError('Diagonals, lower diagonals and upper diagonals must '
                         ' have the same shape.')
    if D.shape[0] != D.shape[1]:
        raise ValueError('Matrices must be square.')

    sz = D.shape[0]
    M = sp.block_diag([D] * n, format='lil')
    # TODO: convert this to use COO format, for efficiency
    rows = range(0, M.shape[0], sz)
    cols = range(sz, M.shape[0], sz)
    for i, j in zip(rows, cols):
        M[i:(i + sz), j:(j + sz)] = U
        M[j:(j + sz), i:(i + sz)] = L

    return M


def _make_square_matrix(M):
    """Make a square matrix from a rectangular one.

    The rectangular matrix should have shape (n, m)
    with n > m (i.e. upright rectangular). The returned
    matrix will be padded with zeros on the right and
    have shape (n, n).
    """
    if M.shape[0] > M.shape[1]:  # must make matrices square
        n = M.shape[0]
        s = M.shape[0] - M.shape[1]
        M = sp.hstack((M, sp.coo_matrix((n, s), dtype=M.dtype)))
    elif M.shape[0] < M.shape[1]:
        raise ValueError('Matrix must have shape (n, m) with n > m')
    return M


_inf = float('inf')


def _get_slice(syst, site):
    """Return a slice from the first orbital of this site to the next."""
    assert 0 <= site < syst.graph.num_nodes
    if syst.site_ranges is None:
        raise RuntimeError('Number of orbitals not defined.\n'
                           'Declare the number of orbitals using the '
                           '`norbs` keyword argument when constructing '
                           'the site families (lattices).')
    # Calculate the index of the run that contains the site.
    # column = np.asarray(syst.site_ranges)[:, 0]
    # run_idx = np.searchsorted(column, site, 'right') - 1
    # The `inf` is needed to avoid the fenceposting problem
    run_idx = bisect.bisect(syst.site_ranges, (site, _inf)) - 1
    # Calculate the slice.
    first_site, norbs, orb_offset = syst.site_ranges[run_idx]
    orb = orb_offset + (site - first_site) * norbs
    return slice(orb, orb + norbs)

# ----------


def _is_positive(a):
    """Check if a, respectively all elements of a, are positive."""
    try:
        return a.all() > 0
    except AttributeError:
        return a > 0


def _is_iterable(obj):
    try:
        _ = (e for e in obj)
        return True
    except TypeError:
        return False


def _make_iterable(variable):
    """If a variable is present, make it iterable"""
    if not _is_iterable(variable):
        return [variable]
    return variable


def _is_inside(x, xmin=None, xmax=None):
    """Check if xmin <= x <= xmax (elementwise if x is an array)."""
    x = np.array(x)
    if xmin is not None and xmax is not None:
        assert xmin <= xmax
        return (xmin <= x) & (x <= xmax)
    if xmin is not None and xmax is None:
        return xmin <= x
    if xmin is None and xmax is not None:
        return x <= xmax
    return np.ones(x.shape, dtype=bool)


def _get_interval(intervals, x):
    """From a list of intervals, get the ones where the point x is inside."""
    return [a for a in intervals if _is_inside(x, *a)]


def _get_unique_interval(intervals, x):
    """From a list of intervals, get the unique one where point x is inside."""
    interval = _get_interval(intervals, x)
    if len(interval) == 1:
        return interval[0]
    elif len(interval) > 1:
        raise ValueError('Interval is not unique')
    return None


def _make_grid(qmin, qmax, nq, gridtype):
    """Make a lin/log grid with nq points between (qmin, qmax)."""
    if qmax < qmin:
        raise ValueError('qmax={} must be larger qmin={}.'.format(qmax, qmin))
    if nq <= 0:
        raise ValueError('number nq={} must be larger zero.'.format(nq))
    if gridtype == 'log':
        if qmax <= 0:
            raise ValueError('qmax={} must be larger zero.'.format(qmax))
        if qmin <= 0:
            raise ValueError('qmin={} must be larger zero.'.format(qmin))
        return np.logspace(np.log10(qmin), np.log10(qmax), nq)
    if gridtype == 'lin':
        return np.linspace(qmin, qmax, nq)
    raise NotImplementedError('gridtype= {} not implemented'.format(gridtype))


class _Chain_1d(kwant.system.FiniteSystem):
    """Make a finite quasi 1D kwant system from a Hamiltonian.

    Parameters
    ----------
    n : int
        number of cells of the finite lead
    H : array like, shape (n*norbs, n*norbs)
        Hamiltonian matrix.
    norbs : int, optional
        Number of orbitals. Default=1
    leads : list of `kwant.system.InfiniteSystem`, optional
        List of Kwant leads to attach on the left and right of the system.
        Number of list elements can not be larger 2.
        If list is empty, no leads are attached. Default=None


    Returns
    -------
    syst : `kwant.system.FiniteSystem`
        Kwant system for the quasi 1D chain
    """

    def __init__(self, n, H, norbs=1, leads=None):

        assert _common.is_type(n, 'integer')
        assert _common.is_type(norbs, 'integer')

        if n < 0:
            raise ValueError('number of cells n={} must be positive.'.format(n))
        if norbs < 0:
            raise ValueError('number of orbitals norbs={} must be positive.'
                             .format(norbs))
        if H.shape != (n * norbs, n * norbs):
            raise ValueError('shape of the hamiltonian matrix={} does not '
                             'match the system size.'.format(H.shape))

        self.norbs = norbs
        self.H = H

        edges = [(i, i + 1) for i in range(n - 1)]
        edges += [elem[::-1] for elem in edges]

        g = kwant.graph.Graph()
        g.add_edges(edges)
        self.graph = g.compressed()

        self.site_ranges = [(0, norbs, 0), (n, 0, n * norbs)]

        if leads is not None:
            if len(leads) == 1:
                self.lead_interfaces = [np.array([0])]
            elif len(leads) == 2:
                self.lead_interfaces = [np.array([0]), np.array([n - 1])]
            elif len(leads) > 2:
                raise ValueError('number of leads={} is bigger than 2.'
                                 .format(len(leads)))
            self.leads = leads

    def hamiltonian(self, i, j, *args, **kwargs):
        i0 = i * self.norbs
        j0 = j * self.norbs
        return np.array([[self.H[i0 + ii, j0 + jj] for jj in range(self.norbs)]
                         for ii in range(self.norbs)], dtype=self.H.dtype)


def _finite_lead_hamiltonian(lead, num_cells, imaginary_potential=None,
                             params=None):
    """Extract the Hamiltonian matrix :math:`H` for a lead set to a
    finite lengths in presence of an imaginary potential.

    Parameters
    ----------
    lead : `kwant.system.InfiniteSystem`
        Kwant lead
    num_cells : int
        number of cells of the finite lead
    imaginary_potential : callable, optional
        imaginary potential function
    params : dict, optional
        Extra parameters for Hamiltonian value functions.

    Returns
    -------
    H : scipy.sparse.coo or scipy.sparse.lil matrix
        Hamiltonian matrix, shape (num_cells*norbs, num_cells*norbs)
        where norbs is the number of orbitals of the lead

    Notes
    -----
    If `imaginary_potential` is present, the Hamiltonian matrix
    will not be hermitian.
    """

    assert _common.is_type(num_cells, 'integer')
    if num_cells < 0:
        raise ValueError('number of cells num_cells={} must be positive.'
                         .format(num_cells))
    cell_norbs = _get_slice(lead, lead.cell_size).start

    simple_boundary = SimpleBoundary(num_cells=num_cells)
    H0 = simple_boundary(lead, params).hamiltonian.transpose()
    if imaginary_potential is None:
        return H0, cell_norbs
    if not callable(imaginary_potential):
        raise ValueError('Absorbing potential is not callable')
    bc_diags = [imaginary_potential(cell / num_cells) / num_cells
                for cell in range(num_cells)]
    S = sp.kron(sp.diags(bc_diags, offsets=0), sp.eye(cell_norbs))
    return H0 - 1j * S, cell_norbs


def _reflect(syst, energy, params=None):
    """Calculate the reflection amplitude :math:`r` for an absorbing lead."""
    assert _common.is_type(energy, 'real_number')
    smatrix = kwant.smatrix(syst, energy, check_hermiticity=False,
                            params=params).submatrix(0, 0)
    return np.array([np.linalg.norm(smatrix[mode, :]) for mode
                     in range(smatrix.shape[0])])


def _modes(lead, energy, params=None):
    """Calculate the momentum and velocities of foreward propagating modes."""
    assert _common.is_type(energy, 'real_number')
    modes = lead.modes(energy, params=params)[0]
    nmodes = modes.momenta.size // 2
    return modes.momenta[nmodes:], modes.velocities[nmodes:]


class AbsorbingReflectionSolver:

    """Calculate the reflection amplitude :math:`r` for a lead
    with imaginary absorbing potential.

    Examples
    --------
    >>> num_cells = 100
    >>> def my_imaginary_potential(x):
            return 50 * x**4
    >>> reflect = AnalyzeReflection(lead, num_cells, my_imaginary_potential)
    >>> energies = numpy.linspace(0, 0.5, 101)
    >>> r = reflect(energies)


    Notes
    -------
    An instance of this class can be called like a method to calculate
    the reflection amplitude :math:`r` of all open modes at a given energy.
    The reflection amplitude is calculated by a static kwant calculation.
    """

    def __init__(self, lead, num_cells, imaginary_potential, params=None):
        """
        Parameters
        ----------
        lead : `kwant.system.InfiniteSystem`
            Kwant lead, for which the reflection should be calculated.
        num_cells : int
            number of cells for a finite lead taken into account
        imaginary_potential : callable
            absorbing potential function
        params : dict, optional
           Extra parameters for Hamiltonian value functions of ``lead``.

        """

        if not isinstance(lead, kwant.system.InfiniteSystem):
            raise TypeError('lead must be an instance of `InfiniteSystem`')

        self.lead = lead
        self.params = params

        H, cell_norbs = _finite_lead_hamiltonian(lead, num_cells,
                                                 imaginary_potential,
                                                 params=params)
        self.syst = _Chain_1d(num_cells, H, norbs=cell_norbs, leads=[lead])

    def __call__(self, energies):
        """ Calculates the reflection amplitude :math:`r` for all open modes
        at the given energies.

        Parameters
        ----------
        energies : float or list of floats shape (ne, )
            energies for which the reflection should be calculated

        Returns
        -------
        reflect : list, shape(ne, ) or numpy array
            Reflection amplitude, ordering similar to `energies`.
            For each `energy` element in `energies`, the corresponding
            `reflect` list element is a numpy array of shape (nmodes, ), where
            `reflect` the number of open modes at this energy. If `energies`
            was a float, the reflection of the the open modes are returned
            directly as a numpy array of shape (nmodes, ).
        momenta : list, shape(ne, ) or numpy array
            Momenta of the mode, ordering similar to `energies`.
            For each `energy` element in `energies`, the corresponding
            `momenta` list element is a numpy array of shape (nmodes, ),
            where nmodes is the number of open modes at this energy.
            If `energies` was a float, the momenta of the the open modes are
            returned directly as a numpy array of shape (nmodes, ).
        velocities : list, shape(ne, ) or numpy array
            Velocities of the mode, ordering similar to `energies`.
            For each `energy` element in `energies`, the corresponding
            `velocities` list element is a numpy array of shape (nmodes, ),
            where nmodes is the number of open modes at this energy.
            If `energies` was a float, the velocities of the the open modes are
            returned directly as a numpy array of shape (nmodes, ).


        Notes
        -------
        If no modes are open at a given energy, the corresponding lists are
        empty. If the energy matches exactly the band openings, the following
        error might occur: 'ValueError: Input a needs to be a square matrix.'
        """

        if _is_iterable(energies):
            reflect = [_reflect(self.syst, energy, params=self.params)
                       for energy in energies]
            momenta, velocities = zip(*[_modes(self.lead, energy,
                                               params=self.params)
                                        for energy in energies])
        else:
            reflect = _reflect(self.syst, energies, params=self.params)
            momenta, velocities = _modes(self.lead, energies,
                                         params=self.params)

        return reflect, momenta, velocities


class AnalyzeReflection:
    """ Analyze the the reflection for a lead."""

    def __init__(self, lead, num_cells, imaginary_potential,
                 spectrum=None, params=None):
        """
        Parameters
        ----------
        lead : `kwant.system.InfiniteSystem`
            Kwant lead, for which the reflection should be calculated.
        num_cells : int
            number of cells for a finite lead taken into account
        imaginary_potential : callable
            absorbing potential function
        spectrum : `BandSketching`, optional
            `kwant.physics.BandSketching` instance of the lead.
            This is mainly for performance.
            If not present, it will be calculated on the fly from `lead`.
        params : dict, optional
            Extra parameters for Hamiltonian value functions of ``lead``.

        """

        self.reflection_solver = AbsorbingReflectionSolver(lead, num_cells,
                                                           imaginary_potential,
                                                           params=params)

        if spectrum is None:
            self.spectrum = kwantspectrum.spectrum(lead, params=params)

    def __call__(self, k, band):
        """Calculates the reflection amplitude :math:`r` for a mode with
        momentum :math:`k` for a given band.

        Parameters
        ----------
        k : int or float, scalar or array, shape (n, )
            Momentum values where the reflection should be calculated.
        band : int
            band index

        Returns
        -------
        reflect : numpy array, shape(n, )
            Reflection amplitude
        energies : numpy array, shape(n, )
            Mode energy
        vel : numpy array, shape(n, )
            Mode velocity
        """

        energies = self.spectrum(k, band)
        rm, km, vm = self.reflection_solver(energies)

        # TODO: what happens if, due to numeric. inacc, rm is empty ?

        # if several modes are open at a given energy, get the mode
        # that corresponds to the band at given momentum k
        try:  # expect k to be iterable
            pos = [np.argmin(np.abs(ki - k0)) for ki, k0 in zip(km, k)]
            ref = np.array([ri[i] for ri, i in zip(rm, pos)])
            vel = np.array([vi[i] for vi, i in zip(vm, pos)])
        except TypeError:  # k is a scalar
            pos = np.argmin(np.abs(km - k))
            ref = rm[pos]
            vel = vm[pos]

        return ref, energies, vel

    def around_extremum(self, kmin, kmax, band, nq=20, dq=0.001, gridtype='log'):
        """Calculate the reflection amplitude :math:`r` within the momentum
        interval ``[kmin, kmax]`` around a local extremum of the dispersion.

        Parameters
        ----------
        kmin, kmax : float
            momentum interval ``[kmin, kmax]`` including the a single local
            dispersion minimum or maximum located at ``k0``.
        band : int
            band index
        nq : int, optional
            number of sample gridpoints between ``[kmin, k0 - dq]`` and between
            ``[k0 + dq, kmax]``.
            The total number of sample points is ``2 * nq``.
        dq : float, optional
            Offset around extrema located at momentum ``k0``.
        gridtype : string, optional
           `lin` : use a linear grid between ``[kmin, k0]`` and ``[k0, kmax]``

           `log` : use a log grid between ``[kmin, k0]`` and ``[k0, kmax]``.
                   The log-grid is choosen dense around ``k0``.

        Returns
        -------
        reflect : numpy array, shape(``2 * nq``, )
            Reflection amplitude :math:`r`
        energies : numpy array, shape(``2 * nq``, )
            Mode energies
        vel : numpy array, shape(``2 * nq``, )
            mode velocities
        k : numpy array, shape(``2 * nq``, )
            mode momenta
        e0 : float
            dispersion energy at the local minimum or maximum
        k0 : float
            momentum of the local minimum or maximum

        Notes
        -------
        The local extremum of the dispersion ``k0`` must be inside the
        interval  ``[kmin, kmax]``, such that  ``kmin <= k0 <= kmax``.
        Otherwise, a ``ValueError`` is thrown.
        """
        # get minimum/maximum position at k0
        k0, e0 = _get_extremum(kmin, kmax, band, self.spectrum)
        # calc reflection on left/right intervals: [kmin, k0-dq], [k0+dq, kmax]
        kl = k0 - _make_grid(dq, k0 - kmin, nq, gridtype)[::-1]
        kr = k0 + _make_grid(dq, kmax - k0, nq, gridtype)
        k = np.concatenate((kl, kr), axis=0)
        refl, ener, vel = self.__call__(k, band)
        return refl, ener, vel, k, e0, k0


class AnalyzeReflectionMonomial:
    """ Analyze the the reflection for a lead for the special case of a
    monomial absorbing potential.

    Notes
    -------
    The reflection amplitude is calculated with analytic expressions
    derived in [1]_.
    Good agreement with the exact numerical result (via `AnalyzeReflection`)
    can only be expected if :math:`k * l >> 1`.
    The length :math:`l` corresponds to `num_cells` and the momentum
    :math:`k` is the distance from a local extremum of the spectrum.

    .. [1] `J. Weston and X. Waintal, Phys. Rev. B 93, 134506 (2016)
       <https://arxiv.org/abs/1510.05967>`_
    """

    def __init__(self, lead, num_cells, strength, degree, params=None):
        """
        Parameters
        ----------
        lead : `kwant.system.InfiniteSystem` or `kwantspectrum.BandSketching`
            Kwant lead or `BandSketching` instance of the lead,
            for which the reflection should be calculated.
        num_cells : int
            number of cells for a finite lead taken into account
        degree : int
            order of the moniminal absorbing boundary potential.
        strength : float
            The strength of the boundary conditions. Formally
            this is the area underneath the monomial curve.
        params : dict, optional
            Extra parameters for Hamiltonian value functions of ``lead``.
            ``params`` is only considered if ``lead`` is an instance of
            `kwant.system.InfiniteSystem`.
        """
        if isinstance(lead, kwant.system.InfiniteSystem):
            self.spectrum = kwantspectrum.spectrum(lead, params=params)
        else:
            self.spectrum = lead

        if num_cells <= 0:
            raise ValueError('Number of unit cells must be positive.')

        self._reflect = ft.partial(_monomial_reflect, length_absorb=num_cells,
                                   strength=strength, degree=degree)

    def around_extremum(self, kmin, kmax, band, nq=20, dq=0.001, gridtype='log'):
        """Calculate the reflection amplitude :math:`r` within the momentum
        interval ``[kmin, kmax]`` around a local extremum of the dispersion.

        Parameters
        ----------
        kmin, kmax : float
            momentum interval ``[kmin, kmax]`` including the a single local
            dispersion minimum or maximum located at ``k0``.
        band : int
            band index
        nq : int, optional
            number of sample gridpoints between ``[kmin, k0 - dq]`` and between
            ``[k0 + dq, kmax]``.
            The total number of sample points is ``2 * nq``.
        dq : float, optional
            Offset around extrema located at momentum ``k0``.
        gridtype : string, optional
           `lin` : use a linear grid between ``[kmin, k0]`` and ``[k0, kmax]``

           `log` : use a log grid between ``[kmin, k0]`` and ``[k0, kmax]``.
                   The log-grid is choosen dense around ``k0``.

        Returns
        -------
        reflect : numpy array, shape(``2 * nq``, )
            Reflection amplitude :math:`r`
        energies : numpy array, shape(``2 * nq``, )
            Mode energies
        vel : numpy array, shape(``2 * nq``, )
            mode velocities
        k : numpy array, shape(``2 * nq``, )
            mode momenta
        e0 : float
            dispersion energy at the local minimum or maximum
        k0 : float
            momentum of the local minimum or maximum

        Notes
        -------
        The local extremum of the dispersion ``k0`` must be inside the
        interval  ``[kmin, kmax]``, such that  ``kmin <= k0 <= kmax``.
        Otherwise, a ``ValueError`` is thrown.
        """
        # get minimum/maximum position at k0
        k0, e0 = _get_extremum(kmin, kmax, band, self.spectrum)
        # calc reflection on left/right intervals: [kmin, k0-dq], [k0+dq, kmax]
        kl = k0 - _make_grid(dq, k0 - kmin, nq, gridtype)[::-1]
        kr = k0 + _make_grid(dq, kmax - k0, nq, gridtype)
        k = np.concatenate((kl, kr), axis=0)
        ener = self.spectrum(k, band)
        vel = self.spectrum(k, band, derivative_order=1)
        refl = self._reflect(np.abs(ener - e0), np.abs(k - k0))
        return refl, ener, vel, k, e0, k0

# -------
# analytical routines for reflection
# -------


def _strength_opti(e, k, length_absorb, degree):
    r""" Monominal absorbing boundary strength :math:`A` for which the absolute
    reflection amplitude :math:`r_\Sigma` is minimal.

    Returns
    -------
    strength : float
        Optimal strength `A` of the monomial absorbing potential.

    Notes
    -------
    The analytical expression can be obtained from
        d r_\Sigma / d A = 0 in Eq. (34)
        J. Weston and X. Waintal, Physical Review B 93, 134506 (2016).
    Note that the formula Eq. (34) is wrong, but we have to replace
        (n-1) -> (n-1)!
    """
    assert _is_positive(e)
    assert _is_positive(k)
    assert _is_positive(length_absorb)
    assert _is_positive(degree)
    degplus = degree + 1
    num = degree * degplus * np.math.factorial(degree - 1)
    denom = 2 * (2 * length_absorb * k) ** degplus
    return - e / k * np.log(num / denom)


def _monomial_reflect(e, k, length_absorb, strength, degree):
    """Reflection amplitude 'r' for the monomial potential.

    Returns
    -------
    refl : float
        reflection amplitude `r`, the value ranges between 0 and 1

    Notes
    -------
    The analytical expression corresponds to Eq. (34)
         J. Weston and X. Waintal, Physical Review B 93, 134506 (2016).
    Note that the formula Eq. (34) is wrong, but we have to replace
        (n-1) -> (n-1)!
    We also limit 'r' to values not larger then one.
    """
    assert _is_positive(e)
    assert _is_positive(k)
    assert _is_positive(length_absorb)
    assert _is_positive(strength)
    assert _is_positive(degree)
    nm1fac = np.math.factorial((degree - 1))
    num = degree * (degree + 1) * nm1fac
    denom = 4 * length_absorb * (2 * length_absorb * k) ** degree
    refl = np.abs(np.exp(-strength * k / e) + strength * num / (e * denom))
    return np.where(refl < 1, refl, 1)


def _low_energy_reflect(e, k, length_absorb, degree, strength):
    """Reflection amplitude 'r' for the low energy mode in monomial potential.

    Returns
    -------
    refl : float
        reflection amplitude `r`, the value ranges between 0 and 1
    """
    assert _is_positive(e)
    assert _is_positive(k)
    assert _is_positive(length_absorb)
    assert _is_positive(degree)
    assert _is_positive(strength)
    nm1fac = np.math.factorial(degree - 1)
    degplus = degree + 1
    nt = degree * degplus * nm1fac / 2
    at = strength * k / e
    denom = 2 * k * length_absorb
    refl = np.abs(np.exp(-at) + nt * at * (1 / denom)**degplus)
    return np.where(refl < 1, refl, 1)


def _monomial_absorbing_potential(strength, degree):
    """Monomial potential function used for absorbing boundaries.
    Form similar to equation (33) in:
    J. Weston and X. Waintal, Physical Review B 93, 134506 (2016).
    """
    assert _is_positive(degree)

    def pot(x, n, a):
        return (n + 1) * a * x**n
    return ft.partial(pot, a=strength, n=degree)


def _max_buffer_velocity(num_buffer_cells, tmax):
    """returns the maximal velocity such that a mode stays in buffer"""
    if num_buffer_cells < 0:
        raise ValueError('Cannot have a negative number of buffer cells.')
    if tmax <= 0:
        raise ValueError('Maximum time must be positive.')
    return 2 * num_buffer_cells / tmax  # factor 2 due to back and forth


def _optimal_split(degree):
    r"""Optimal splitting `x` in buffer/absorbing zone for the low energy modes
    Formula obtained from d r_\Sigma / d x = 0 in low energy approximation

    Definition
    ----------

        length buffer zone (`num_buffer_cells`) = x * length
        length absorbing zone (`num_cells`) = (1-x) * length
        length is total length of additional lead cells
        (`num_cells + num_buffer_cells`)

    Returns
    -------
    x : float
        optimal splitting parameter
    """
    if degree < 0:
        raise ValueError('Degree={} must be positive'.format(degree))
    return (2 + degree) / (3 + 2 * degree)

# -------
# analytical routines for reflection - end
# -------


# -------
# routines to do some band structure gymnastics
# TODO:
# rewrite spectrum more flexible to include most of the
# logic in spectrum
# if the spectrum is truncted by emin/emax, maximal curvature and velocity
# points might not exist. handle this case correctly.
# -------


def _get_extremum(kmin, kmax, band, spectrum):
    """Get the unique minima/maxima of the band at k0 that satisfies
    kmin <= k0 <= kmax.

    Returns
    -------
    k0 : float, momentum at the extremum
    e0 : float, energy at the extremum
    """
    zeros = spectrum.intersect(f=0, band=band, derivative_order=1, kmin=kmin, kmax=kmax)
    if len(zeros) != 1:  # test for existance and uniqueness
        raise ValueError('(kmin, kmax) interval must be choosen such that '
                         'exactly one extremum of the dispersion at k0 '
                         'lies within. Here k0={}.'.format(zeros))
    return zeros[0], spectrum(zeros[0], band)


def _max_curvature_point(spectrum, emin=None, emax=None):
    """Find the maximal velocity, respectively curvature of the spectrum.

    Parameters
    ----------
    emin, emax: float, optional
        if not `None`, we restrict to the zone bounded by [emin, emax].
    Returns
    -------
    g0 : float
        maximal absolute value of the curvature (`g0` >= 0) in
        a local minimum or maximum located at energy `e0`, momentum `k0`
        and band with index `band`
    """
    def energy_extrema(band):
        """Return an array with momenta, where velocity has local extrema"""
        # unconstrained case: velocity derivative is zero
        zeros = spectrum.intersect(f=0, band=band, derivative_order=1)
        # filter points with energies in [emin, emax]
        if _common.is_not_empty(zeros):
            energies = spectrum(zeros, band)
            inside = _is_inside(energies, emin, emax)
            zeros = zeros[inside]
        return zeros

    # find the largest curvature on all extremum points
    d2E_b = [0] * spectrum.nbands
    k_b = [0] * spectrum.nbands
    for band in range(spectrum.nbands):
        # get all momenta where energy is maximal
        k_extrema = energy_extrema(band)
        # now find the maximal curvature, if several minima are present
        if _common.is_not_empty(k_extrema):
            d2E = spectrum(k_extrema, band, derivative_order=2)
            max_id = np.argmax(np.abs(d2E))
            d2E_b[band] = d2E[max_id]
            k_b[band] = k_extrema[max_id]

    # find the largest curvature from all bands
    max_band = np.argmax(np.abs(d2E_b))
    gmax = d2E_b[max_band]
    if gmax == 0:
        logger.warning('could not find maximal curvature value for '
                       'spectrum within emin={}, emax={}'. format(emin, emax))
        raise RuntimeError('unable to find max curvature point of the spectrum')
    kmax = k_b[max_band]
    energy_max = spectrum(kmax, max_band)
    return kmax, energy_max, max_band, gmax


def _max_curvature(spectrum, emin=None, emax=None):
    """Find the (local) dispersion minima/maxima with the largest curvature.
    """

    k0, e0, band, g0 = _max_curvature_point(spectrum, emin=emin, emax=emax)

    kmin = 2 * spectrum.kmin
    kmax = 2 * spectrum.kmax

    # get the momentum interval with positive velocity sourrounding k0
    # and set k1 to the momentum of either the left or right interval border,
    # such that the distance to k0 is minimal
    intervals_e = spectrum.intervals(band, lower=emin, upper=emax,
                                     kmin=kmin, kmax=kmax)
    epsilon = 1E-6  # second derivative might not become exactly zero
    if np.sign(g0) > 0:
        intervals_g = spectrum.intervals(band, lower=epsilon, derivative_order=2,
                                         kmin=kmin, kmax=kmax)
    else:
        intervals_g = spectrum.intervals(band, upper=-epsilon, derivative_order=2,
                                         kmin=kmin, kmax=kmax)
    intervals = kwantspectrum.intersect_intervals(intervals_e, intervals_g)
    interval = _get_unique_interval(intervals, k0)
    q = np.min(np.abs(np.array(interval) - k0))

    logger.debug('local min/max with hightest curvature g: g={}, k={}, energy={},'
                 'band={}, neighbor extrema with smallest momentum distance at '
                 'relative momentum q={}'.format(g0, k0, e0, band, q))
    return k0, e0, band, q, g0


def _max_velocity_point(spectrum, emin=None, emax=None):
    """Find the maximal velocity of the spectrum.

    Parameters
    ----------
    emin, emax: float, optional
        if not `None`, we restrict to the zone bounded by [emin, emax].
    Returns
    -------
    kmax : float
        mometum value at maximum
    energy_max : float
        energy value at maximum
    max_band : int
        band with maximum velocity
    vmax : float
        maximum velocity
    """
    def velocity_maxima(band):
        """Return an array with momenta, where velocity has local extrema"""
        # unconstrained case: velocity derivative is zero
        zeros = spectrum.intersect(f=0, band=band, derivative_order=2)
        # if noise prevents to find E''(k) ==0, we look for E'(k) > 0 intervals
        if not _common.is_not_empty(zeros):
            v_pos = spectrum.intervals(band, lower=0, derivative_order=1)
            zeros = np.array(v_pos).flatten()
        # filter points with energies in [emin, emax]
        if _common.is_not_empty(zeros):
            energies = spectrum(zeros, band)
            inside = _is_inside(energies, emin, emax)
            zeros = zeros[inside]
        # velocity maximization with energy constrained:
        # if velocity maxima are outside the energy range
        # the band cuts at emin/emax are local extrema
        if emin is not None:
            inters = spectrum.intersect(f=emin, band=band)
            zeros = np.append(zeros, inters)
        if emax is not None:
            inters = spectrum.intersect(f=emax, band=band)
            zeros = np.append(zeros, inters)
        return zeros

    # find the largest velocity per band
    dE_b = [-np.inf] * spectrum.nbands
    k_b = [-np.inf] * spectrum.nbands
    for band in range(spectrum.nbands):
        # get all momenta where velocity is maximal
        momenta_vmax = velocity_maxima(band)
        # now find the maximal velocity, if several minima are present
        if _common.is_not_empty(momenta_vmax):
            dE = spectrum(momenta_vmax, band, derivative_order=1)
            max_id = np.argmax(dE)
            dE_b[band] = dE[max_id]
            k_b[band] = momenta_vmax[max_id]

    # find the largest velocity from all bands
    max_band = np.argmax(dE_b)
    vmax = dE_b[max_band]
    if vmax == -np.inf:
        logger.warning('could not find maximum velocity value for '
                       'spectrum within emin={}, emax={}'.format(emin, emax))
        raise RuntimeError('unable to find max velocity point of the spectrum')
    kmax = k_b[max_band]
    energy_max = spectrum(kmax, max_band)
    return kmax, energy_max, max_band, vmax


def _max_velocity(spectrum, emin=None, emax=None):
    """Find the highest velocity of the spectrum and the minimum
    distance to the sourrounding local extrema

    Returns
    -------
    k0 : float
        momentum of the maximum positive velocity point
    e0 : float
        E(k0, band) (energy at the maximum positive velocity point)
    band : int
        band index of the band with vmax
    eq : float
        eq = | E(k0) - E(k1) | (relative energy distance)
    q : float
        q = |k0 - k1| (minimum relative distance to surounding minimum/maximum)
    vmax : float
        vmax = E'(k0, band) > 0 (maximal positive velocity of the spectrum)
    """

    # get max velocity point
    k0, e0, band, vmax = _max_velocity_point(spectrum, emin=emin, emax=emax)
    kmin = 2 * spectrum.kmin
    kmax = 2 * spectrum.kmax

    # get the momentum interval with positive velocity sourrounding k0
    # and set k1 to the momentum of either the left or right interval border,
    # such that the distance to k0 is minimal
    intervals_e = spectrum.intervals(band, lower=emin, upper=emax,
                                     kmin=kmin, kmax=kmax)
    intervals_v = spectrum.intervals(band, lower=0, derivative_order=1,
                                     kmin=kmin, kmax=kmax)
    intervals = kwantspectrum.intersect_intervals(intervals_e, intervals_v)

    k_left, k_right = _get_unique_interval(intervals, k0)

    # if k0 is a velocity maxima with E''(k0)=0, we search a k1 with
    # E'(k1) = 0, such that |k0 - k1| is minimal. by construction, k1
    # corresponds either to k_left or k_right.
    # on the other hand if k0 is not a velocity maxima (E''(k0)/=0),
    # then, by construction, k0 will be either k_left or k_right.
    # we set k1 to the opposite momentum, since this is the nearest possible
    # energy extremum.
    if _common.is_zero(k0 - k_left):  # k0 = k_left < k_right, E''(k0) /= 0
        k1 = k_right
    elif _common.is_zero(k0 - k_right):  # k_left < k_right = k0, E''(k0) /= 0
        k1 = k_left
    else:  # k0 with k_left < k0 < k_right
        k1 = k_left if abs(k0 - k_left) < abs(k0 - k_right) else k_right

    # relative absolute energy and momentum of the maximal velocity point
    # from local surounding extremum
    e1 = spectrum(k1, band)
    q = np.abs(k1 - k0)
    eq = np.abs(e1 - e0)

    logger.debug('highest velocity={} at k={}, energy={}, '
                 'band={}, neighbor extrema at k={}, energy={}'
                 . format(vmax, k0, e0, band, k1, e1))

    return k0, e0, band, q, eq, vmax


def _fast_mode(spectrum, emin, emax):
    """Fast (high) energy mode of a spectrum

    Returns
    -------
    eq : float
        eq = | E(kmax) - E(k0) | (relative energy distance)
    vmax : float
        vmax = E'(kmax) > 0 (maximal positive velocity of the spectrum)
    q : float
        q = |kmax - k0| (minimum relative distance to surounding minimum/maximum)

    Notes
    -----
    k0 is the momentum of either the left or right extremum around kmax
    such that q, the relative distance, is minimal
    """
    *_, q, eq, vmax = _max_velocity(spectrum, emin, emax)
    return eq, vmax, q


def _slow_mode(spectrum, emin, emax):
    r"""Slow (low) energy mode of a spectrum

    Returns
    -------
    disp : callable
        disp = |E(k)|, with E(0) = 0 (energy dispersion parametrization)
    vel : callable
        vel = |E'(k)|, with E'(0) = 0 (velocity function parametrization)
    q : float
        maximum momentum (k) argument k \in [-q, q] of `disp` and `vel`

    Notes
    -----
    The dispersion function disp parametrizes the spectrum around the local
    extremum with the hightest curvature. The maximum momentum q
    is chosen such that disp is a strong monotonous function for k \in [0, q]
    and k \in [0, -q].
    """
    k0, e0, band, q, *_ = _max_curvature(spectrum, emin, emax)
    v0 = spectrum(k0, band, derivative_order=1)

    def disp(k):
        # in quadratic approximation E(k) = g0 * k**2
        return np.abs(spectrum(k0 + k, band) - e0)

    def vel(k):
        # in quadratic approximation v(k) = 2 * g0 * k
        return np.abs(spectrum(k0 + k, band, derivative_order=1) - v0)

    return disp, vel, q


# -------
# end of band structure analysis
# ----


def _maximal_buffer_momentum(tmax, len_buffer, vel_func, kmax):
    """Find the maximal momentum of a mode such that it stays into the buffer

    Parameters
    ----------
    tmax : int or float
        Maximal time for a tkwant simulation to run. Must be positive > 0.
    len_buffer : float
        length of the buffer zone (`num_buffer_cells`)
    vel_func : callable
        velocity function `v(k)` with k in [0, kmax]
    kmax : float
        Maximal value of the momentum argument of the velocity function

    Returns
    -------
    k : float
        maximal momentum that a mode with velocity function `v(k)` can have
        such that it stays inside the buffer. k has values between 0 and kmax.

    Notes
    -------
    mathematical description of the routine:

        vmax = 2 * len_buffer / tmax > 0 (maximal velocity of a mode
                                              such that it stays into buffer)
        we require v(k) to be monotonically increasing (for uniquness)
        and that kmax > 0, such that v(0) < v(kmax)

        - if v(0) <= vmax <= v(kmax):
            find the unique solution k in [0, kmax] such that v(k) = vmax

        - if vmax > v(kmax) (buffer zone larger then fastest mode)
            we return kmax

     modes with momenta in [0, k] stay into the buffer zone
     modes with momenta in [k, kmax] will escape buffer zone
     (and have to be captured by the absorbing zone)
    """

    # the checks should be save even if vel_func
    # has some numerical inaccuracy
    assert len_buffer > 0
    assert tmax > 0
    assert kmax > 0
    assert vel_func(0) < vel_func(kmax)

    def func(k):
        return vel_func(k) - 2 * len_buffer / tmax

    assert func(0) < 0
    if func(kmax) < 0:
        return kmax
    return brentq(func, 0, kmax)


def _reflect_slow_mode(slow_mode, tmax, strength, degree, length):
    """Estimate the reflection of the slow mode in the lead (buffer+aborb)
    in monomial approx.

    Parameters
    ----------
    slow_mode : tuple
        parametrization of the slowest, low energy mode
    tmax : int or float
        Maximal time for a tkwant simulation to run. Must be positive > 0.
    strength : float
        The strength of the boundary conditions. Formally
        this is the area underneath the monomial curve.
    degree : int
        order of the monominal absorbing boundary potential.
        Must be positive > 0.
    length : float
        total length of all additional lead cells
        (num_cells+num_buffer_cells)

    Returns
    -------
    refl : float
        reflection amplitude `r`, the value ranges between 0 and 1

    Notes
    -------
    If the routine encounters numerical problems, it returns
    a reflection coefficient of one.
    """

    x = _optimal_split(degree)
    length_buffer = x * length  # (corresponds to `num_buffer_cells`)
    length_absorb = (1 - x) * length  # (corresponds to `num_cells`)

    # Get maximal momentum `k` of slow mode such that it stays into the buffer
    energy_func, vel_func, kmax = slow_mode
    if not callable(energy_func):
        raise ValueError('Energy function is not callable')
    if not callable(vel_func):
        raise ValueError('Velocity function is not callable')
    try:
        k = _maximal_buffer_momentum(tmax, length_buffer, vel_func, kmax)
    except Exception:  # numerical accuracy can spoil the inversion
        logger.warning('k-inversion problem: {}, {}, {}'
                       .format(tmax, length_buffer, kmax))
        return 1

    # Return the reflection of the absorbing zone
    try:
        return _low_energy_reflect(energy_func(k), k, length_absorb, degree,
                                   strength)
    except Exception:
        logger.warning('low energy reflection problem: {}, {}, {}, {}'
                       .format(energy_func(k), k, length_absorb, strength))
        return 1


def _optimize_length(fast_mode, slow_mode, tmax, refl_max, strength, degree,
                     length_init, lmin=1):
    """Find the minimal possible length for an absorbing lead, such that
     `r < refl_max`, while keeping the strength fixed.

    Parameters
    ----------
    fast_mode : tuple
        parameters characterizing the fastest mode of the spectrum
    slow_mode : tuple
        parametrization of the slowest, low energy mode
    tmax : int or float
        Maximal time for a tkwant simulation to run. Must be positive > 0.
    refl_max : float
        maximal allowed reflection amplitude :math:`r`, must be in (0, 1)
        interval.
    strength : float
        The strength of the boundary conditions. Formally
        this is the area underneath the monomial curve.
    degree : int
        order of the monominal absorbing boundary potential.
        Must be positive > 0.
    length_init : float
        initial total length of all additional lead cells
        (num_cells+num_buffer_cells)
    lmin : float, optional
        minimal length to perform numerical root finding

    Returns
    -------
    length : float
        new estimate for the total length of the additional lead cells
        (`num_cells + num_buffer_cells`)
        The returned value of length in inside the inteval [lmin, length_init]
    success : bool
        `True`: new smaller length found: `length < length_init`
         such that : `r < refl_max`.
        `False`: not able to find a smaller length such that:
        `length < length_init` and `r < refl_max`.
        `r` is the total reflection amplitude of the lead
    """

    if refl_max <= 0:
        raise ValueError('Reflection coefficint={} must be positive'
                         .format(refl_max))

    assert 0 <= lmin <= length_init
    momentum, energy, _ = fast_mode
    xabs = (1 - _optimal_split(degree))

    def func(length):  # reflection criterion `r < refl_max`
        length_absorb = length * xabs
        r1 = _monomial_reflect(energy, momentum, length_absorb, strength, degree)
        r2 = _reflect_slow_mode(slow_mode, tmax, strength, degree, length)
        return max(r1, r2) - refl_max

    # try to find a smaller length
    try:
        length = brentq(func, lmin, length_init)
        success = True
    except Exception:
        length = length_init
        success = False
    return length, success


def _optimize_strength(fast_mode, refl_max, degree, length_init):
    """Find an appropriate strength of the monomial absorbing potential,
    such that such that `r < refl_max`, while keeping the length fixed.

    Parameters
    ----------
    fast_mode : tuple
        parameters characterizing the fastest mode of the spectrum
    refl_max : float
        maximal allowed reflection amplitude :math:`r`, must be in (0, 1)
        interval.
    degree : int
        order of the monominal absorbing boundary potential.
        Must be positive > 0.
    length_init : float
        initial total length of all additional lead cells
        (`num_cells + num_buffer_cells`)

    Returns
    -------
    strength : float
        The strength of the boundary conditions. Formally
        this is the area underneath the monomial curve.
        `strength` is only meaningful if `success` is `True`
    success : bool
        `True`: strength found such that: `r < refl_max`
        `False`: not able to find strength such that:
        `r < refl_max`
        `r` is the total reflection amplitude of the lead
    """

    # the total lead reflection `r` has absorption and reflection contribution.
    # a large strength lowers absorption but increases reflection and
    # vice versa. the reflection contribution (but not the absorption contrib.)
    # depends however also on the length over which the potential is smeared
    # (`num_cells`) and can be lowered if we increase the length.
    # the goal of this routine is to find a strength sufficiently large that
    # the fast mode is absorbed. we assume that the fast mode needs
    # the largest strength A. the strength should stay as small as possible
    # however to keep the reflection contribution, especially from the slow
    # modes, small, in order to choose the length small as well.

    # TODO: can we tune here ?
    # we could try to lower the strength iteratively, this
    # is just a one-shot try and error.
    if refl_max <= 0:
        raise ValueError('Reflection coefficint={} must be positive'.
                         format(refl_max))

    momentum, energy, _ = fast_mode

    length_absorb = length_init * (1 - _optimal_split(degree))
    strength = _strength_opti(energy, momentum, length_absorb, degree)
    success = _monomial_reflect(energy, momentum, length_absorb, strength,
                                degree) <= refl_max
    return strength, success


def _new_length_estimate(fast_mode, slow_mode, tmax, refl_max, degree,
                         length_init):
    """Try to find an appropriate strength/length combination for the monomial
    absorbing potential such that the new length < length_init

    Parameters
    ----------
    fast_mode : tuple
        parameters characterizing the fastest mode of the spectrum
    slow_mode : tuple
        parametrization of the slowest, low energy mode
    tmax : int or float
        Maximal time for a tkwant simulation to run. Must be positive > 0.
    refl_max : float
        maximal allowed reflection amplitude :math:`r`, must be in (0, 1)
        interval.
    degree : int
        order of the monominal absorbing boundary potential.
        Must be positive > 0.
    length_init : float
        initial total length of all additional lead cells
        (num_cells+num_buffer_cells)

    Returns
    -------
    length : float
        new estimate for the total length of the additional lead cells
        (`num_cells + num_buffer_cells`)
    strength : float
        The strength of the boundary conditions. Formally
        this is the area underneath the monomial curve.
        `strength` is only meaningful if `success` is `True`
    success : bool
        `True`: new smaller length found: `length < length_init`
        `False`: not able to find a smaller length such that:
        `length < length_init`
    """

    # use the fast mode to find a strength sufficiently large
    # keep the length fixed to the initial length `length_init`
    strength, success = _optimize_strength(fast_mode, refl_max, degree,
                                           length_init)

    # try to find a smaller length such that both fast and slow modes
    # are reflected less then allowd by `refl_max`.
    # the strength is kept constant.
    if success:
        length, success = _optimize_length(fast_mode, slow_mode, tmax,
                                           refl_max, strength, degree,
                                           length_init)
    else:
        length = length_init

    return length, strength, success


def _monomial_parameter_estimate(spectrum, tmax, refl_max, degree,
                                 emin=None, emax=None, eps=1E-4):
    """Estimate (optimal) parameters for the absorbing potential in monomial
    approximation.

    Parameters
    ----------
    spectrum : `BandSketching`
        `kwant.physics.BandSketching` instance of the lead.
    tmax : int or float
        Maximal time for a tkwant simulation to run. Must be positive > 0.
    refl_max : float
        maximal allowed reflection amplitude :math:`r`, must be in (0, 1)
        interval.
    degree : int
        order of the monominal absorbing boundary potential.
        Must be positive > 0.
    emin : float, optional
        lower energy cutoff. If set, only modes with energies above
        `emin` are considered. Defaut=None
    emax : float, optional
        upper energy cutoff. If set, only modes with energies below
        `emax` are considered. Defaut=None
    eps : float, optional
        minimal difference for length minimization step

    Returns
    -------
    num_cells : int
        number of cells for a finite lead taken into account
        `num_cells` is only meaningful if `absorbing_boundary` is `True`
    num_buffer_cells : int
        number of lead cells added to the start
        of the boundary conditions with no absorbing potential applied.
        `num_buffer_cells` is always meaningful,
        independent of `absorbing_boundary`
    strength : float
        The strength of the boundary conditions. Formally
        this is the area underneath the monomial curve.
        `strength` is only meaningful if `absorbing_boundary` is `True`
    absorbing_boundary : bool
        `True`: use absorbing boundary, optimal parameters were found
        `False`: use simple boundary, no optimal parameters were found

    Notes
    -------
    The routine returns the flag `absorbing_boundary` to tell the calling
    routine if (optimal) monomial parameters were found, in order
    to construct a monomial absorbing boundary condition.
    `absorbing_boundary = False` occurs if
    simple boundaries (only buffer cells) work better, or if the algorithm
    cannot find optimal parameters or if the algorithm fails.
    In all these casees simple boundaries serve as a save fallback,
    but maybe with a low performance.
    """
    if emin is not None:
        assert _common.is_type(emin, 'real_number')
    if emax is not None:
        assert _common.is_type(emax, 'real_number')
    if emax is not None and emin is not None:
        if emax < emin:
            raise ValueError('emax={} must be larger than emin={}.'
                             .format(emax, emin))

    # two reference points of the spectrum:
    # one with highest velocity (fast mode)
    # one with the highest curvature (slow mode)
    try:
        fast_mode = _fast_mode(spectrum, emin, emax)
        slow_mode = _slow_mode(spectrum, emin, emax)
    except Exception as error:
        # TODO: the case with emin/emax, where the highest velocity
        # resp. curvature do not follow analytically from the spectrum
        # is not yet handled properly.
        logger.warning('problem to analyse spectrum for boundary conditions: '
                       '{0}'.format(error))
        logger.info('switch to simple boundary conditions fallback')
        return 0, 0., 0, False

    _, vmax, _ = fast_mode

    assert vmax >= 0
    assert tmax >= 0
    assert eps >= 0

    len_max = vmax * tmax / 2
    length = len_max

    while True:
        length_new, strength, success = _new_length_estimate(fast_mode, slow_mode,
                                                             tmax, refl_max,
                                                             degree, length)
        logger.debug('length_new={}, strength={}, success={}'.
                     format(length_new, strength, success))
        if success and length_new <= length - eps:
            length = length_new
        else:
            break

    xsplit = _optimal_split(degree) if length < len_max else 1
    num_cells = ceil(length * (1 - xsplit))
    num_buffer_cells = ceil(length * xsplit)

    assert num_cells >= 0
    assert num_buffer_cells >= 0

    absorbing_boundary = length < len_max and num_cells > 0

    return num_cells, strength, num_buffer_cells, absorbing_boundary


@log_func
def automatic_boundary(leads, tmax, refl_max=1E-6, degree=6, emin=None,
                       emax=None, params=None):
    """
    Routine to find automatically a boundary condition such that the
    reflection amplitude :math:`r` for a lead stays below a given value.

    Parameters
    ----------
    leads : `kwant.system.InfiniteSystem` or `kwantspectrum.BandSketching`
        Kwant lead or `BandSketching` instance of the lead,
        for which the boundary condition is intended.
    tmax : int or float
        Maximal time for a tkwant simulation to run. Must be positive > 0.
    refl_max : float, optional
        maximal allowed reflection amplitude :math:`r`, must be in (0, 1)
        interval. Default=1E-7
    degree : int, optional
        order of the monominal absorbing boundary potential.
        Must be positive > 0. Default=4.
    emin : float, optional
        lower energy cutoff. If set, only modes with energies above
        `emin` are considered. Defaut=None
    emax : float, optional
        upper energy cutoff. If set, only modes with energies below
        `emax` are considered. Defaut=None
    params : dict, optional
        Extra arguments to pass to the Hamiltonian of ``leads``.
        Might only be provided if ``leads`` is an instance
        of `kwant.system.InfiniteSystem` (or a sequence thereof).
        If provided, ``params`` must include the time argument at initial time
        explicitly, if the lead Hamiltonian is explicitly time dependent.


    Returns
    -------
    boundaries : list of `MonomialAbsorbingBoundary` or `SimpleBoundary`
        List of boundary conditions. The length of ``boundaries`` is
        similar to the length of ``leads``.

    Notes
    -----
    The routine returns `MonomialAbsorbingBoundary` or `SimpleBoundary`
    conditions depending on which one is estimated to be computationally
    more efficient.

    """
    def get_boundary(i, lead):
        """Boundary condition for one lead"""
        if isinstance(lead, kwant.system.InfiniteSystem):
            logger.info('calculate lead spectrum for lead={}'.format(i))
            spectrum = kwantspectrum.spectrum(lead, params=params)
        else:  # assume that lead behaves like a spectrum
            spectrum = lead

        logger.info('estimate absorbing boundary parameters for lead={}'.format(i))
        num_cells, strength, num_buffer_cells, absorbing_boundary = \
            _monomial_parameter_estimate(spectrum, tmax, refl_max, degree,
                                         emin, emax)

        if absorbing_boundary:
            logger.info('use absorbing boundary for lead={}: num_cells = {}, '
                        'strength = {}, num_buffer_cells = {}'
                        .format(i, num_cells, strength, num_buffer_cells))
            return MonomialAbsorbingBoundary(num_cells, strength, degree,
                                             num_buffer_cells)
        logger.info('use simple boundary for lead={}'.format(i))
        return SimpleBoundary(tmax=tmax)

    logger.info('estimate optimal boundary conditions with parameters: '
                'tmax = {}, refl_max = {}, degree={}, emin={}, emax={}, '
                'params={}'.format(tmax, refl_max, degree, emin, emax, params))

    # type and consistency checks
    assert _common.is_type(tmax, 'real_number')
    assert _common.is_type(refl_max, 'real_number')
    assert _common.is_type(degree, 'real_number')
    if tmax <= 0:
        raise ValueError('Maximum time must be positive.')

    if not isinstance(leads, collections.abc.Iterable):
        leads = [leads]

    return [get_boundary(i, lead) for i, lead in enumerate(leads)]
