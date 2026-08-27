# -*- coding: utf-8 -*-
# Copyright 2016 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""tkwant, a Python package for time-resolved quantum transport."""

import os

from ._common import version as __version__  # pragma: no flakes
from ._common import TkwantDeprecationWarning
from . import _logging as logging

__all__ = ['TkwantDeprecationWarning', 'logging']

for module in ('system', 'leads', 'onebody', 'manybody', 'mpi'):
    exec('from . import {0}'.format(module))
    __all__.append(module)


# to make stuff available in tkwant namespace
# available = [
#    ('system', [])
# ]

# for module, names in available:
#    exec('from .{0} import {1}'.format(module, ', '.join(names)))
#    __all__.extend(names)
# del available, module, names  # remove cruft from namespace


del module  # remove cruft from namespace


def test(verbose=True):
    """Run tkwant's unit tests."""
    import pytest
    return pytest.main([os.path.dirname(os.path.abspath(__file__)), '-s']
                       + (['-v'] if verbose else []))
