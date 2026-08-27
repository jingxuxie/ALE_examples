# -*- coding: utf-8 -*-
# Copyright 2016-2020 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Tools for extracting time-dependent parts of Kwant systems."""

from collections import namedtuple
import numpy as np
import inspect
import warnings

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import scipy.sparse as sps

from .import _common


__all__ = ['hamiltonian_with_boundaries', 'add_time_to_params',
           'is_time_dependent_function', 'orb_range', 'EvaluatedSystem']


def add_time_to_params(params, time_name, time, check_numeric_type=False):
    """Add a ``time_name: time`` key-value pair to a ``params`` dict.

    Parameters
    ----------
    params : dict or None
        Input dict. Can be empty or None. ``params`` must
        not contain the ``time_name`` key - this will raise a `KeyError`.
    time_name : obj
        A dict key to refer to the "time".
    time : obj
        The actual value of "time".
    check_numeric_type : bool, optional
        If true, check if the `time` argument is a finite real number.
        By default, no check is performed.

    Returns
    -------
    tparams : dict
        A copy of the input dict ``params`` that contains an additional
        ``time_name: time`` key-value pair.
    """
    if check_numeric_type:
        if not _common.is_type(time, 'real_number', require_finite=True):
            raise TypeError('time must be a finite real number')

    if params is None:
        tparams = {}
    else:
        if time_name in params:
            raise KeyError("'params' must not contain {}".format(time_name))
        tparams = params.copy()
    tparams[time_name] = time
    return tparams


def is_time_dependent_function(obj, time_name):
    """Return `True` if `obj` is callable and has a time argument"""
    return callable(obj) and time_name in str(inspect.signature(obj))


class EvaluatedSystem(namedtuple('_EvaluatedSystem',
                                 ['hamiltonian', 'boundary_slices',
                                  'solution_validators', 'time_validators'])):

    """Hamiltonian matrix of central system + boundary conditions.

    Parameters
    ----------
    hamiltonian : `~scipy.sparse.coo_matrix`
        The Hamiltonian matrix of the central system + boundary conditions.
    boundary_slices : sequence of `slice`
        Slices into ``hamiltonian`` that project onto the boundary conditions.
    solution_validators : sequence of callable
        One callable per boundary condition. Each callable takes a single
        argument, an array representing a solution *inside the boundary
        conditions*, and returns True if the solution is valid, and False
        otherwise.
    time_validators : sequence of callable
        One callable per boundary condition. Each callable has signature
        ``(next_time)`` and return True if the given boundary condition
        can be used up to the time ``next_time``, otherwise returns False.
    """

    def solution_is_valid(self, solution):
        return all(is_valid(solution[boundary]) for is_valid, boundary
                   in zip(self.solution_validators, self.boundary_slices))

    def time_is_valid(self, time):
        return all(is_valid(time) for is_valid in self.time_validators)


def hamiltonian_with_boundaries(syst, boundaries, params):
    r"""Generate the Hamiltonian with boundary conditions attached.

    Only generate the time-independent part of the Hamiltonian.
    The boundary conditions are represented by matrices :math:`h_n`
    (one per lead) that will form a direct sum with the Hamiltonian
    of the central system, :math:`H_S`:

    .. math:: H_{tot} = H_S \oplus h_0 \oplus h_1 \oplus \cdots

    In addition, coupling terms given by the lead inter-cell
    hoppings will be added between the added boundary conditions
    and the corresponding lead interface in the central system
    Hamiltonian.

    Parameters
    ----------
    syst : `~kwant.system.FiniteSystem`
        System with leads attached.
    boundaries : sequence of `~tkwant.leads.BoundaryBase`
        The boundary conditions to attach; one per lead.
    params : dict, optional
        Extra arguments to pass to the Hamiltonian of ``syst`` at the
        initial time. Must include the time argument explicitly if
        Hamiltonian is time dependent.

    Returns
    -------
    `EvaluatedSystem`
        The Hamiltonian of the central system, evaluated at t=0,
        with boundary conditions attached, and accompanying metadata.
    """

    if not len(syst.leads) == len(boundaries):
        raise ValueError('Number of leads= {} does not match '
                         'the number of boundaries provided= {}'
                         .format(len(syst.leads), len(boundaries)))

    # generate time-independent Hamiltonian and boundary condition
    # matrices and glue them together
    boundaries = [bc(lead, params) for lead, bc in zip(syst.leads, boundaries)]
    h_0 = syst.hamiltonian_submatrix(params=params, sparse=True)
    h_tot = sps.block_diag([h_0] + [bdy.hamiltonian for bdy in boundaries],
                           format='lil')

    boundary_slices = []

    # couple central system to boundary conditions and vice versa
    orb_offset = h_0.shape[0]
    for lead, lead_iface, boundary in zip(syst.leads, syst.lead_interfaces,
                                          boundaries):
        V = lead.inter_cell_hopping(params=params)
        # slices over lead interface orbitals within the lead
        num_iface_sites = lead.graph.num_nodes - lead.cell_size
        V_slices = [slice(*orb_range(lead, s)) for s in range(num_iface_sites)]
        # slices going *to* and *from* the boundary conditions/central system
        to_slices = [slice(*(s + orb_offset)) for s in boundary.to_slices]
        from_slices = [slice(*(s + orb_offset)) for s in boundary.from_slices]

        # iterate through all sites in the interface -- they have to
        # be treated separately, as interface sites in `syst` are not
        # necessarily grouped consecutively.
        for syst_site, V_slice in zip(lead_iface, V_slices):
            syst_slice = slice(*orb_range(syst, syst_site))
            # coupled *to* system, *from* boundary conditions
            for to_slice in to_slices:
                h_tot[syst_slice, to_slice] =\
                    V[:, V_slice].conjugate().transpose()
            # couple *from* system, *to* boundary conditions
            for from_slice in from_slices:
                h_tot[from_slice, syst_slice] = V[:, V_slice]
                pass

        # remember which orbitals correspond to this boundary condition
        boundary_slices.append(slice(orb_offset,
                                     orb_offset + boundary.hamiltonian.shape[0]))
        # now point to the start of the next boundary condition block
        orb_offset += boundary.hamiltonian.shape[0]

    solution_is_valid = [bdy.solution_is_valid for bdy in boundaries]
    time_is_valid = [bdy.time_is_valid for bdy in boundaries]

    return EvaluatedSystem(h_tot, boundary_slices,
                           solution_is_valid, time_is_valid)


def orb_range(syst, site):
    """Return the first orbital of this and the next site.

    Parameters
    ----------
    syst : `~kwant.system.System`
    site : int

    Returns
    -------
    pair of integers
    """
    assert 0 <= site < syst.graph.num_nodes
    if syst.site_ranges is None:
        raise RuntimeError('Number of orbitals not defined.\n'
                           'Declare the number of orbitals using the `norbs` '
                           'keyword argument when constructing site families')
    # Calculate the index of the run that contains the site.
    column = np.asarray(syst.site_ranges)[:, 0]
    run_idx = np.searchsorted(column, site, 'right') - 1
    # calculate the slice
    first_site, norbs, orb_offset = syst.site_ranges[run_idx]
    orb = orb_offset + (site - first_site) * norbs
    return orb, orb + norbs
