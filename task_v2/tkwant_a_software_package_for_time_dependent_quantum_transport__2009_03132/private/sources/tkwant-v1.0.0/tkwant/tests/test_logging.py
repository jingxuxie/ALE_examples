# -*- coding: utf-8 -*-
# Copyright 2020 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

"""Test module for `tkwant._logging`"""

import logging

from .. import _logging


def test_logging_level():
    assert _logging.level == logging.WARNING


def test_logging_handler():
    assert isinstance(_logging.handler, logging.Handler)
    assert isinstance(_logging.debug_handler, logging.Handler)
    assert isinstance(_logging.simple_handler, logging.Handler)


def test_logging_filter():
    assert _logging.filter is None


def test_logger(caplog):

    # make a logger and test that it is working if we use a predefined handler
    logger = _logging.make_logger(name=__name__)
    _logging.handler = _logging.simple_handler
    # no log events for info
    logger.info('this is a logger info')
    assert len(caplog.text) == 0
    # log event for warning (default level)
    logger.warning('this is a logger warning')
    assert "this is a logger warning" in caplog.text

    # make a logger and test that that we can change the log level
    logger = _logging.make_logger(name=__name__)
    _logging.handler = _logging.simple_handler
    _logging.level = logging.INFO
    # an event must be logged now at log-level info
    logger.info('this is a logger info')
    assert "this is a logger info" in caplog.text

    # we could do the same tests also for the handler and the filter
    # but the caplog fixture catches the logging events even when the handler
    # is the nullhandler or the messages are filtered.
