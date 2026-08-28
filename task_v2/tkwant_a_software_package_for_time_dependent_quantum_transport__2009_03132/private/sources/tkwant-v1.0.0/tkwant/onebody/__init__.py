# -*- coding: utf-8 -*-
# Copyright 2016-2019 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Tools for solving the one-body time-dependent Schrödinger equation."""

__all__ = []

for module in ('solvers', 'kernels', 'onebody'):
    exec('from . import {0}'.format(module))
    __all__.append(module)

available = [
    ('onebody', onebody.__all__)
]

for module, names in available:
    exec('from .{0} import {1}'.format(module, ', '.join(names)))
    __all__.extend(names)

del available, module, names  # remove cruft from namespace
