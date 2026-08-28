# -*- coding: utf-8 -*-
#
# cython: embedsignature=True
#
# Copyright 2016, 2017 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.


cdef class Kernel:
    cdef public int size, nevals


ctypedef void (*rhs_t)(const void *self, const complex *psi_bar, complex *dpsidt,
                       double time) except *


cdef class CKernel(Kernel):
    cdef void *c_self
    cdef rhs_t c_rhs
