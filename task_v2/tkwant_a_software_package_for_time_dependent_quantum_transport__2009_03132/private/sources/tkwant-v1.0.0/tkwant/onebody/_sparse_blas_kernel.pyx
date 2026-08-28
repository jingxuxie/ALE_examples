# -*- coding: utf-8 -*-
# cython: embedsignature=True
#
# Copyright 2016, 2017 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

from libc.string cimport memset
import numpy as np

from ..linalg import blas_sparse
from ..linalg cimport blas_sparse as sb
from ..linalg cimport blas as db
from .kernels cimport CKernel

cdef complex complex_one = 1, complex_minus_i = -1j, complex_zero = 0,


cdef class SparseBlas(CKernel):
    """Evaluate the RHS of the Schrödinger equation using sparse blas.

    Only available if tkwant has been built against a sparse BLAS library.

    Parameters
    ----------
    H0 : `scipy.sparse.base`
        Hamiltonian at ``t=0`` (including any boundary conditions).
    W : callable
        Time-dependent part of the Hamiltonian. Typically the object returned
        by `tkwant.system.extract_perturbation`.
    psi_st : `~numpy.ndarray`, optional
        The wavefunction of the initial eigenstate defined over the central
        system (if starting in an initial eigenstate).

    Attributes
    ----------
    H0 : int
        Handle for a matrix inside the sparse blas library. The Hamiltonian
        at ``t=0``.
    W : callable
        Time-dependent part of the Hamiltonian. Typically the object returned
        by `tkwant.system.extract_perturbation`.
    psi_st : array of complex or `None`
        The wavefunction of the initial eigenstate defined over the central
        system (if starting in an initial eigenstate).
    size : int
        The size of the time-independent part of the Hamiltonian. This
        also sets the size of the solution vector.
    """

    cdef sb.blas_sparse_matrix H0
    cdef object W
    cdef object args
    cdef complex[:] psi_st, temp
    cdef int center_size

    def __init__(self, H0, W, args, complex[:] psi_st=None):
        pass

    def __cinit__(self, H0, W, args, complex[:] psi_st=None):
        # `self.c_self` has the same lifetime as `self`; don't increment refcount
        self.c_self = <void*> self
        self.c_rhs = SparseBlas._rhs
        self.size = H0.shape[0]
        self.nevals = 0
        self.psi_st = psi_st
        self.W = W
        self.args = args
        if W is not None:
            self.center_size = self.W.size
        else:
            self.center_size = self.size

        H0 = H0.tocoo()

        # create temporary array storage
        self.temp = np.empty((self.center_size,), dtype=complex)

        # create sparse blas matrix handle from Scipy sparse matrix
        cdef int err = 0
        cdef complex[::1] data = H0.data
        cdef int[::1] cols = H0.col, rows = H0.row
        self.H0 = sb.BLAS_zuscr_begin(H0.shape[0], H0.shape[1])
        if self.H0 == sb.blas_invalid_handle:
            raise RuntimeError('Error initializing sparse matrix.')
        # this copies the data, so there is no need to incref H0
        err = sb.BLAS_zuscr_insert_entries(self.H0, H0.nnz,
                                           <const void*>&data[0],
                                           <const int*>&rows[0],
                                           <const int*>&cols[0])
        if err:
            raise RuntimeError('Error inserting entries into sparse matrix.')

        err = sb.BLAS_zuscr_end(self.H0)
        if err:
            raise RuntimeError('Error when finalizing sparse matrix.')

    def __dealloc__(self):
        if sb.BLAS_usds(self.H0):
            raise RuntimeError('Error destroying sparse matrix')

    def __init__(self, H0, W, args, complex[:] psi_st=None):
        # taken care of by __cinit__
        pass

    def set_args(self, args):
        self.args = args

    # TODO: make this more efficient -- fewer copies and temp storage
    # Actually evaluate the RHS. This is implemented as a cdef static method so
    # that the signature conforms to that expected by the C-level Solver API.
    @staticmethod
    cdef void _rhs(const void *_self, const complex *psi, complex *dpsidt,
                   double time) except *:
        cdef SparseBlas self = <SparseBlas>_self
        memset(<void*>dpsidt, 0, self.size * sizeof(complex))
        ### H0 @ psi -> dpsidt
        sb.BLAS_zusmv(sb.blas_no_trans, <const void*>&complex_one,
                      self.H0, <const void*>psi, 1, <void*>dpsidt, 1)
        ### W(t) @ temp + dpsidt -> dpsidt
        cdef complex *temp = psi
        if self.psi_st is not None:
            # we need to act on `temp = psi + psi_st`
            temp = &self.temp[0]
            # we only need construct vectors over the *central* system
            db.cblas_zcopy(self.center_size, <const void*>psi, 1,
                           temp, 1)
            db.cblas_zaxpy(self.center_size, <const void*>&complex_one,
                           <const void*>&self.psi_st[0], 1,
                           temp, 1)
        # finally act with the time-depedent part
        try:
            self.W.apply(time, <complex[:self.center_size]>temp,
                   out=<complex[:self.center_size]>dpsidt)
        except Exception as exept:
            if self.W is None:
                pass
            else:
                raise exept

        ### dpsidt = -1j * dpsidt
        db.cblas_zscal(self.size, <const void*>&complex_minus_i, <void*>dpsidt, 1)
