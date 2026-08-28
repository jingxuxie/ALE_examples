# Copyright 2016-2019 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Utility routines."""


import subprocess
import os
import inspect
import numpy as np

__all__ = ['version', 'TkwantDeprecationWarning', 'is_type', 'is_type_array',
           'is_not_empty', 'is_zero', 'time_start', 'time_name']

# tkwant's default initial time and time argument name
time_start = 0
time_name = 'time'

package_root = os.path.dirname(os.path.realpath(__file__))
distr_root = os.path.dirname(package_root)
version_file = '_tkwant_version.py'


def get_version_from_git():
    try:
        p = subprocess.Popen(['git', 'rev-parse', '--show-toplevel'],
                             cwd=distr_root,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        return
    if p.wait() != 0:
        return
    if not os.path.samefile(p.communicate()[0].decode().rstrip('\n'), distr_root):
        # The top-level directory of the current Git repository is not the same
        # as the root directory of the tkwant distribution: do not extract the
        # version from Git.
        return

    # git describe --first-parent does not take into account tags from branches
    # that were merged-in.
    for opts in [['--first-parent'], []]:
        try:
            p = subprocess.Popen(['git', 'describe', '--long'] + opts,
                                 cwd=distr_root,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            return
        if p.wait() == 0:
            break
    else:
        return
    description = p.communicate()[0].decode().strip('v').rstrip('\n')

    release, dev, git = description.rsplit('-', 2)
    version = [release]
    labels = []
    if dev != "0":
        version.append(".dev{}".format(dev))
        labels.append(git)

    try:
        p = subprocess.Popen(['git', 'diff', '--quiet'], cwd=distr_root)
    except OSError:
        labels.append('confused')  # This should never happen.
    else:
        if p.wait() == 1:
            labels.append('dirty')

    if labels:
        version.append('+')
        version.append(".".join(labels))

    return "".join(version)


# populate the version_info dictionary with values stored in the version file
version_info = {}
with open(os.path.join(package_root, version_file), 'r') as f:
    exec(f.read(), {}, version_info)
version = version_info['version']
version_is_from_git = (version == "__use_git__")
if version_is_from_git:
    version = get_version_from_git()
    if not version:
        version = "unknown"


class TkwantDeprecationWarning(Warning):
    """Class of warnings about a deprecated feature of tkwant.

    DeprecationWarning has been made invisible by default in Python 2.7 in order
    to not confuse non-developer users with warnings that are not relevant to
    them.  In the case of tkwant, by far most users are developers, so we feel
    that a TkwantDeprecationWarning that is visible by default is useful.
    """
    pass


def ensure_isinstance(obj, typ, msg=None):
    if isinstance(obj, typ):
        return
    if msg is None:
        msg = "Expecting an instance of {}.".format(typ.__name__)
    raise TypeError(msg)

# type checking and small helper routines


def is_type(variable, generic_type, require_finite=False):
    """Return true if type(variable) matches the generic type."""
    # TODO: require finite for all types
    if generic_type == 'integer':
        return np.issubdtype(type(variable), np.integer)
    if generic_type == 'number':
        return np.issubdtype(type(variable), np.number)
    if generic_type == 'real_number':
        _type = type(variable)
        is_number = np.issubdtype(_type, np.number)
        is_complex = np.issubdtype(_type, np.complexfloating)
        if is_number and require_finite:
            is_finite = np.isfinite(variable)
            return is_number and is_finite and not is_complex
        return is_number and not is_complex
    if generic_type == 'complex':
        _type = type(variable)
        is_number = np.issubdtype(_type, np.number)
        is_complex = np.issubdtype(_type, np.complexfloating)
        return is_number and is_complex
    raise NotImplementedError('generic_type= {} not implemented'
                              .format(generic_type))


def is_type_array(array, generic_type):
    """Return true everywhere where type(array) matches the generic type"""
    array = np.array(array)
    return np.array([is_type(x, generic_type) for x in array.flatten()])


def is_zero(x, tol=1E-14):
    """Return true if |x| < tol."""
    return np.abs(x) < tol


def is_not_empty(obj):
    """Check if obj exists."""
    try:
        return obj.any() or len(obj) > 0
    except AttributeError:
        if obj:
            return True
        return False


def get_default_function_argument(func, kwarg):
    """Return the default value of a function argument.

    Parameters
    ----------
    func : callable
        Function to inspect.
    kwarg : str
        Function argument for which we like to obtain the default value.

    Returns
    -------
    default : obj
        Default argument of function `func`.
        If func(kwarg=42), the returned value would be 42.

    Notes
    -----
    A TypeError is raised, if the function `func` has no `kwarg` argument
    with a default value.
    """
    P = inspect.Parameter
    pars = inspect.signature(func).parameters  # an *ordered mapping*
    for k, v in pars.items():
        if k == kwarg and v.kind in (P.POSITIONAL_OR_KEYWORD, P.KEYWORD_ONLY):
            if v.default is not inspect._empty:
                return v.default
    try:
        func_name = func.__name__
    except AttributeError:
        func_name = '<unknown func>'   # for functools.partial and friends
    raise ValueError("Function argument {} not present in {}".
                     format(kwarg, func_name))
