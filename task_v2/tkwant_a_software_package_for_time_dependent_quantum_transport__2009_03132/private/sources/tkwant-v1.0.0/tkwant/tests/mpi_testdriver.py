# -*- coding: utf-8 -*-
# Copyright 2016-2019 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Tools for testing parallel code."""

import os
import inspect
import subprocess

__all__ = ["wrap"]


def _format_path(func):
    """Return a working path and module"""
    file = inspect.getfile(func)
    path = os.path.abspath(file)
    module = func.__module__

    for i in range(module.count(".")):
        path = os.path.split(path)[0]

    return path, module


def wrap(num_processes=1):
    """Return a decorator to run function with mpirun.
    Function must not take argument.

    num_processes: int, numer of MPI core
    parents: int, number of parent to include in working directory
    """

    def wrapper(func):
        path, module = _format_path(func)
        command = ["mpirun", "-n", str(num_processes), "-wdir", path, "python3", "-c",
                   "import {0} as module; module.{1}.original()"
                   .format(module, func.__name__)]

        def new_func():
            subprocess.run(command, check=True)

        new_func.original = func

        return new_func

    return wrapper
