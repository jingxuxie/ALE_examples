# -*- coding: utf-8 -*-
# Copyright 2020 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Logging routines."""

import logging
import functools
import sys

__all__ = ['level', 'handler', 'filter', 'debug_handler', 'simple_handler',
           'make_logger', 'log_func']


def _make_handler(format=None):
    """Return a stream handler from a given format"""
    handler = logging.StreamHandler(sys.stdout)
    if format is not None:
        handler.setFormatter(format)
    return handler


def _make_logger(name, level, handler, filter=None):
    """Return a logger"""
    _logger = logging.getLogger(name)
    _logger.setLevel(level)
    _logger.addHandler(handler)
    if filter is not None:
        _logger.addFilter(filter)
    return _logger


def make_logger(name):
    """Return a logger with additional information

    Parameters
    ----------
    name : str
        The name of the logger
    info : callable
        A function returning additional information as a dict.
        Dict attributes appear as LogRecord attributes in the logger
        and can be included in the logger output with an appropriate format.

    Returns
    -------
    DelayedLogger : `logging.Logger`
        Logger instance with additional information and delayed creation.

    Notes
    -----
    This function uses the module attributes: level, filter, handler
    """
    class CustomLogger(logging.Logger):
        """Customize the logger class with additional information."""
        def _log(self, level, msg, args, exc_info=None, extra=None):
            if extra is None:
                extra = info()
            super(CustomLogger, self)._log(level, msg, args, exc_info, extra)

    class DelayedLogger():
        """An instance of this class works like the logger in python standard lib.

        This class delays the creation of the actual logger to the moment,
        when a first logging event is triggered.
        This allows to overwrite default level, handlers and filters,
        stored in this class, at runtime.
        """
        # the logger is a singleton, so we store it as class variable
        _logger = None

        def __getattribute__(self, key):
            # the first attribute access will initializes the logger
            try:
                return getattr(DelayedLogger._logger, key)
            except Exception as e:
                if DelayedLogger._logger is None:
                    logging.setLoggerClass(CustomLogger)  # add information to logger
                    DelayedLogger._logger = _make_logger(name, level, handler, filter)
                return self.__getattribute__(key)
                raise e

    from .mpi import get_rank  # importing at module level gives circular import
    info = get_rank
    assert callable(info)
    assert isinstance(name, str)
    return DelayedLogger()


def log_func(logger, funcname=''):
    r"""Return a wrapper to log function calls

    Use this wrapper as:

    @log_func(my_logger)
    def my_function():
        pass

    Parameters
    ----------
    logger : `logging.Logger`
            Logger instance
    funcname : str, optional
        Name of the function that is decorated that will apper in the log.

    Returns
    -------
    decorate : callable
        A wrapper to log function call and return.
    """
    def decorate(func):
        logname = funcname if funcname else func.__name__
        startmsg = 'start {}'.format(logname)
        endmsg = '{} finished'.format(logname)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(startmsg)
            result = func(*args, **kwargs)
            logger.debug(endmsg)
            return result
        return wrapper
    return decorate


# two predefined handlers for tkwant

"""logging handler with format: level:module-name:line-number:MPI-rank: message"""
_format = logging.Formatter('%(levelname)s:%(name)s:%(lineno)d:rank=%(rank)s: %(message)s')
debug_handler = _make_handler(_format)

"""logging handler with format: message"""
simple_handler = _make_handler()

# tkwant's default logging settings
level = logging.WARNING
handler = logging.NullHandler()  # suppress logging
filter = None
