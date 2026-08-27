# -*- coding: utf-8 -*-

# library-specific init
IF SPARSELIB == "rsb":
    cdef extern from "rsb.h":
        ctypedef signed int rsb_err_t;
        cdef struct rsb_initopts:
            pass
        cdef rsb_err_t rsb_lib_init(rsb_initopts *iop)
    # initialize librsb with no explicit options
    if rsb_lib_init(NULL) != 0:
        raise RuntimeError('Failed to initialize librsb')
