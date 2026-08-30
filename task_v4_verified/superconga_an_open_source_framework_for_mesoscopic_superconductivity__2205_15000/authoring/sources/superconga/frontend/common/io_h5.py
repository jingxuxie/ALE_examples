#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""Functionality for reading/writing data from/to disk."""

import h5py
import numpy as np
import os
import sys


__all__ = ["read_data", "write_data"]


# Read data for a certain key from h5 file.
def _read_data(hf, key):
    """Read a dataset from an H5 file."""

    if not key in hf.keys():
        sys.exit(f"-- ERROR! Could not find {key} in h5 file.")

    # Fetch dimensions.
    dim_x = hf[key].attrs["dim_x"]
    dim_y = hf[key].attrs["dim_y"]

    # Convert to NumPy.
    data = np.array(hf[key])
    return np.reshape(data, [-1, dim_y, dim_x])


def _get_filename(data_dir, filenames):
    """Get the first existing filename from a list of filenames."""

    for filename in filenames:
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            return filename
    return filenames[0]


def read_data(data_dir, key):
    """Read data, e.g. the order parameter, from a directory."""

    # Check if H5 file exists.
    if key in ["ldos"]:
        filenames = ["postprocess.h5", "spectroscopy.h5"]
    else:
        filenames = ["simulation.h5"]
    filename = _get_filename(data_dir=data_dir, filenames=filenames)

    # Full path.
    h5_path = os.path.join(data_dir, filename)

    # Check if it exists.
    if not os.path.exists(h5_path):
        sys.exit(f"-- ERROR! The file {h5_path} does not exist.")

    # Open H5 file.
    hf = h5py.File(h5_path, "r")

    # Read data.
    return _read_data(hf=hf, key=key)


# Write data for a certain key to h5 file.
def _write_data(hf, key, data):
    """Write a dataset to an H5 file."""

    # Get data dimensions.
    dims = np.shape(data)
    if len(dims) == 2:
        dim_z = 1
        dim_y, dim_x = np.shape(data)
    elif len(dims) == 3:
        dim_z, dim_y, dim_x = np.shape(data)
    else:
        print("-- ERROR! The data should be 2D or 3D.")
        return False

    # TODO(Niclas): Do it in a better way.
    if "order_parameter" in key:
        is_complex = 1
        assert dim_z % 2 == 0
        dim_z = dim_z // 2
    else:
        is_complex = 0

    # Delete dataset if it exists.
    if key in hf.keys():
        del hf[key]

    # Create dataset and set attributes.
    hf.create_dataset(key, data=data.flatten())
    hf[key].attrs["dim_x"] = dim_x
    hf[key].attrs["dim_y"] = dim_y
    hf[key].attrs["dim_z"] = dim_z
    hf[key].attrs["is_complex"] = is_complex
    return True


def write_data(data_dir, key, data):
    """Write data, e.g. the order parameter, to a directory."""

    if key in ["ldos"]:
        filename = "postprocess.h5"
    else:
        filename = "simulation.h5"

    # Open H5 file.
    h5_path = os.path.join(data_dir, filename)
    hf = h5py.File(h5_path, "a")

    # Write data.
    success = _write_data(hf=hf, key=key, data=data)

    return success
