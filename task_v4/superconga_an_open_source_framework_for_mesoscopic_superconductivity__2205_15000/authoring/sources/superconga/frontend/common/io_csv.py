#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""Functionality for reading/writing data from/to disk."""

import numpy as np
import os
import pandas as pd
import sys

__all__ = ["read_data", "write_data"]


# Read data for a certain key from Pandas dataframe.
def _read_data(df, key):
    """Read a column from a CSV file."""

    if not ((key in df) and ("x_idx" in df) and ("y_idx" in df)):
        sys.exit(f"-- ERROR! Could not find {key}, or indices, in csv file.")

    # Fetch dimensions.
    dim_x = df["x_idx"].max() + 1
    dim_y = df["y_idx"].max() + 1

    # Convert to NumPy.
    data = df[key].to_numpy()
    return np.reshape(data, [-1, dim_y, dim_x])


def read_data(data_dir, key):
    """Read data, e.g. the order parameter, from a directory."""

    # Open CSV file.
    if "order_parameter" in key:
        filename = "order_parameter.csv"
    else:
        filename = key + ".csv"
    csv_path = os.path.join(data_dir, filename)

    # The file does not exist.
    if not os.path.exists(csv_path):
        sys.exit(f"-- ERROR! The file {csv_path} does not exist.")

    # Open file.
    df = pd.read_csv(csv_path)

    # Unfortunately the data is saved in a rather annoying way.
    if "order_parameter" in key:
        symmetry = key[(len("order_parameter") + 1) :]
        key_real = symmetry + "_re"
        key_imag = symmetry + "_im"
        data_real = _read_data(df=df, key=key_real)
        data_imag = _read_data(df=df, key=key_imag)
        data = np.concatenate([data_real, data_imag], axis=0)
    elif "current_density" in key:
        data_x = _read_data(df=df, key="j_x")
        data_y = _read_data(df=df, key="j_y")
        data = np.concatenate([data_x, data_y], axis=0)
    elif "vector_potential" in key:
        data_x = _read_data(df=df, key="a_x")
        data_y = _read_data(df=df, key="a_y")
        data = np.concatenate([data_x, data_y], axis=0)
    elif "flux_density" in key:
        data = _read_data(df=df, key="b_z")
    elif "domain" in key:
        data = _read_data(df=df, key=key)
    elif "ldos" in key:
        data = _read_data(df=df, key=key)
    else:
        raise ValueError(f"-- ERROR! Can not find data for {key}.")

    return data


# Write data for a certain key to csv file.
def _write_data(filename, key, data):
    """Write a column to a CSV file."""

    # Remove dimensions.
    data = np.squeeze(data)

    # Read file if it exists.
    if os.path.exists(filename):
        df = pd.read_csv(filename)
    else:
        df = pd.DataFrame()

    # Get data dimensions.
    dims = np.shape(data)

    # TODO(Niclas): Unnecessary to do this every time we're adding a column.
    if len(dims) == 2:
        dim_y, dim_x = np.shape(data)

        # Create meshgrid.
        vx = np.array(list(range(dim_x)))
        vy = np.array(list(range(dim_y)))
        X, Y = np.meshgrid(vx, vy)

        # Add/update columns.
        df["x_idx"] = X.flatten()
        df["y_idx"] = Y.flatten()
    elif len(dims) == 3:
        dim_z, dim_y, dim_x = np.shape(data)

        # Create meshgrid.
        vx = np.array(list(range(dim_x)))
        vy = np.array(list(range(dim_y)))
        vz = np.array(list(range(dim_z)))
        X, Y, Z = np.meshgrid(vx, vy, vz)

        # Add/update columns.
        df["x_idx"] = X.flatten()
        df["y_idx"] = Y.flatten()
        df["e_idx"] = Z.flatten()
    else:
        print("-- ERROR! The data should be 2D or 3D.")
        return False

    # Add column.
    df[key] = data.flatten()

    # Write.
    df.to_csv(filename, header=True, index=False, float_format="%.16e")

    return True


def write_data(data_dir, key, data):
    """Write data, e.g. the order parameter, to a directory."""

    # Determine filename.
    if "order_parameter" in key:
        filename = "order_parameter.csv"
    else:
        filename = key + ".csv"
    csv_path = os.path.join(data_dir, filename)

    # Unfortunately the data is saved in a rather annoying way.
    if "order_parameter" in key:
        symmetry = key[(len("order_parameter") + 1) :]
        key_real = symmetry + "_re"
        key_imag = symmetry + "_im"
        data_real, data_imag = np.split(data, indices_or_sections=2, axis=0)
        success_real = _write_data(filename=csv_path, key=key_real, data=data_real)
        success_imag = _write_data(filename=csv_path, key=key_imag, data=data_imag)
        success = success_real and success_imag
    elif "current_density" in key:
        data_x, data_y = np.split(data, indices_or_sections=2, axis=0)
        success_x = _write_data(filename=csv_path, key="j_x", data=data_x)
        success_y = _write_data(filename=csv_path, key="j_y", data=data_y)
        success = success_x and success_y
    elif "vector_potential" in key:
        data_x, data_y = np.split(data, indices_or_sections=2, axis=0)
        success_x = _write_data(filename=csv_path, key="a_x", data=data_x)
        success_y = _write_data(filename=csv_path, key="a_y", data=data_y)
        success = success_x and success_y
    elif "flux_density" in key:
        success = _write_data(filename=csv_path, key="b_z", data=data)
    elif "domain" in key:
        success = _write_data(filename=csv_path, key=key, data=data)
    elif "ldos" in key:
        success = _write_data(filename=csv_path, key=key, data=data)
    else:
        raise ValueError(f"-- ERROR! Can not find data for {key}.")

    return success
