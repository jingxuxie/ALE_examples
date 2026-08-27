# -*- coding: utf-8 -*-
# Copyright 2019 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

"""Test module for `tkwant._common`"""

import functools
import pytest

from .._common import get_default_function_argument


def foo(a, b=42, c=None):
    pass


def bar(x, a, b=42, c=None):
    pass


class Foo():
    def __init__(self, a, b=42, c=None):
        pass


class Bar():
    def __init__(self, x, a, b=42, c=None):
        pass


FUNCTIONS = [foo, bar, Foo, Bar]
FUNCTION_NAMES = ['foo', 'bar', 'Foo', 'Bar']


@pytest.mark.parametrize('foo, function_name', zip(FUNCTIONS, FUNCTION_NAMES))
def test_get_default_function_argument_with_function(foo, function_name):

    assert get_default_function_argument(foo, 'b') == 42
    assert get_default_function_argument(foo, 'c') is None

    # check that partial binding works
    foo_bind = functools.partial(foo, a=2)

    assert get_default_function_argument(foo_bind, 'a') == 2
    assert get_default_function_argument(foo_bind, 'b') == 42
    assert get_default_function_argument(foo_bind, 'c') is None

    # check if argument has no default value
    with pytest.raises(ValueError) as exc:
        get_default_function_argument(foo, 'a')
    assert str(exc.value) == "Function argument a not present in {}"\
                             .format(function_name)

    # check if argument has not default value in the prebind version
    with pytest.raises(ValueError) as exc:
        get_default_function_argument(foo_bind, 'x')
    assert str(exc.value) == "Function argument x not present in <unknown func>"

    # check if argument is not present
    with pytest.raises(ValueError) as exc:
        get_default_function_argument(foo, 'd')
    assert str(exc.value) == "Function argument d not present in {}"\
                             .format(function_name)

    # check if argument is not present in the prebind version
    with pytest.raises(ValueError) as exc:
        get_default_function_argument(foo_bind, 'd')
    assert str(exc.value) == "Function argument d not present in <unknown func>"
