# -*- coding: utf-8 -*-
# Copyright 2016, 2017 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

import pytest
import numpy as np
import itertools as it
import functools
import scipy.sparse as sp
import tinyarray as ta
from numpy.testing import assert_array_almost_equal, assert_almost_equal
import kwant

from .. import kernels
from ... import _common

no_sparse_blas = pytest.mark.skipif(not hasattr(kernels, 'SparseBlas'),
                                    reason='No sparse BLAS available.')


def random_vector(N):
    return np.random.rand(N) + 1j * np.random.rand(N)


@pytest.mark.parametrize(('kernel_type',), [
    (kernels.Scipy,),
    (kernels.Simple,),
    pytest.param(getattr(kernels, 'SparseBlas', None), marks=no_sparse_blas)
])
def test_kernel(kernel_type):
    N = 1000

    H_simple = sp.eye(N, dtype=complex, format='csr')
    H_rand = sp.rand(N, N, format='csr') + 1j * sp.rand(N, N, format='csr')

    class W_func:
        def __init__(self, size, w):
            self.size = size
            self.w = w

        def apply(self, time, psi, out=None):
            result = self.w.dot(psi)
            if out is not None:
                out = np.asarray(out)
                out[:] += result
            else:
                return result

    for psi_st in (None, np.zeros((N,), dtype=complex), random_vector(N)):
        for H, W in it.product((H_simple, H_rand), repeat=2):

            w_func = W_func(N, W)

            psi = random_vector(N)
            nonstatic = psi if psi_st is None else psi + psi_st
            should_be = -1j * (H.dot(psi) + W.dot(nonstatic))

            py_kern = kernel_type(H, w_func, (), psi_st=psi_st)
            c_kern = kernels.extract_c_kernel(py_kern)
            for kern in (py_kern, c_kern):
                dpsidt = random_vector(N)  # this will be overwritten anyway
                nevals = kern.nevals
                kern.rhs(psi, dpsidt, 0)
                assert kern.nevals == nevals + 1
                assert np.allclose(should_be, dpsidt)

            # now test with psi_st smaller than the total size; this will be
            # the case when we have a system with added boundary conditions.

            central_norbs = N // 2
            W_part = W.tolil()[:central_norbs, :central_norbs].tocsr()
            if psi_st is not None:
                psi_st_part = psi_st[:central_norbs]
            else:
                psi_st_part = None

            w_func = W_func(central_norbs, W_part)

            psi = random_vector(N)
            central_psi = psi[:central_norbs]
            should_be = H.dot(psi)
            nonstatic = (central_psi if psi_st is None else
                         central_psi + psi_st_part)
            should_be[:central_norbs] += W_part.dot(nonstatic)
            should_be *= -1j

            py_kern = kernel_type(H, w_func, (), psi_st=psi_st_part)
            c_kern = kernels.extract_c_kernel(py_kern)
            for kern in (py_kern, c_kern):
                dpsidt = random_vector(N)  # this will be overwritten anyway
                kern.rhs(psi, dpsidt, 0)
                assert np.allclose(should_be, dpsidt)


