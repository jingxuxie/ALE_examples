#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""Functionality for reading/writing data from/to disk."""

import json
import os
import sys

from . import io_csv
from . import io_h5


def read_config(data_dir, filenames):
    """Read a JSON configuration file."""

    if not isinstance(filenames, list):
        filenames = [filenames]

    success = False
    for filename in filenames:
        config_path = os.path.join(data_dir, filename)
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                data = f.read()
            config = json.loads(data)
            success = True
            break

    if not success:
        sys.exit("-- ERROR! Could not find config file.")

    return config


def read_simulation_config(data_dir):
    """Read a JSON simulation configuration file."""

    # Supporting old filename.
    filenames = [
        "simulation_config.json",
        "config.json",
    ]
    return read_config(data_dir=data_dir, filenames=filenames)


def read_postprocess_config(data_dir):
    """Read a JSON postprocess configuration file."""

    # Supporting old filename.
    filenames = [
        "postprocess_config.json",
        "postprocess.json",
    ]
    return read_config(data_dir=data_dir, filenames=filenames)


def read_data(data_dir, key, data_format):
    """Read data, e.g. the order parameter, from a directory."""

    if data_format == "h5":
        data = io_h5.read_data(data_dir=data_dir, key=key)
    elif data_format == "csv":
        data = io_csv.read_data(data_dir=data_dir, key=key)
    else:
        raise ValueError(f"-- ERROR! Data format {data_format} is not supported.")

    return data


def write_data(data_dir, key, data, data_format):
    """Write data, e.g. the order parameter, to a directory."""

    if data_format == "h5":
        success = io_h5.write_data(data_dir=data_dir, key=key, data=data)
    elif data_format == "csv":
        success = io_csv.write_data(data_dir=data_dir, key=key, data=data)
    else:
        raise ValueError(f"-- ERROR! Data format {data_format} is not supported.")

    return success
