#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""
The main part of the simulation plotter.
"""

import argparse
import os
import sys
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

# TODO(Niclas): I don't understand how Python imports work...
try:
    from . import default
    from .arguments import make_parser
except ImportError:
    import default
    from arguments import make_parser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))
from common import plotting, io


def get_rows_cols(view: list, num_op_comps: int) -> tuple:
    """Compute the number of needed rows and columns in order to plot everything requested."""

    rows = 0
    cols = 0
    for what in view:
        if what == "D":
            rows += num_op_comps
            cols = max(cols, 2)
        elif what == "J":
            rows += 1
            cols = max(cols, 2)
        elif what == "A":
            rows += 1
            cols = max(cols, 2)
        elif what == "B":
            rows += 1
            cols = max(cols, 1)
        else:
            raise ValueError(f"-- ERROR! View '{what}' is not understood.")
    return rows, cols


def make_plot_row(
    fig,
    axes,
    idx,
    data,
    extent,
    labels,
    colormaps,
    bad_color="dimgray",
    landscape=False,
    cartesian=False,
) -> None:
    """Make an entire row (or column) of plots."""

    # Extract row axes.
    axes_row = axes[:, idx] if landscape else axes[idx, :]
    num_axes = len(axes_row)

    if data.shape[0] == 1:
        # Sanity check.
        assert (num_axes == 1) or (num_axes == 2)

        # Determine which axis to turn on/off.
        ax_idx_on = int(num_axes == 2 and landscape)
        ax_idx_off = 1 - ax_idx_on

        # Plot the data.
        plotting.imshow_and_colorbar(
            fig=fig,
            ax=axes_row[ax_idx_on],
            data=np.squeeze(data),
            label=labels[0],
            extent=extent,
            plot_type=plotting.PlotType.DEFAULT,
            colormap=colormaps["default"],
            bad_color=bad_color,
        )

        # Turn off the unused axis.
        if num_axes == 2:
            axes_row[ax_idx_off].axis("off")
    else:
        # Sanity checks.
        assert data.shape[0] == 2
        assert len(axes_row) == 2

        if cartesian:
            # Plot (real, imag) or (x, y) components.
            for i, ax in enumerate(axes_row):
                plotting.imshow_and_colorbar(
                    fig=fig,
                    ax=ax,
                    data=data[i, :, :],
                    label=labels[i],
                    extent=extent,
                    plot_type=plotting.PlotType.DEFAULT,
                    colormap=colormaps["default"],
                    bad_color=bad_color,
                )
        else:
            # Plot magnitude.
            plotting.imshow_and_colorbar(
                fig=fig,
                ax=axes_row[0],
                data=np.hypot(data[0, :, :], data[1, :, :]),
                label=labels[0],
                extent=extent,
                plot_type=plotting.PlotType.POSITIVE,
                colormap=colormaps["magnitude"],
                bad_color=bad_color,
            )

            # Plot phase or angle.
            plotting.imshow_and_colorbar(
                fig=fig,
                ax=axes_row[1],
                data=np.arctan2(data[1, :, :], data[0, :, :]),
                label=labels[1],
                extent=extent,
                plot_type=plotting.PlotType.ANGLE,
                colormap=colormaps["angle"],
                bad_color=bad_color,
            )


def apply_chiral_transform(data_op_comp_1, data_op_comp_2):
    """Transform order-parameter to the eigenbasis of the angular momentum operator L_z."""

    # Sanity check data dimensions and shape.
    data_shape_1 = np.shape(data_op_comp_1)
    data_shape_2 = np.shape(data_op_comp_2)
    assert data_shape_1 == data_shape_2
    assert len(data_shape_1) == 3

    # Assert: first index for real and imaginary part.
    assert data_shape_1[0] == 2

    # Get the magnitude and phases.
    op_mag_1 = np.hypot(data_op_comp_1[0, :, :], data_op_comp_1[1, :, :])
    op_mag_2 = np.hypot(data_op_comp_2[0, :, :], data_op_comp_2[1, :, :])
    op_phase_1 = np.arctan2(data_op_comp_1[1, :, :], data_op_comp_1[0, :, :])
    op_phase_2 = np.arctan2(data_op_comp_2[1, :, :], data_op_comp_2[0, :, :])

    # Transform to the eigenbasis of the L_z operator.
    # Yes, OP plus is with a minus between components. The plus comes from how it is defined
    # in the angular momentum eigenbasis: eta_{+/-} = exp((+/-)2*i*theta)
    op_plus = (
        op_mag_1 * np.exp(1.0j * op_phase_1)
        - op_mag_2 * 1.0j * np.exp(1.0j * op_phase_2)
    ) / np.sqrt(2.0)
    op_minus = (
        op_mag_1 * np.exp(1.0j * op_phase_1)
        + op_mag_2 * 1.0j * np.exp(1.0j * op_phase_2)
    ) / np.sqrt(2.0)

    # The plotter works in real and imaginary parts: return these.
    data_op_comp_1[0] = np.real(op_plus)
    data_op_comp_1[1] = np.imag(op_plus)
    data_op_comp_2[0] = np.real(op_minus)
    data_op_comp_2[1] = np.imag(op_minus)

    return data_op_comp_1, data_op_comp_2


def run(
    data_dir: str,
    save_path: Optional[str] = None,
    view: Optional[list] = default.settings["view"],
    cartesian: Optional[bool] = default.settings["cartesian"],
    subplot_width: Optional[int] = default.settings["subplot_width"],
    subplot_height: Optional[int] = default.settings["subplot_height"],
    landscape: Optional[bool] = default.settings["landscape"],
    fontsize: Optional[int] = default.settings["fontsize"],
    alphabet: Optional[bool] = default.settings["alphabet"],
    show_path: Optional[bool] = default.settings["show_path"],
    use_tex: Optional[bool] = default.settings["use_tex"],
    colormaps: Optional[dict] = default.settings["colormaps"],
    exterior_color: Optional[str] = default.settings["exterior_color"],
    chiral_transform: Optional[str] = default.settings["chiral_transform"],
) -> None:
    """Run the simulation plotter."""

    # Check if data_dir is set.
    if data_dir is None:
        sys.exit("-- ERROR! Please specify '--load-path'.")

    # Read configuration file.
    config = io.read_simulation_config(data_dir=data_dir)

    # Set global parameters, i.e. for all plots. Must be done before the figure is made.
    plotting.set_global_parameters(fontsize=fontsize, use_tex=use_tex)

    # Compute the number of needed rows and columns.
    num_op_comps = len(config["physics"]["order_parameter"])
    rows, cols = get_rows_cols(view=view, num_op_comps=num_op_comps)

    # Make figure.
    if landscape:
        rows, cols = cols, rows
    name = data_dir if show_path else None
    fig, axes = plotting.make_figure(
        rows=rows,
        cols=cols,
        subplot_width=subplot_width,
        subplot_height=subplot_height,
        sharex="all",
        sharey="all",
        name=name,
    )

    # Set the data format.
    data_format = config["misc"]["data_format"]

    # Get the domain so we can color the outside of the domain gray.
    domain = io.read_data(data_dir=data_dir, key="domain", data_format=data_format)
    domain = domain.astype(float)
    domain[domain == 0] = np.nan

    # Extent.
    _, dim_y, dim_x = domain.shape
    ppxi = config["numerics"]["points_per_coherence_length"]
    extent = plotting.get_extent(ppxi=ppxi, dim_x=dim_x, dim_y=dim_y)

    # Loop over plot objects and plot them.
    idx = 0
    for what in view:
        # Get the actual keys and whether to "erase" the values outside of the domain.
        if what == "D":
            keys = []
            for symmetry in config["physics"]["order_parameter"].keys():
                keys.append("order_parameter_" + symmetry)
            erase = True
        elif what == "J":
            keys = ["current_density"]
            erase = True
        elif what == "A":
            keys = ["vector_potential"]
            erase = False
        elif what == "B":
            keys = ["magnetic_flux_density"]
            erase = False
        else:
            continue

        # Chiral transformation: only if OP has two components.
        if (what == "D") and (chiral_transform) and (num_op_comps == 2):
            # Read data.
            op_data_list = []
            for key in keys:
                # Extract data from file.
                op_data = io.read_data(
                    data_dir=data_dir, key=key, data_format=data_format
                )

                op_data_list.append(op_data)

            # Apply chiral transformation.
            chiral_data_list = apply_chiral_transform(op_data_list[0], op_data_list[1])

            # Chiral OP keys, used to get chiral OP labels.
            chiral_keys = ["order_parameter_+", "order_parameter_-"]

            applied_chiral_transform = True
        else:
            applied_chiral_transform = False

        # Loop over keys and plot the data.
        key_idx = 0
        for key in keys:
            if applied_chiral_transform:
                data = chiral_data_list[key_idx]
                key = chiral_keys[key_idx]
            else:
                # Extract data from file.
                data = io.read_data(data_dir=data_dir, key=key, data_format=data_format)

            # Erase data outside of the domain, i.e. set to NaN.
            if erase:
                data *= domain

            # Get labels.
            labels = (
                default.labels[key]["cartesian"]
                if cartesian
                else default.labels[key]["polar"]
            )

            # Plot a row (or column if landscape == True).
            make_plot_row(
                fig=fig,
                axes=axes,
                idx=idx,
                data=data,
                extent=extent,
                labels=labels,
                colormaps=colormaps,
                landscape=landscape,
                cartesian=cartesian,
                bad_color=exterior_color,
            )

            # Increase index.
            idx += 1
            key_idx += 1

    # Set ticks and labels, e.g. x/\xi_0.
    plotting.set_axes_ticks_and_labels(axes=axes, extent=extent)

    # Set alphabetic label, e.g. (a) at the top left.
    if alphabet:
        plotting.set_alphabetic_labels(axes=axes)

    # To save some space.
    fig.tight_layout()

    # Show or save.
    if save_path is None:
        plt.show()
    else:
        plt.savefig(save_path)
        print(f"-- Wrote plot to {save_path}")

    # Close stuff.
    plt.close()


# -----------------------------------------------------------------------------
# MAIN FUNCTION
# -----------------------------------------------------------------------------
def main(args: argparse.Namespace) -> None:
    """Main entry of the simulation plotter."""

    colormaps = {
        "default": args.cmap_default,
        "magnitude": args.cmap_magnitude,
        "angle": args.cmap_angle,
    }

    # Run the plotter.
    run(
        data_dir=args.load_path,
        save_path=args.save_path,
        view=args.view,
        cartesian=args.cartesian,
        subplot_width=args.subplot_width,
        subplot_height=args.subplot_height,
        landscape=(not args.no_landscape),
        fontsize=args.fontsize,
        alphabet=(not args.no_alphabet),
        show_path=(not args.no_path),
        use_tex=(not args.no_tex),
        colormaps=colormaps,
        exterior_color=args.exterior_color,
        chiral_transform=args.chiral_transform,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    make_parser(parser)
    args = parser.parse_args()
    main(args)