def test_perturbation_extractor():

    def td_hopping(i, j, time):
        ab = ta.array(sorted((i.tag, j.tag)))
        return -1 + time * kwant.digest.uniform(ab)

    lat = kwant.lattice.chain(norbs=1)
    N = 4

    syst = kwant.Builder()
    syst[(lat(i) for i in range(N))] = 1
    syst[lat.neighbors()] = td_hopping

    W = kernels.PerturbationExtractor(syst.finalized(), time_name='time', time_start=0)
    time = 3

    assert W.size == N
    assert isinstance(W.size, int)

    assert W.nnz == 6
    assert isinstance(W.nnz, int)

    wdat = W.data(time)
    assert len(wdat) == W.nnz
    assert isinstance(wdat, np.ndarray)
    assert _common.is_type_array(wdat, 'complex').all()

    row_col = W.row_col()
    assert len(row_col) == 2
    assert len(row_col[0]) == W.nnz
    assert len(row_col[1]) == W.nnz
    assert isinstance(row_col, tuple)
    assert _common.is_type_array(row_col, 'integer').all()

    empty = W.empty()
    assert empty.shape == (N, N)
    assert isinstance(empty, sp.coo_matrix)

    wt = W.evaluate(time)
    assert wt.shape == (N, N)
    assert isinstance(wt, sp.coo_matrix)
    assert np.all(wt.data == wdat)

    ket = np.random.rand(N) + 1j * np.random.rand(N)
    out = W.apply(time, ket)
    assert isinstance(out, np.ndarray)
    assert len(out) == N
    assert _common.is_type_array(out, 'complex').all()

    W = kernels.PerturbationInterpolator(syst.finalized(), time_name='time', time_start=0)

    assert W.size == N
    assert isinstance(W.size, int)

    assert W.nnz == 6
    assert isinstance(W.nnz, int)

    wt = W.evaluate(time)
    assert wt.shape == (N, N)
    assert isinstance(wt, sp.coo_matrix)
    assert np.all(wt.data == wdat)

    ket = np.random.rand(N) + 1j * np.random.rand(N)
    out = W.apply(time, ket)
    assert isinstance(out, np.ndarray)
    assert len(out) == N
    assert _common.is_type_array(out, 'complex').all()


def test_extract_perturbation():

    perturb_types = [kernels.PerturbationExtractor,
                     kernels.PerturbationInterpolator,
                     functools.partial(kernels.PerturbationInterpolator, dt=0)]

    def inner_test(fsyst, N):
        for i, perturb in enumerate(perturb_types):
            W = perturb(fsyst, time_name='time', time_start=0)
            H0 = fsyst.hamiltonian_submatrix(params={'time': 0})
            H1 = fsyst.hamiltonian_submatrix(params={'time': 1})
            ket = np.random.rand(N) + 1j * np.random.rand(N)
            # calulate W(t)
            # check return and in-place modification
            if i == 1:  # numerical tolerance for interpolated W(t)
                assert_array_almost_equal(W.evaluate(1) - (H1 - H0), 0)
            else:
                assert np.all(W.evaluate(1) == (H1 - H0))

            wmat = W.evaluate(1)  # get matrix shape
            for i in range(len(wmat.data)):
                wmat.data[i] = 0
            W.evaluate(1, wmat)    # in-place
            if i == 1:  # numerical tolerance for interpolated W(t)
                assert_array_almost_equal(wmat - (H1 - H0), 0)
            else:
                assert np.all(wmat == (H1 - H0))
            # check with wrong size for in-place modification
            pytest.raises(AssertionError, W.evaluate, 1, sp.coo_matrix((N - 1, N - 1), dtype=np.complex))
            pytest.raises(AssertionError, W.evaluate, 1, sp.coo_matrix((N + 1, N + 1), dtype=np.complex))
            # data array attribute of coo matrix has wrong size
            pytest.raises(AssertionError, W.evaluate, 1, sp.coo_matrix((N, N), dtype=np.complex))

            assert isinstance(W.evaluate(1), sp.coo_matrix)

            # calulate W(t) @ ket
            # calculations not done in same order, only check if close
            # check return and in-place modification
            assert isinstance(W.apply(1, ket), np.ndarray)
            assert np.allclose(W.apply(1, ket), np.dot(H1 - H0, ket))  # return
            out = np.zeros(N, dtype=np.complex)
            W.apply(1, ket, out)  # in-place
            assert np.allclose(out, np.dot(H1 - H0, ket))
            # check with wrong size for in-place modification
            pytest.raises(AssertionError, W.apply, 1, np.zeros((N - 1), dtype=np.complex))
            pytest.raises(AssertionError, W.apply, 1, np.zeros((N + 1), dtype=np.complex))

    def td_onsite(i, time):
        return 2 + time * kwant.digest.uniform(i.tag)

    def td_hopping(i, j, time):
        ab = ta.array(sorted((i.tag, j.tag)))
        return -1 + time * kwant.digest.uniform(ab)

    lat = kwant.lattice.chain(norbs=1)
    N = 4

    # test whole system time-dependent
    syst = kwant.Builder()
    syst[(lat(i) for i in range(N))] = td_onsite
    syst[lat.neighbors()] = td_hopping
    inner_test(syst.finalized(), N)
    # check that error is raised if norbs not given
    lat.norbs = None
    for perturb in perturb_types:
        pytest.raises(RuntimeError, perturb,
                      syst.finalized(), time_name='time', time_start=0)
    lat.norbs = 1

    # test only a partial amount time-dependent
    syst = kwant.Builder()
    syst[(lat(i) for i in range(N))] = td_onsite
    syst[(lat(i) for i in range(0, N, 2))] = 1.
    syst[lat.neighbors()] = -1
    inner_test(syst.finalized(), N)

    # test >1 orbital per site
    sigma_0 = np.eye(2)
    sigma_y = np.array([[0, -1j], [1j, 0]])

    def td_onsite2(i, time):
        U = kwant.digest.uniform(i.tag)
        return 2 + time * U * sigma_y

    def td_hopping2(i, j, time):
        U = kwant.digest.uniform(ta.array(sorted((i.tag, j.tag))))
        return -1 + time * U * sigma_0

    def td_interhopping(i, j, time):
        # *from* 2 orbital lattice *to* 1 orbital lattice
        U = kwant.digest.uniform(ta.array(sorted((i.tag, j.tag))))
        return 1j * time * U * np.array([[1, 1]])

    lat2 = kwant.lattice.chain(name='b', norbs=2)

    syst = kwant.Builder()
    syst[(lat(i) for i in range(N))] = td_onsite
    syst[(lat2(i) for i in range(N))] = td_onsite2
    syst[lat.neighbors()] = td_hopping
    syst[lat2.neighbors()] = td_hopping2
    syst[kwant.builder.HoppingKind((0,), lat, lat2)] = td_interhopping
    inner_test(syst.finalized(), 2 * N + N)


