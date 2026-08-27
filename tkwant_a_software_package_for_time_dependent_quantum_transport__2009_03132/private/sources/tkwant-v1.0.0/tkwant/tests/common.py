# -*- coding: utf-8 -*-
# Copyright 2016 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Common utilities for testing"""

import numpy as np
import tinyarray as ta
import kwant


def make_square(N, lat=None, sym=kwant.builder.NoSymmetry(), norbs=1, functional=False, mat=np.eye):
    if not lat:
        lat = kwant.lattice.square(norbs=norbs)
    syst = kwant.Builder(sym)
    onsite = (lambda i, t, arg: 4 * mat(norbs)) if functional else 4 * mat(norbs)
    hop = (lambda i, j, t, arg: -1 * mat(norbs)) if functional else -1 * mat(norbs)
    syst[(lat(i, j) for i in range(N) for j in range(N))] = onsite
    syst[lat.neighbors()] = hop
    return lat, syst


def make_chain(N, lat=None, sym=kwant.builder.NoSymmetry(), norbs=1, functional=False, mat=np.eye):
    if not lat:
        lat = kwant.lattice.chain(norbs=norbs)
    syst = kwant.Builder(sym)
    onsite = (lambda i, t, arg: 2 * mat(norbs)) if functional else 2 * mat(norbs)
    hop = (lambda i, j, t, arg: -1 * mat(norbs)) if functional else -1 * mat(norbs)
    syst[(lat(i) for i in range(N))] = onsite
    syst[lat.neighbors()] = hop
    return lat, syst


def make_square_with_leads(N, norbs=1, functional=False, mat=np.eye):
    lat, syst = make_square(N, norbs=norbs, mat=mat)
    _, lead = make_square(N, lat, kwant.TranslationalSymmetry([-1, 0]),
                          norbs=norbs, functional=functional, mat=mat)
    syst.attach_lead(lead)
    syst.attach_lead(lead.reversed())
    return lat, syst


def make_chain_with_leads(N, norbs=1, functional=False, mat=np.eye):
    lat, syst = make_chain(N, norbs=norbs, mat=mat)
    _, lead = make_chain(N, lat, kwant.TranslationalSymmetry([-1]),
                         norbs=norbs, functional=functional, mat=mat)
    syst.attach_lead(lead)
    syst.attach_lead(lead.reversed())
    return lat, syst


def make_simple_lead(lat):
    syst = kwant.Builder(kwant.TranslationalSymmetry((-1, 0)))
    syst[(lat(0, j) for j in range(3))] = 4
    syst[lat.neighbors()] = -1 + 1j
    return syst


def make_complex_lead(lat):
    syst = kwant.Builder(kwant.TranslationalSymmetry((-1, 0)))
    syst[(lat(0, j) for j in range(3))] = 4
    syst[kwant.HoppingKind((0, 1), lat)] = -1
    syst[(lat(0, 0), lat(1, 0))] = -1j
    syst[(lat(0, 1), lat(1, 0))] = -1
    syst[(lat(0, 2), lat(1, 2))] = -1 + 1j
    return syst


def make_system_with_leads(lat, lead_maker):
    syst = kwant.Builder()
    syst[(lat(i, j) for i in range(3) for j in range(3))] = 4
    syst[lat.neighbors()] = -1
    syst.attach_lead(lead_maker(lat))
    syst.attach_lead(lead_maker(lat).reversed())
    return syst


def check_boundary_hamiltonian(H, cell_norbs, iface_norbs,
                               cell_hamiltonian, inter_cell_hopping):
    this_cell = ta.array([0, cell_norbs])
    this_iface = ta.array([0, iface_norbs])
    H = H.todense()
    ncells = H.shape[0] // cell_norbs
    for i in range(ncells):
        H_cell = cell_hamiltonian(i)
        assert np.allclose(H[slice(*this_cell), slice(*this_cell)], H_cell,
                           atol=1e-16, rtol=1e-16)
        # can only check forwards/backwards if we are not on the last/first cell
        if i < ncells - 1:
            V_cell = inter_cell_hopping(i)
            next_cell = this_cell + cell_norbs
            assert np.allclose(H[slice(*this_iface), slice(*next_cell)],
                               V_cell.conjugate().transpose(), atol=1e-16,
                               rtol=1e-16)
            assert np.allclose(H[slice(*next_cell), slice(*this_iface)],
                               V_cell, atol=1e-16, rtol=1e-16)
        this_cell += cell_norbs
        this_iface += cell_norbs
