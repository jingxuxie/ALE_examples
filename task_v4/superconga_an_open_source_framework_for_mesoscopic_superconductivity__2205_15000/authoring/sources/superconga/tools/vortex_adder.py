#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""Simple script for adding Abrikosov vortices to the order parameter read from a file."""

import argparse
import json
import numpy as np
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../frontend"))
from common import io

# -----------------------------------------------------------------------------
# MAIN FUNCTION
# -----------------------------------------------------------------------------
def main() -> None:
    # Create parser and subparsers.
    parser = argparse.ArgumentParser(
        description="Add Abrikosov vortices to order parameter."
    )
    parser.add_argument(
        "-L",
        "--load-path",
        type=str,
        default=None,
        help="Path to original data. (Default: %(default)s)",
    )
    parser.add_argument(
        "-S",
        "--save-path",
        type=str,
        default=None,
        help="Where to put the data. Files will be overwritten if they exist. (Default: %(default)s)",
    )
    # Additional Abrikosov vortices.
    parser.add_argument(
        "--vortex",
        metavar=("center_x", "center_y", "winding_number"),
        type=float,
        action="append",
        nargs=3,
        help="Add a vortex in all order-parameter components. Note, a vortex has a negative winding number, and an anti-vortex a positive winding number, for a positive external flux-density and negatively charged carriers.",
    )

    # Parse arguments.
    args = parser.parse_args()

    # Print help if nothing is set.
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # Data directories.
    load_dir = os.path.normpath(args.load_path)
    save_dir = os.path.normpath(args.save_path)

    # Check if load_dir is set.
    if load_dir is None:
        sys.exit("-- ERROR! Please specify '--load-path'.")

    # Check if save_dir is set.
    if save_dir is None:
        sys.exit("-- ERROR! Please specify '--save-path'.")

    # Get vortices.
    vortices = []
    if args.vortex is not None:
        for vortex in args.vortex:
            center_x, center_y, winding_number = vortex
            vortices.append(
                {
                    "center_x": center_x,
                    "center_y": center_y,
                    "winding_number": winding_number,
                }
            )

    # Read config.
    config = io.read_simulation_config(data_dir=load_dir)

    # Data format.
    data_format = config["misc"]["data_format"]

    # Get domain.
    domain = io.read_data(data_dir=load_dir, key="domain", data_format=data_format)
    domain = (domain.astype(float))[0]
    dim_y, dim_x = domain.shape

    # Read important geometry parameters.
    ppxi = config["numerics"]["points_per_coherence_length"]
    x_len = dim_x / ppxi
    y_len = dim_y / ppxi
    x_max = x_len * 0.5
    x_min = -x_max
    y_max = y_len * 0.5
    y_min = -y_max

    # Copy files.
    if not load_dir == save_dir:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        if data_format == "csv":
            for filename in [
                "domain.csv",
                "order_parameter.csv",
                "vector_potential.csv",
            ]:
                path = os.path.join(load_dir, filename)
                shutil.copy(path, save_dir)
        elif data_format == "h5":
            path = os.path.join(load_dir, "simulation.h5")
            shutil.copy(path, save_dir)
        else:
            raise ValueError(f"-- ERROR! Data format {data_format} not supported.")
        # Also copy config file.
        config_path = os.path.join(load_dir, "simulation_config.json")
        shutil.copy(config_path, save_dir)

    # Get order parameter components.
    keys = []
    for symmetry in config["physics"]["order_parameter"].keys():
        keys.append("order_parameter_" + symmetry)

    # Loop over order parameter components and vortices.
    success = True
    for key in keys:
        # Read the data.
        read_data = io.read_data(data_dir=save_dir, key=key, data_format=data_format)

        # Cast data to complex for easier vortex application.
        data = read_data[0] + (1.0j) * read_data[1]

        # Loop over vortices.
        for vortex in vortices:
            # Compute vortex coordinates in appropriate coordinate system.
            x0 = np.linspace(x_min, x_max, dim_x) - vortex["center_x"]
            y0 = np.linspace(y_min, y_max, dim_y) - vortex["center_y"]
            vortex_X, vortex_Y = np.meshgrid(x0, y0)

            # Compute vortex as a phase winding.
            angle = np.arctan2(vortex_Y, vortex_X)
            phaseWinding = np.exp((1.0j) * angle * vortex["winding_number"])

            # Apply vortex.
            data *= phaseWinding

        save_data = np.array([data.real, data.imag])

        # Write the data.
        success = io.write_data(
            data_dir=save_dir,
            key=key,
            data=save_data,
            data_format=data_format,
        )

        # Abort if not successful.
        if not success:
            print(f"-- ERROR! Could not write {key}.")
            break

    if success:
        print(
            f"-- SUCCESS! Loaded data from {load_dir}, added vortices, and saved in {save_dir}."
        )
    else:
        print(
            f"-- FAILURE! Could not load data from {load_dir}, add vortices, and save in {save_dir}."
        )


if __name__ == "__main__":
    main()