def test_perturbation_interpolation():

    def td_onsite(i, time):
        return 2 + np.sin(time * 0.1) * kwant.digest.uniform(i.tag)

    def td_hopping(i, j, time):
        ab = ta.array(sorted((i.tag, j.tag)))
        return -1 + np.sin(time * 0.13) * kwant.digest.uniform(ab)

    def td_onsite2(i, time):
        U = kwant.digest.uniform(i.tag)
        return 2 + np.cos(time * 0.12) * U * sigma_y

    def td_hopping2(i, j, time):
        U = kwant.digest.uniform(ta.array(sorted((i.tag, j.tag))))
        return -1 + np.cos(time * 0.15) * U * sigma_0

    def td_interhopping(i, j, time):
        # *from* 2 orbital lattice *to* 1 orbital lattice
        U = kwant.digest.uniform(ta.array(sorted((i.tag, j.tag))))
        return 1j * np.sin(time * 0.05) * U * np.array([[1, 1]])

    # test >1 orbital per site
    sigma_0 = np.eye(2)
    sigma_y = np.array([[0, -1j], [1j, 0]])

    N = 4
    lat = kwant.lattice.chain(norbs=1)
    lat2 = kwant.lattice.chain(name='b', norbs=2)

    syst = kwant.Builder()
    syst[(lat(i) for i in range(N))] = td_onsite
    syst[(lat2(i) for i in range(N))] = td_onsite2
    syst[lat.neighbors()] = td_hopping
    syst[lat2.neighbors()] = td_hopping2
    syst[kwant.builder.HoppingKind((0,), lat, lat2)] = td_interhopping

    fsyst = syst.finalized()

    dt = 2.0

    w = kernels.PerturbationExtractor(fsyst, time_name='time', time_start=0)
    wi = kernels.PerturbationInterpolator(fsyst, time_name='time', time_start=0, dt=dt)

    for time in [0.4, 0.5, 0.7, 1, 1.6, 2, 2.1, 8.5, 19.8]:
        time *= dt
        wt = w.evaluate(time)
        wti = wi.evaluate(time)
        assert_almost_equal(np.max(np.abs(wt - wti)), 0, decimal=5)
